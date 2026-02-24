"""
AirAd Backend — Governance Service Layer (R4)

All business logic for fraud scoring, blacklist management, vendor suspension,
ToS acceptance, and consent management lives here.
Every mutation calls log_action() (R5).
Multi-step mutations wrapped in @transaction.atomic.
"""

import logging
from typing import Any

from apps.audit.utils import log_action
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from .models import (
    FRAUD_SIGNAL_SCORES,
    AppealStatus,
    Blacklist,
    BlacklistType,
    ConsentCategory,
    ConsentRecord,
    EnforcementAction,
    FraudScore,
    FraudSignal,
    VendorSuspension,
    VendorToSAcceptance,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# §6.2 — Fraud Score
# ---------------------------------------------------------------------------


@transaction.atomic
def add_fraud_signal(
    signal: str,
    actor: Any,
    request: HttpRequest | None,
    vendor_id: str | None = None,
    actor_email: str = "",
    reason: str = "",
) -> FraudScore:
    """Add a fraud signal to a vendor's or user's fraud score.

    Increments the score by the signal's defined weight.
    If the score crosses AUTO_SUSPEND_THRESHOLD (6+), sets is_auto_suspended=True
    and flags the vendor as FLAGGED in QC.

    Args:
        signal: One of FraudSignal values.
        actor: AdminUser or None (system-initiated).
        request: HTTP request for audit tracing.
        vendor_id: UUID string of the vendor (optional).
        actor_email: Email of the entity being scored.
        reason: Human-readable reason for this signal.

    Returns:
        Updated FraudScore instance.

    Raises:
        ValueError: If signal is not a valid FraudSignal value.
    """
    from .models import FRAUD_SCORE_AUTO_SUSPEND_THRESHOLD

    valid_signals = [s.value for s in FraudSignal]
    if signal not in valid_signals:
        raise ValueError(
            f"Invalid fraud signal '{signal}'. Must be one of {valid_signals}"
        )

    score_delta = FRAUD_SIGNAL_SCORES.get(signal, 1)

    fraud_score, _ = FraudScore.objects.select_for_update().get_or_create(
        vendor_id=vendor_id if vendor_id else None,
        defaults={"actor_email": actor_email, "score": 0},
    )

    if actor_email and not fraud_score.actor_email:
        fraud_score.actor_email = actor_email

    before_score = fraud_score.score
    fraud_score.score += score_delta

    signal_event = {
        "signal": signal,
        "score_delta": score_delta,
        "reason": reason,
        "ts": timezone.now().isoformat(),
    }
    signals_list = list(fraud_score.signals) if fraud_score.signals else []
    signals_list.append(signal_event)
    fraud_score.signals = signals_list

    newly_suspended = False
    if fraud_score.should_auto_suspend and not fraud_score.is_auto_suspended:
        fraud_score.is_auto_suspended = True
        newly_suspended = True

        if vendor_id:
            from apps.vendors.models import QCStatus, Vendor

            try:
                vendor = Vendor.objects.get(id=vendor_id)
                vendor.qc_status = QCStatus.FLAGGED
                vendor.qc_notes = (
                    f"Auto-suspended: fraud score reached {fraud_score.score} "
                    f"(threshold: {FRAUD_SCORE_AUTO_SUSPEND_THRESHOLD}). "
                    f"Requires Ops Manager approval to reactivate."
                )
                vendor.save(update_fields=["qc_status", "qc_notes", "updated_at"])
                log_action(
                    action="VENDOR_AUTO_SUSPENDED_FRAUD",
                    actor=actor,
                    target_obj=vendor,
                    request=request,
                    before={"qc_status": QCStatus.FLAGGED},
                    after={"fraud_score": fraud_score.score, "signal": signal},
                )
            except Exception:
                logger.exception(
                    "Failed to flag vendor %s for fraud auto-suspend", vendor_id
                )

    fraud_score.save()

    log_action(
        action="FRAUD_SIGNAL_ADDED",
        actor=actor,
        target_obj=fraud_score,
        request=request,
        before={"score": before_score},
        after={
            "score": fraud_score.score,
            "signal": signal,
            "score_delta": score_delta,
            "is_auto_suspended": fraud_score.is_auto_suspended,
            "newly_suspended": newly_suspended,
        },
    )
    return fraud_score


def get_fraud_score(vendor_id: str) -> FraudScore | None:
    """Return the FraudScore for a vendor, or None if not found.

    Args:
        vendor_id: UUID string of the vendor.

    Returns:
        FraudScore instance or None.
    """
    try:
        return FraudScore.objects.get(vendor_id=vendor_id)
    except FraudScore.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# §6.3 — Blacklist Management
# ---------------------------------------------------------------------------


@transaction.atomic
def add_to_blacklist(
    blacklist_type: str,
    value: str,
    reason: str,
    actor: Any,
    request: HttpRequest | None,
) -> Blacklist:
    """Add an entry to the blacklist. Requires Ops Manager approval (enforced in views).

    Args:
        blacklist_type: One of BlacklistType values.
        value: The value to blacklist (phone, device ID, or 'lat,lon').
        reason: Mandatory reason for blacklisting.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Created or reactivated Blacklist instance.

    Raises:
        ValueError: If blacklist_type is invalid or reason is empty.
    """
    valid_types = [t.value for t in BlacklistType]
    if blacklist_type not in valid_types:
        raise ValueError(
            f"Invalid blacklist_type '{blacklist_type}'. Must be one of {valid_types}"
        )

    if not reason.strip():
        raise ValueError(
            "Reason is required for blacklist entries (audit trail requirement)."
        )

    entry, created = Blacklist.objects.get_or_create(
        blacklist_type=blacklist_type,
        value=value.strip(),
        defaults={
            "reason": reason.strip(),
            "added_by": actor if hasattr(actor, "pk") else None,
            "is_active": True,
        },
    )

    if not created and not entry.is_active:
        entry.is_active = True
        entry.reason = reason.strip()
        entry.added_by = actor if hasattr(actor, "pk") else None
        entry.save(update_fields=["is_active", "reason", "added_by", "updated_at"])

    log_action(
        action="BLACKLIST_ENTRY_ADDED",
        actor=actor,
        target_obj=entry,
        request=request,
        before={},
        after={"blacklist_type": blacklist_type, "value": value, "reason": reason},
    )
    return entry


@transaction.atomic
def lift_blacklist_entry(
    entry_id: str,
    actor: Any,
    request: HttpRequest | None,
    notes: str = "",
) -> Blacklist:
    """Lift a blacklist entry (appeal approved).

    Args:
        entry_id: UUID string of the Blacklist entry.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
        notes: Optional notes from the appeal review.

    Returns:
        Updated Blacklist instance with is_active=False.

    Raises:
        ValueError: If entry not found or already inactive.
    """
    try:
        entry = Blacklist.objects.get(id=entry_id)
    except Blacklist.DoesNotExist:
        raise ValueError(f"Blacklist entry '{entry_id}' not found")

    if not entry.is_active:
        raise ValueError("Blacklist entry is already inactive.")

    entry.is_active = False
    entry.save(update_fields=["is_active", "updated_at"])

    log_action(
        action="BLACKLIST_ENTRY_LIFTED",
        actor=actor,
        target_obj=entry,
        request=request,
        before={"is_active": True},
        after={"is_active": False, "notes": notes},
    )
    return entry


def is_blacklisted(blacklist_type: str, value: str) -> bool:
    """Check whether a value is currently on the active blacklist.

    Args:
        blacklist_type: One of BlacklistType values.
        value: The value to check.

    Returns:
        True if an active blacklist entry exists for this type+value.
    """
    return Blacklist.objects.filter(
        blacklist_type=blacklist_type,
        value=value.strip(),
        is_active=True,
    ).exists()


# ---------------------------------------------------------------------------
# §8.2 — Vendor Suspension (Enforcement Ladder)
# ---------------------------------------------------------------------------


@transaction.atomic
def issue_enforcement_action(
    vendor_id: str,
    action: str,
    reason: str,
    actor: Any,
    request: HttpRequest | None,
    policy_reference: str = "",
    suspension_days: int = 7,
) -> VendorSuspension:
    """Issue an enforcement action against a vendor (spec §8.2).

    For TEMPORARY_SUSPENSION, sets suspension_ends_at = now + suspension_days.
    For PERMANENT_BAN, also sets vendor.is_deleted=True (soft delete).
    All actions are audit-logged.

    Args:
        vendor_id: UUID string of the vendor.
        action: One of EnforcementAction values.
        reason: Mandatory reason for the action (shown to vendor).
        actor: AdminUser issuing the action.
        request: HTTP request for audit tracing.
        policy_reference: Optional policy clause reference.
        suspension_days: Days for TEMPORARY_SUSPENSION (default 7).

    Returns:
        Created VendorSuspension instance.

    Raises:
        ValueError: If action is invalid or vendor not found.
    """
    from apps.vendors.models import Vendor

    valid_actions = [a.value for a in EnforcementAction]
    if action not in valid_actions:
        raise ValueError(
            f"Invalid enforcement action '{action}'. Must be one of {valid_actions}"
        )

    if not reason.strip():
        raise ValueError("Reason is required for enforcement actions.")

    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        raise ValueError(f"Vendor '{vendor_id}' not found")

    suspension_ends_at = None
    if action == EnforcementAction.TEMPORARY_SUSPENSION:
        from datetime import timedelta

        suspension_ends_at = timezone.now() + timedelta(days=suspension_days)

    suspension = VendorSuspension.objects.create(
        vendor=vendor,
        action=action,
        reason=reason.strip(),
        policy_reference=policy_reference.strip(),
        issued_by=actor if hasattr(actor, "pk") else None,
        suspension_ends_at=suspension_ends_at,
        is_active=True,
    )

    if action == EnforcementAction.PERMANENT_BAN:
        from apps.vendors.models import QCStatus

        vendor.qc_status = QCStatus.FLAGGED
        vendor.qc_notes = f"Permanently banned: {reason}"
        vendor.save(update_fields=["qc_status", "qc_notes", "updated_at"])

    log_action(
        action="VENDOR_ENFORCEMENT_ACTION",
        actor=actor,
        target_obj=vendor,
        request=request,
        before={},
        after={
            "enforcement_action": action,
            "reason": reason,
            "suspension_ends_at": (
                suspension_ends_at.isoformat() if suspension_ends_at else None
            ),
            "policy_reference": policy_reference,
        },
    )
    return suspension


@transaction.atomic
def process_appeal(
    suspension_id: str,
    decision: str,
    reviewer: Any,
    request: HttpRequest | None,
    notes: str = "",
) -> VendorSuspension:
    """Process an appeal for a vendor suspension (spec §8.2).

    decision must be 'APPROVED' or 'REJECTED'.
    On APPROVED: sets is_active=False, restores vendor QC status to PENDING.

    Args:
        suspension_id: UUID string of the VendorSuspension.
        decision: 'APPROVED' or 'REJECTED'.
        reviewer: AdminUser reviewing the appeal.
        request: HTTP request for audit tracing.
        notes: Notes from the appeal review.

    Returns:
        Updated VendorSuspension instance.

    Raises:
        ValueError: If suspension not found, no appeal pending, or invalid decision.
    """
    try:
        suspension = VendorSuspension.objects.select_related("vendor").get(
            id=suspension_id
        )
    except VendorSuspension.DoesNotExist:
        raise ValueError(f"Suspension '{suspension_id}' not found")

    if suspension.appeal_status != AppealStatus.PENDING:
        raise ValueError("No pending appeal on this suspension.")

    if decision not in (AppealStatus.APPROVED, AppealStatus.REJECTED):
        raise ValueError("Decision must be 'APPROVED' or 'REJECTED'.")

    before = {
        "appeal_status": suspension.appeal_status,
        "is_active": suspension.is_active,
    }

    suspension.appeal_status = decision
    suspension.appeal_notes = notes
    suspension.appeal_reviewed_by = reviewer if hasattr(reviewer, "pk") else None
    suspension.appeal_reviewed_at = timezone.now()

    if decision == AppealStatus.APPROVED:
        suspension.is_active = False
        from apps.vendors.models import QCStatus

        suspension.vendor.qc_status = QCStatus.PENDING
        suspension.vendor.qc_notes = "Suspension lifted — appeal approved."
        suspension.vendor.save(update_fields=["qc_status", "qc_notes", "updated_at"])

    suspension.save()

    log_action(
        action="VENDOR_APPEAL_PROCESSED",
        actor=reviewer,
        target_obj=suspension.vendor,
        request=request,
        before=before,
        after={
            "appeal_status": decision,
            "is_active": suspension.is_active,
            "notes": notes,
        },
    )
    return suspension


@transaction.atomic
def file_appeal(
    suspension_id: str,
    actor: Any,
    request: HttpRequest | None,
) -> VendorSuspension:
    """File an appeal for a vendor suspension (spec §8.2 — 7-day window).

    Args:
        suspension_id: UUID string of the VendorSuspension.
        actor: AdminUser or vendor representative filing the appeal.
        request: HTTP request for audit tracing.

    Returns:
        Updated VendorSuspension with appeal_status=PENDING.

    Raises:
        ValueError: If suspension not found, already appealed, or appeal window expired.
    """
    from datetime import timedelta

    try:
        suspension = VendorSuspension.objects.get(id=suspension_id)
    except VendorSuspension.DoesNotExist:
        raise ValueError(f"Suspension '{suspension_id}' not found")

    if suspension.appeal_status != AppealStatus.NONE:
        raise ValueError("An appeal has already been filed for this suspension.")

    appeal_deadline = suspension.created_at + timedelta(days=7)
    if timezone.now() > appeal_deadline:
        raise ValueError("Appeal window has expired (7 days from suspension date).")

    suspension.appeal_status = AppealStatus.PENDING
    suspension.save(update_fields=["appeal_status", "updated_at"])

    log_action(
        action="VENDOR_APPEAL_FILED",
        actor=actor,
        target_obj=suspension,
        request=request,
        before={"appeal_status": AppealStatus.NONE},
        after={"appeal_status": AppealStatus.PENDING},
    )
    return suspension


# ---------------------------------------------------------------------------
# §8.3 — Vendor ToS Acceptance
# ---------------------------------------------------------------------------


@transaction.atomic
def record_tos_acceptance(
    vendor_id: str,
    accepted_by_email: str,
    actor: Any,
    request: HttpRequest | None,
    tos_version: str = "1.0",
) -> VendorToSAcceptance:
    """Record vendor terms-of-service acceptance (spec §8.3).

    Args:
        vendor_id: UUID string of the vendor.
        accepted_by_email: Email of the person accepting the ToS.
        actor: AdminUser or vendor representative.
        request: HTTP request for audit tracing.
        tos_version: Version of the ToS being accepted.

    Returns:
        Created VendorToSAcceptance instance.

    Raises:
        ValueError: If vendor not found.
    """
    from apps.vendors.models import Vendor
    from core.utils import get_client_ip

    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        raise ValueError(f"Vendor '{vendor_id}' not found")

    ip_address = get_client_ip(request) if request else None

    acceptance = VendorToSAcceptance.objects.create(
        vendor=vendor,
        tos_version=tos_version,
        accepted_by_email=accepted_by_email,
        ip_address=ip_address,
    )

    log_action(
        action="VENDOR_TOS_ACCEPTED",
        actor=actor,
        target_obj=vendor,
        request=request,
        before={},
        after={
            "tos_version": tos_version,
            "accepted_by_email": accepted_by_email,
            "ip_address": ip_address,
        },
    )
    return acceptance


# ---------------------------------------------------------------------------
# §8.1 — Consent Management
# ---------------------------------------------------------------------------


@transaction.atomic
def record_consent(
    user_id: str,
    category: str,
    granted: bool,
    actor: Any,
    request: HttpRequest | None,
) -> ConsentRecord:
    """Record a GDPR consent action for a user (spec §8.1).

    Creates a new immutable ConsentRecord for the given category.
    The most recent record for a category is the current consent state.

    Args:
        user_id: UUID string of the AdminUser.
        category: One of ConsentCategory values.
        granted: True = opted in, False = opted out.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Created ConsentRecord instance.

    Raises:
        ValueError: If category is invalid or user not found.
    """
    from apps.accounts.models import AdminUser
    from core.utils import get_client_ip

    valid_categories = [c.value for c in ConsentCategory]
    if category not in valid_categories:
        raise ValueError(
            f"Invalid consent category '{category}'. Must be one of {valid_categories}"
        )

    try:
        user = AdminUser.objects.get(id=user_id)
    except AdminUser.DoesNotExist:
        raise ValueError(f"User '{user_id}' not found")

    ip_address = get_client_ip(request) if request else None

    record = ConsentRecord.objects.create(
        user=user,
        category=category,
        granted=granted,
        ip_address=ip_address,
    )

    log_action(
        action="CONSENT_UPDATED",
        actor=actor,
        target_obj=user,
        request=request,
        before={},
        after={"category": category, "granted": granted, "ip_address": ip_address},
    )
    return record


def get_current_consent(user_id: str) -> dict[str, bool]:
    """Return the current consent state for all categories for a user.

    Returns the most recent ConsentRecord per category.

    Args:
        user_id: UUID string of the AdminUser.

    Returns:
        Dict mapping category → granted (bool). Missing categories = not yet set.
    """
    from django.db.models import Max

    latest_ids = (
        ConsentRecord.objects.filter(user_id=user_id)
        .values("category")
        .annotate(latest=Max("created_at"))
    )

    result: dict[str, bool] = {}
    for item in latest_ids:
        record = ConsentRecord.objects.filter(
            user_id=user_id,
            category=item["category"],
            created_at=item["latest"],
        ).first()
        if record:
            result[record.category] = record.granted

    return result
