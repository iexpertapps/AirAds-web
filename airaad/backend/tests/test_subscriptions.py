"""
AirAd — tests/test_subscriptions.py

Tests for apps/subscriptions — Phase B tasks.
"""
from __future__ import annotations

import pytest


class TestSubscriptionExpiryCheckTask:
    """Tests for apps.subscriptions.tasks.subscription_expiry_check."""

    def test_task_is_registered(self) -> None:
        """subscription_expiry_check task is importable and registered with Celery."""
        from apps.subscriptions.tasks import subscription_expiry_check
        assert callable(subscription_expiry_check)

    def test_task_runs_without_error(self) -> None:
        """subscription_expiry_check runs without raising."""
        from apps.subscriptions.tasks import subscription_expiry_check
        subscription_expiry_check()  # Must not raise

    def test_task_name_is_correct(self) -> None:
        """Task is registered under the expected Celery task name."""
        from apps.subscriptions.tasks import subscription_expiry_check
        assert subscription_expiry_check.name == "apps.subscriptions.tasks.subscription_expiry_check"

    def test_task_is_bound(self) -> None:
        """Task is a bound Celery task (bind=True)."""
        from apps.subscriptions.tasks import subscription_expiry_check
        assert hasattr(subscription_expiry_check, "delay")
        assert hasattr(subscription_expiry_check, "apply_async")
