from django.urls import path
from . import views
from .views_metrics import MetricsView, HealthMetricsView, BusinessMetricsView
from .business_dashboard import BusinessMetricsDashboard
from .views_health import SystemHealthView, HealthSummaryView, ComponentHealthView
from .views_alerts import AlertTriggerView, ActiveAlertsView, AlertAcknowledgeView, AlertResolveView, AlertCheckView
from .views_uptime import UptimeCheckView, UptimeStatisticsView, UptimeHistoryView, UptimeStatusView

app_name = 'user_portal'

urlpatterns = [
    # Discovery endpoints
    path('nearby/vendors/', views.NearbyVendorsView.as_view(), name='nearby-vendors'),
    path('nearby/ar-markers/', views.ARMarkersView.as_view(), name='ar-markers'),
    path('vendors/<uuid:pk>/', views.VendorDetailView.as_view(), name='vendor-detail'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('search/voice/', views.VoiceSearchView.as_view(), name='voice-search'),
    path('tags/', views.TagsView.as_view(), name='tags'),
    path('promotions/strip/', views.PromotionsStripView.as_view(), name='promotions-strip'),
    path('cities/', views.CitiesView.as_view(), name='cities'),
    path('flash-deals/', views.FlashDealsView.as_view(), name='flash-deals'),
    path('nearby/reels/', views.NearbyReelsView.as_view(), name='nearby-reels'),
    
    # Metrics endpoints
    path('metrics/', MetricsView.as_view(), name='prometheus-metrics'),
    path('metrics/health/', HealthMetricsView.as_view(), name='health-metrics'),
    path('metrics/business/', BusinessMetricsView.as_view(), name='business-metrics'),
    
    # Dashboard endpoints
    path('dashboard/', BusinessMetricsDashboard.as_view(), name='business-dashboard'),
    
    # Health endpoints
    path('health/', SystemHealthView.as_view(), name='system-health'),
    path('health/summary/', HealthSummaryView.as_view(), name='health-summary'),
    path('health/<str:component>/', ComponentHealthView.as_view(), name='component-health'),
    
    # Alert endpoints
    path('alerts/trigger/', AlertTriggerView.as_view(), name='alert-trigger'),
    path('alerts/active/', ActiveAlertsView.as_view(), name='active-alerts'),
    path('alerts/<str:alert_id>/acknowledge/', AlertAcknowledgeView.as_view(), name='alert-acknowledge'),
    path('alerts/<str:alert_id>/resolve/', AlertResolveView.as_view(), name='alert-resolve'),
    path('alerts/check/', AlertCheckView.as_view(), name='alert-check'),
    
    # Uptime endpoints
    path('uptime/check/', UptimeCheckView.as_view(), name='uptime-check'),
    path('uptime/statistics/', UptimeStatisticsView.as_view(), name='uptime-statistics'),
    path('uptime/history/', UptimeHistoryView.as_view(), name='uptime-history'),
    path('uptime/status/', UptimeStatusView.as_view(), name='uptime-status'),
]
