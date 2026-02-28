"""
AirAd Backend — Payments URL Configuration
Mounted at: /api/v1/payments/

7 endpoints per BACKEND_MASTER_PLAN.md §8:
- create-checkout, create-portal-session, webhook
- subscription-status, invoices, cancel, resume
"""

from django.urls import path

from .views import (
    CancelSubscriptionView,
    CreateCheckoutView,
    CreatePortalSessionView,
    InvoiceListView,
    ResumeSubscriptionView,
    StripeWebhookView,
    SubscriptionStatusView,
)

urlpatterns = [
    path("create-checkout/", CreateCheckoutView.as_view(), name="payments-create-checkout"),
    path("create-portal-session/", CreatePortalSessionView.as_view(), name="payments-create-portal"),
    path("webhook/", StripeWebhookView.as_view(), name="payments-webhook"),
    path("subscription-status/", SubscriptionStatusView.as_view(), name="payments-subscription-status"),
    path("invoices/", InvoiceListView.as_view(), name="payments-invoices"),
    path("cancel/", CancelSubscriptionView.as_view(), name="payments-cancel"),
    path("resume/", ResumeSubscriptionView.as_view(), name="payments-resume"),
]
