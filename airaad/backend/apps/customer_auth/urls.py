from django.urls import path
from . import views

app_name = 'customer_auth'

urlpatterns = [
    # Guest token management
    path('guest/', views.GuestTokenView.as_view(), name='guest_token'),
    
    # Registration and authentication
    path('register/', views.CustomerRegistrationView.as_view(), name='register'),
    path('verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('login/', views.CustomerLoginView.as_view(), name='login'),
    path('logout/', views.CustomerLogoutView.as_view(), name='logout'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password reset
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Profile and account management
    path('me/', views.CustomerProfileView.as_view(), name='profile'),
    path('account/export/', views.AccountExportView.as_view(), name='account_export'),
    path('account/', views.AccountDeleteView.as_view(), name='account_delete'),
    
    # GDPR consent
    path('consent/', views.ConsentRecordView.as_view(), name='consent_record'),
]
