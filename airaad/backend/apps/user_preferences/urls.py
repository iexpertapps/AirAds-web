from django.urls import path
from . import views

app_name = 'user_preferences'

urlpatterns = [
    # User preferences
    path('preferences/', views.UserPreferenceView.as_view(), name='preferences'),
    
    # Search history
    path('search-history/', views.SearchHistoryView.as_view(), name='search_history'),
    
    # Interaction tracking
    path('interactions/', views.InteractionTrackingView.as_view(), name='interaction_tracking'),
    
    # Reel view tracking
    path('reel-views/', views.ReelViewTrackingView.as_view(), name='reel_view_tracking'),
    
    # Flash deal alerts
    path('flash-alerts/', views.FlashDealAlertView.as_view(), name='flash_deal_alerts'),
    
    # Guest data migration (internal)
    path('migrate/', views.MigrationView.as_view(), name='migrate_guest_data'),
    
    # User statistics
    path('stats/', views.UserStatsView.as_view(), name='user_stats'),
]
