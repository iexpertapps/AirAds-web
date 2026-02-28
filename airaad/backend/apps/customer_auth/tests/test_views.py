"""
API Layer tests for Customer Authentication Views.
Tests auth flows, JWT tokens, consent recording, and GDPR compliance.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.customer_auth.models import CustomerUser, GuestToken, ConsentRecord

User = get_user_model()


class GuestTokenViewTest(TestCase):
    """Test cases for GuestTokenView."""
    
    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
    
    def test_create_guest_token_success(self):
        """Test successful guest token creation."""
        response = self.client.post('/api/v1/customer-auth/guest/')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('token', response.data['data'])
        self.assertIn('expires_at', response.data['data'])
    
    def test_validate_guest_token_success(self):
        """Test successful guest token validation."""
        # Create a guest token first
        guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        response = self.client.get(
            '/api/v1/customer-auth/guest/',
            HTTP_X_GUEST_TOKEN=str(guest_token.token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertTrue(response.data['data']['valid'])
    
    def test_validate_guest_token_missing(self):
        """Test validation fails when token is missing."""
        response = self.client.get('/api/v1/customer-auth/guest/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_validate_guest_token_expired(self):
        """Test validation fails for expired token."""
        # Create an expired guest token
        guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        response = self.client.get(
            '/api/v1/customer-auth/guest/',
            HTTP_X_GUEST_TOKEN=str(guest_token.token)
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])


class CustomerRegistrationViewTest(TestCase):
    """Test cases for CustomerRegistrationView."""
    
    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
    
    def test_registration_success(self):
        """Test successful customer registration."""
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'display_name': 'New User'
        }
        
        response = self.client.post('/api/v1/customer-auth/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])
        self.assertEqual(response.data['data']['user']['email'], 'newuser@example.com')
    
    def test_registration_missing_email(self):
        """Test registration fails without email."""
        data = {
            'password': 'SecurePass123!',
            'display_name': 'New User'
        }
        
        response = self.client.post('/api/v1/customer-auth/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_registration_missing_password(self):
        """Test registration fails without password."""
        data = {
            'email': 'newuser@example.com',
            'display_name': 'New User'
        }
        
        response = self.client.post('/api/v1/customer-auth/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_registration_invalid_email(self):
        """Test registration fails with invalid email."""
        data = {
            'email': 'invalid-email',
            'password': 'SecurePass123!',
            'display_name': 'New User'
        }
        
        response = self.client.post('/api/v1/customer-auth/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_registration_duplicate_email(self):
        """Test registration fails with duplicate email."""
        # Create existing user
        User.objects.create_user(
            email='existing@example.com',
            username='existing@example.com',
            password='pass123'
        )
        
        data = {
            'email': 'existing@example.com',
            'password': 'SecurePass123!',
            'display_name': 'New User'
        }
        
        response = self.client.post('/api/v1/customer-auth/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_registration_with_guest_token(self):
        """Test registration with guest token migration."""
        # Create guest token
        guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'display_name': 'New User',
            'guest_token': str(guest_token.token)
        }
        
        response = self.client.post('/api/v1/customer-auth/register/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])


class CustomerLoginViewTest(TestCase):
    """Test cases for CustomerLoginView."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
    
    def test_login_success(self):
        """Test successful login."""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/v1/customer-auth/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])
        self.assertIn('access', response.data['data']['tokens'])
        self.assertIn('refresh', response.data['data']['tokens'])
    
    def test_login_wrong_password(self):
        """Test login fails with wrong password."""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post('/api/v1/customer-auth/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
    
    def test_login_nonexistent_user(self):
        """Test login fails for nonexistent user."""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/v1/customer-auth/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
    
    def test_login_missing_email(self):
        """Test login fails without email."""
        data = {
            'password': 'testpass123'
        }
        
        response = self.client.post('/api/v1/customer-auth/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_login_missing_password(self):
        """Test login fails without password."""
        data = {
            'email': 'test@example.com'
        }
        
        response = self.client.post('/api/v1/customer-auth/login/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])


class CustomerLogoutViewTest(TestCase):
    """Test cases for CustomerLogoutView."""
    
    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_logout_success(self):
        """Test successful logout."""
        data = {
            'refresh_token': 'fake-refresh-token'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.logout_customer') as mock_logout:
            mock_logout.return_value = True
            
            response = self.client.post('/api/v1/customer-auth/logout/', data)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
    
    def test_logout_missing_token(self):
        """Test logout fails without refresh token."""
        response = self.client.post('/api/v1/customer-auth/logout/', {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_logout_unauthenticated(self):
        """Test logout fails without authentication."""
        self.client.force_authenticate(user=None)
        
        data = {
            'refresh_token': 'fake-refresh-token'
        }
        
        response = self.client.post('/api/v1/customer-auth/logout/', data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetViewTest(TestCase):
    """Test cases for Password Reset views."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
    
    def test_password_reset_request_success(self):
        """Test password reset request."""
        data = {
            'email': 'test@example.com'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.request_password_reset') as mock_reset:
            mock_reset.return_value = True
            
            response = self.client.post('/api/v1/customer-auth/password-reset/', data)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
    
    def test_password_reset_request_nonexistent_email(self):
        """Test password reset with nonexistent email (should still return success)."""
        data = {
            'email': 'nonexistent@example.com'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.request_password_reset') as mock_reset:
            mock_reset.return_value = False
            
            # Should still return success to prevent email enumeration
            response = self.client.post('/api/v1/customer-auth/password-reset/', data)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
    
    def test_password_reset_confirm_success(self):
        """Test password reset confirmation."""
        data = {
            'token': 'fake-reset-token',
            'new_password': 'NewSecurePass123!'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.confirm_password_reset') as mock_confirm:
            mock_confirm.return_value = True
            
            response = self.client.post('/api/v1/customer-auth/password-reset/confirm/', data)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
    
    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirmation with invalid token."""
        data = {
            'token': 'invalid-token',
            'new_password': 'NewSecurePass123!'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.confirm_password_reset') as mock_confirm:
            mock_confirm.return_value = False
            
            response = self.client.post('/api/v1/customer-auth/password-reset/confirm/', data)
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertFalse(response.data['success'])


class CustomerProfileViewTest(TestCase):
    """Test cases for CustomerProfileView."""
    
    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User',
            phone_number='+923001234567'
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_get_profile_success(self):
        """Test successful profile retrieval."""
        response = self.client.get('/api/v1/customer-auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['email'], 'test@example.com')
        self.assertEqual(response.data['data']['display_name'], 'Test User')
    
    def test_get_profile_unauthenticated(self):
        """Test profile retrieval fails without authentication."""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/v1/customer-auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ConsentRecordViewTest(TestCase):
    """Test cases for ConsentRecordView."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
    
    def test_record_consent_authenticated(self):
        """Test consent recording for authenticated user."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'consent_type': 'LOCATION',
            'consented': True,
            'consent_version': '1.0'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.record_consent') as mock_consent:
            mock_consent.return_value = True
            
            response = self.client.post('/api/v1/customer-auth/consent/', data)
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['success'])
    
    def test_record_consent_guest(self):
        """Test consent recording for guest user."""
        guest_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        data = {
            'consent_type': 'ANALYTICS',
            'consented': True,
            'consent_version': '1.0'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.record_consent') as mock_consent:
            mock_consent.return_value = True
            
            response = self.client.post(
                '/api/v1/customer-auth/consent/',
                data,
                HTTP_X_GUEST_TOKEN=str(guest_token.token)
            )
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data['success'])
    
    def test_record_consent_missing_type(self):
        """Test consent recording fails without consent type."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'consented': True
        }
        
        response = self.client.post('/api/v1/customer-auth/consent/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_record_consent_guest_missing_token(self):
        """Test consent recording fails for guest without token."""
        data = {
            'consent_type': 'LOCATION',
            'consented': True
        }
        
        response = self.client.post('/api/v1/customer-auth/consent/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])


class AccountExportViewTest(TestCase):
    """Test cases for AccountExportView (GDPR compliance)."""
    
    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_export_data_success(self):
        """Test successful data export."""
        with patch('apps.customer_auth.services.CustomerAuthService.export_user_data') as mock_export:
            mock_export.return_value = {
                'user': {'email': 'test@example.com'},
                'preferences': {},
                'history': []
            }
            
            response = self.client.get('/api/v1/customer-auth/account/export/')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response['Content-Type'], 'application/json')
            self.assertIn('attachment', response['Content-Disposition'])
    
    def test_export_data_unauthenticated(self):
        """Test data export fails without authentication."""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/v1/customer-auth/account/export/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AccountDeleteViewTest(TestCase):
    """Test cases for AccountDeleteView (GDPR right to erasure)."""
    
    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_delete_account_success(self):
        """Test successful account deletion."""
        data = {
            'confirmation_code': 'DELETE_MY_ACCOUNT'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.delete_user_account') as mock_delete:
            mock_delete.return_value = True
            
            response = self.client.delete('/api/v1/customer-auth/account/', data)
            
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(response.data['success'])
    
    def test_delete_account_missing_confirmation(self):
        """Test account deletion fails without confirmation code."""
        response = self.client.delete('/api/v1/customer-auth/account/', {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_delete_account_unauthenticated(self):
        """Test account deletion fails without authentication."""
        self.client.force_authenticate(user=None)
        
        data = {
            'confirmation_code': 'DELETE_MY_ACCOUNT'
        }
        
        response = self.client.delete('/api/v1/customer-auth/delete/', data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
