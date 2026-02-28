"""
Notifications App URLs
"""

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('templates/', views.NotificationTemplateListView.as_view(), name='template-list'),
    path('logs/', views.NotificationLogListView.as_view(), name='log-list'),
]
