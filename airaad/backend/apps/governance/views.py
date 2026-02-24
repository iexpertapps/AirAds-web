"""
AirAd Backend — Governance Views

Zero business logic — all delegated to governance/services.py (R4).
Every view uses RolePermission.for_roles() (R3).

Endpoints:
  Fraud Score:
    GET  /api/v1/governance/fraud-scores/                    — list (SUPER_ADMIN, OPERATIONS_MANAGER)
    POST /api/v1/governance/fraud-scores/signals/            — add signal (SUPER_ADMIN, OPERATIONS_MANAGER)
    GET  /api/v1/governance/fraud-scores/<vendor_pk>/        — vendor score detail

  Blacklist:
    GET  /api/v1/governance/blacklist/                       — list (SUPER_ADMIN, OPERATIONS_MANAGER)
    POST /api/v1/governance/blacklist/                       — add entry (SUPER_ADMIN, OPERATIONS_MANAGER)
    POST /api/v1/governance/blacklist/<pk>/lift/             — lift entry (SUPER_ADMIN, OPERATIONS_MANAGER)

  Vendor Suspension:
    GET  /api/v1/governance/suspensions/                     — list (SUPER_ADMIN, OPERATIONS_MANAGER)
    POST /api/v1/governance/suspensions/                     — issue action (SUPER_ADMIN, OPERATIONS_MANAGER)
    POST /api/v1/governance/suspensions/<pk>/appeal/         — file appeal (any authenticated)
    POST /api/v1/governance/suspensions/<pk>/appeal/review/  — review appeal (SUPER_ADMIN, OPERATIONS_MANAGER)

  ToS Acceptance:
    POST /api/v1/governance/tos/accept/                      — record acceptance
    GET  /api/v1/governance/tos/<vendor_pk>/                 — list acceptances for vendor

  Consent:
    GET  /api/v1/governance/consent/                         — current consent state (self)
    POST /api/v1/governance/consent/                         — update consent (self)
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AdminRole
from apps.accounts.permissions import RolePermission
from core.exceptions import success_response
from core.pagination import StandardResultsPagination

from .models import Blacklist, FraudScore, VendorSuspension, VendorToSAcceptance
from .serializers import (
    AddFraudSignalSerializer,
    BlacklistSerializer,
    ConsentRecordSerializer,
    CreateBlacklistSerializer,
    FraudScoreSerializer,
    IssueEnforcementSerializer,
    LiftBlacklistSerializer,
    ProcessAppealSerializer,
    RecordToSAcceptanceSerializer,
    UpdateConsentSerializer,
    VendorSuspensionSerializer,
    VendorToSAcceptanceSerializer,
)
from .services import (
    add_fraud_signal,
    add_to_blacklist,
    file_appeal,
    get_current_consent,
    get_fraud_score,
    issue_enforcement_action,
    lift_blacklist_entry,
    process_appeal,
    record_consent,
    record_tos_acceptance,
)

logger = logging.getLogger(__name__)

_GOVERNANCE_ROLES = RolePermission.for_roles(
    AdminRole.SUPER_ADMIN,
    AdminRole.OPERATIONS_MANAGER,
)
_GOVERNANCE_READ_ROLES = RolePermission.for_roles(
    AdminRole.SUPER_ADMIN,
    AdminRole.OPERATIONS_MANAGER,
    AdminRole.CONTENT_MODERATOR,
)


# ---------------------------------------------------------------------------
# Fraud Score
# ---------------------------------------------------------------------------


class FraudScoreListView(APIView):
    """GET /api/v1/governance/fraud-scores/ — list all fraud scores."""

    permission_classes = [_GOVERNANCE_READ_ROLES]

    @extend_schema(
        tags=["Governance"],
        summary="List fraud scores (SUPER_ADMIN, OPERATIONS_MANAGER)",
        responses={200: FraudScoreSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of fraud scores, optionally filtered by auto_suspended."""
        qs = FraudScore.objects.select_related("vendor").order_by("-score")

        auto_suspended = request.query_params.get("auto_suspended")
        if auto_suspended is not None:
            qs = qs.filter(is_auto_suspended=auto_suspended.lower() == "true")

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            FraudScoreSerializer(page, many=True).data
        )


class FraudSignalCreateView(APIView):
    """POST /api/v1/governance/fraud-scores/signals/ — add a fraud signal."""

    permission_classes = [_GOVERNANCE_ROLES]

    @extend_schema(
        tags=["Governance"],
        summary="Add fraud signal to vendor score (SUPER_ADMIN, OPERATIONS_MANAGER)",
        request=AddFraudSignalSerializer,
        responses={200: FraudScoreSerializer},
    )
    def post(self, request: Request) -> Response:
        """Add a fraud signal and update the vendor's fraud score."""
        serializer = AddFraudSignalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            fraud_score = add_fraud_signal(
                signal=d["signal"],
                actor=request.user,
                request=request._request,
                vendor_id=str(d["vendor_id"]) if d.get("vendor_id") else None,
                actor_email=d.get("actor_email", ""),
                reason=d.get("reason", ""),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(data=FraudScoreSerializer(fraud_score).data)


class FraudScoreDetailView(APIView):
    """GET /api/v1/governance/fraud-scores/<vendor_pk>/ — vendor fraud score detail."""

    permission_classes = [_GOVERNANCE_READ_ROLES]

    @extend_schema(
        tags=["Governance"],
        summary="Get fraud score for a vendor (SUPER_ADMIN, OPERATIONS_MANAGER)",
        responses={200: FraudScoreSerializer},
    )
    def get(self, request: Request, vendor_pk: str) -> Response:
        """Return the fraud score for a specific vendor."""
        fraud_score = get_fraud_score(vendor_pk)
        if fraud_score is None:
            return success_response(
                data={
                    "vendor_id": vendor_pk,
                    "score": 0,
                    "signals": [],
                    "is_auto_suspended": False,
                },
                message="No fraud signals recorded for this vendor.",
            )
        return success_response(data=FraudScoreSerializer(fraud_score).data)


# ---------------------------------------------------------------------------
# Blacklist
# ---------------------------------------------------------------------------


class BlacklistListCreateView(APIView):
    """GET/POST /api/v1/governance/blacklist/ — list or add blacklist entries."""

    _read_roles = _GOVERNANCE_READ_ROLES
    _write_roles = _GOVERNANCE_ROLES

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Governance"],
        summary="List blacklist entries (SUPER_ADMIN, OPERATIONS_MANAGER)",
        responses={200: BlacklistSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of blacklist entries."""
        qs = Blacklist.objects.select_related("added_by").order_by("-created_at")

        blacklist_type = request.query_params.get("blacklist_type")
        if blacklist_type:
            qs = qs.filter(blacklist_type=blacklist_type)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            BlacklistSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["Governance"],
        summary="Add blacklist entry (SUPER_ADMIN, OPERATIONS_MANAGER)",
        request=CreateBlacklistSerializer,
        responses={201: BlacklistSerializer},
    )
    def post(self, request: Request) -> Response:
        """Add a new blacklist entry. Reason is mandatory."""
        serializer = CreateBlacklistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            entry = add_to_blacklist(
                blacklist_type=d["blacklist_type"],
                value=d["value"],
                reason=d["reason"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=BlacklistSerializer(entry).data,
            message="Blacklist entry added.",
            status_code=status.HTTP_201_CREATED,
        )


class BlacklistLiftView(APIView):
    """POST /api/v1/governance/blacklist/<pk>/lift/ — lift a blacklist entry."""

    permission_classes = [_GOVERNANCE_ROLES]

    @extend_schema(
        tags=["Governance"],
        summary="Lift blacklist entry — appeal approved (SUPER_ADMIN, OPERATIONS_MANAGER)",
        request=LiftBlacklistSerializer,
        responses={200: BlacklistSerializer},
    )
    def post(self, request: Request, pk: str) -> Response:
        """Lift (deactivate) a blacklist entry."""
        serializer = LiftBlacklistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            entry = lift_blacklist_entry(
                entry_id=pk,
                actor=request.user,
                request=request._request,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=BlacklistSerializer(entry).data, message="Blacklist entry lifted."
        )


# ---------------------------------------------------------------------------
# Vendor Suspension
# ---------------------------------------------------------------------------


class VendorSuspensionListCreateView(APIView):
    """GET/POST /api/v1/governance/suspensions/ — list or issue enforcement actions."""

    _read_roles = _GOVERNANCE_READ_ROLES
    _write_roles = _GOVERNANCE_ROLES

    def get_permissions(self) -> list:
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [self._read_roles()]
        return [self._write_roles()]

    @extend_schema(
        tags=["Governance"],
        summary="List vendor suspensions (SUPER_ADMIN, OPERATIONS_MANAGER)",
        responses={200: VendorSuspensionSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of vendor suspensions."""
        qs = VendorSuspension.objects.select_related(
            "vendor", "issued_by", "appeal_reviewed_by"
        ).order_by("-created_at")

        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            VendorSuspensionSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["Governance"],
        summary="Issue enforcement action against vendor (SUPER_ADMIN, OPERATIONS_MANAGER)",
        request=IssueEnforcementSerializer,
        responses={201: VendorSuspensionSerializer},
    )
    def post(self, request: Request) -> Response:
        """Issue an enforcement action (warn/suspend/ban) against a vendor."""
        serializer = IssueEnforcementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            suspension = issue_enforcement_action(
                vendor_id=str(d["vendor_id"]),
                action=d["action"],
                reason=d["reason"],
                actor=request.user,
                request=request._request,
                policy_reference=d.get("policy_reference", ""),
                suspension_days=d.get("suspension_days", 7),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=VendorSuspensionSerializer(suspension).data,
            message="Enforcement action issued.",
            status_code=status.HTTP_201_CREATED,
        )


class VendorSuspensionAppealView(APIView):
    """POST /api/v1/governance/suspensions/<pk>/appeal/ — file an appeal."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Governance"],
        summary="File appeal for a vendor suspension (any authenticated user)",
        responses={200: VendorSuspensionSerializer},
    )
    def post(self, request: Request, pk: str) -> Response:
        """File an appeal for a suspension. Must be within 7 days."""
        try:
            suspension = file_appeal(
                suspension_id=pk,
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=VendorSuspensionSerializer(suspension).data,
            message="Appeal filed. An Operations Manager will review within 24 hours.",
        )


class VendorSuspensionAppealReviewView(APIView):
    """POST /api/v1/governance/suspensions/<pk>/appeal/review/ — review an appeal."""

    permission_classes = [_GOVERNANCE_ROLES]

    @extend_schema(
        tags=["Governance"],
        summary="Review appeal for a vendor suspension (SUPER_ADMIN, OPERATIONS_MANAGER)",
        request=ProcessAppealSerializer,
        responses={200: VendorSuspensionSerializer},
    )
    def post(self, request: Request, pk: str) -> Response:
        """Approve or reject an appeal. Decision is final."""
        serializer = ProcessAppealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            suspension = process_appeal(
                suspension_id=pk,
                decision=serializer.validated_data["decision"],
                reviewer=request.user,
                request=request._request,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=VendorSuspensionSerializer(suspension).data,
            message="Appeal reviewed.",
        )


# ---------------------------------------------------------------------------
# Vendor ToS Acceptance
# ---------------------------------------------------------------------------


class VendorToSAcceptanceView(APIView):
    """POST /api/v1/governance/tos/accept/ — record ToS acceptance."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Governance"],
        summary="Record vendor ToS acceptance (any authenticated user)",
        request=RecordToSAcceptanceSerializer,
        responses={201: VendorToSAcceptanceSerializer},
    )
    def post(self, request: Request) -> Response:
        """Record that a vendor has accepted the Terms of Service."""
        serializer = RecordToSAcceptanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            acceptance = record_tos_acceptance(
                vendor_id=str(d["vendor_id"]),
                accepted_by_email=d["accepted_by_email"],
                actor=request.user,
                request=request._request,
                tos_version=d.get("tos_version", "1.0"),
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=VendorToSAcceptanceSerializer(acceptance).data,
            message="Terms of Service acceptance recorded.",
            status_code=status.HTTP_201_CREATED,
        )


class VendorToSHistoryView(APIView):
    """GET /api/v1/governance/tos/<vendor_pk>/ — ToS acceptance history for a vendor."""

    permission_classes = [_GOVERNANCE_ROLES]

    @extend_schema(
        tags=["Governance"],
        summary="List ToS acceptance history for a vendor (SUPER_ADMIN, OPERATIONS_MANAGER)",
        responses={200: VendorToSAcceptanceSerializer(many=True)},
    )
    def get(self, request: Request, vendor_pk: str) -> Response:
        """Return all ToS acceptance records for a vendor."""
        acceptances = VendorToSAcceptance.objects.filter(vendor_id=vendor_pk).order_by(
            "-accepted_at"
        )
        return success_response(
            data=VendorToSAcceptanceSerializer(acceptances, many=True).data
        )


# ---------------------------------------------------------------------------
# Consent Management
# ---------------------------------------------------------------------------


class ConsentView(APIView):
    """GET/POST /api/v1/governance/consent/ — manage GDPR consent for authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Governance"],
        summary="Get current consent state for authenticated user",
        responses={200: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        """Return the current consent state for all categories."""
        consent = get_current_consent(str(request.user.pk))
        return success_response(data=consent)

    @extend_schema(
        tags=["Governance"],
        summary="Update consent for a category (authenticated user)",
        request=UpdateConsentSerializer,
        responses={201: ConsentRecordSerializer},
    )
    def post(self, request: Request) -> Response:
        """Record a consent opt-in or opt-out for a category."""
        serializer = UpdateConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            record = record_consent(
                user_id=str(request.user.pk),
                category=d["category"],
                granted=d["granted"],
                actor=request.user,
                request=request._request,
            )
        except ValueError as e:
            return Response(
                {"success": False, "data": None, "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data=ConsentRecordSerializer(record).data,
            message="Consent updated.",
            status_code=status.HTTP_201_CREATED,
        )
