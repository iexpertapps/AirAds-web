"""
AirAd Backend — Tags Service Layer (R4)

SYSTEM tags cannot be created, edited, or deleted via API — enforced here.
slug is immutable after creation — enforced here.
Every mutation calls log_action() (R5).
"""

import logging
from typing import Any

from apps.audit.utils import log_action
from django.db import transaction
from django.http import HttpRequest

from .models import Tag, TagType

logger = logging.getLogger(__name__)

_IMMUTABLE_SLUG_ERROR = "Tag slug is immutable and cannot be changed after creation"
_SYSTEM_TAG_ERROR = "SYSTEM tags cannot be created, edited, or deleted via the API"


def _reject_system_tag(tag: Tag) -> None:
    """Raise PermissionError if the tag is a SYSTEM tag.

    Args:
        tag: Tag instance to check.

    Raises:
        PermissionError: If tag_type is SYSTEM.
    """
    if tag.is_system:
        raise PermissionError(_SYSTEM_TAG_ERROR)


@transaction.atomic
def create_tag(
    name: str,
    slug: str,
    tag_type: str,
    actor: Any,
    request: HttpRequest,
    display_label: str = "",
    display_order: int = 0,
    icon_name: str = "",
    expires_at: Any | None = None,
) -> Tag:
    """Create a new Tag. SYSTEM tags cannot be created via API.

    Args:
        name: Human-readable tag name.
        slug: URL-safe identifier — immutable after creation.
        tag_type: One of TagType values. SYSTEM is rejected.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.
        display_label: Optional UI display string.
        display_order: Optional ordering integer.
        icon_name: Optional icon identifier.

    Returns:
        Newly created Tag instance.

    Raises:
        PermissionError: If tag_type is SYSTEM.
        ValueError: If slug is already in use.
    """
    if tag_type == TagType.SYSTEM:
        raise PermissionError(_SYSTEM_TAG_ERROR)

    slug = slug.strip()
    if Tag.objects.filter(slug=slug).exists():
        raise ValueError(f"Tag with slug '{slug}' already exists")

    tag = Tag.objects.create(
        name=name.strip(),
        slug=slug,
        tag_type=tag_type,
        display_label=display_label or name.strip(),
        display_order=display_order,
        icon_name=icon_name,
        expires_at=expires_at,
    )
    log_action(
        action="TAG_CREATED",
        actor=actor,
        target_obj=tag,
        request=request,
        before={},
        after={"name": tag.name, "slug": tag.slug, "tag_type": tag.tag_type},
    )
    return tag


@transaction.atomic
def update_tag(
    tag: Tag,
    updates: dict[str, Any],
    actor: Any,
    request: HttpRequest,
) -> Tag:
    """Update a Tag. SYSTEM tags and slug changes are rejected.

    Args:
        tag: Tag instance to update.
        updates: Dict of field names to new values. 'slug' and 'tag_type=SYSTEM' rejected.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Returns:
        Updated Tag instance.

    Raises:
        PermissionError: If tag is a SYSTEM tag.
        ValueError: If 'slug' is included in updates.
    """
    _reject_system_tag(tag)

    if "slug" in updates:
        raise ValueError(_IMMUTABLE_SLUG_ERROR)
    if updates.get("tag_type") == TagType.SYSTEM:
        raise PermissionError(_SYSTEM_TAG_ERROR)

    before = {
        "name": tag.name,
        "display_label": tag.display_label,
        "is_active": tag.is_active,
    }

    allowed_fields = {
        "name",
        "display_label",
        "display_order",
        "icon_name",
        "is_active",
        "tag_type",
        "expires_at",
    }
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(tag, field, value)

    tag.save()
    log_action(
        action="TAG_UPDATED",
        actor=actor,
        target_obj=tag,
        request=request,
        before=before,
        after={"name": tag.name, "is_active": tag.is_active},
    )
    return tag


@transaction.atomic
def delete_tag(tag: Tag, actor: Any, request: HttpRequest) -> None:
    """Delete a Tag. SYSTEM tags cannot be deleted.

    Args:
        tag: Tag instance to delete.
        actor: AdminUser performing the action.
        request: HTTP request for audit tracing.

    Raises:
        PermissionError: If tag is a SYSTEM tag.
    """
    _reject_system_tag(tag)

    tag_id = str(tag.id)
    tag_name = tag.name
    tag.delete()

    log_action(
        action="TAG_DELETED",
        actor=actor,
        target_obj=None,
        request=request,
        before={"id": tag_id, "name": tag_name},
        after={},
    )
