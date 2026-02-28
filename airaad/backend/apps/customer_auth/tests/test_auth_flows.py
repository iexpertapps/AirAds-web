"""
Unit tests for Authentication flows.
Tests guest mode, registration, login, JWT functionality.
"""

import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.customer_auth.models import CustomerUser, ConsentRecord, GuestToken
from apps.customer_auth.services import CustomerAuthService
from apps.customer_auth.views import (
    GuestAuthView, RegisterView, LoginView, LogoutView, 
    RefreshTokenView, VerifyOTPView, SendOTPView
)

User = get_user_model()


class CustomerAuthServiceTest(TestCase):
    """Test cases for CustomerAuthService."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = 'test@example.com'
        self.test_password = 'testpass123'
        self.test_phone = '+1234567890'
        self.test_display_name = 'Test User'
    
    def test_create_guest_token(self):
        """Test guest token creation."""
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        self.assertIsInstance(guest_token, GuestToken)
        self.assertIsNotNone(guest_token.token)
        self.assertIsInstance(guest_token.token, uuid.UUID)
        self.assertEqual(guest_token.ip_address, '192.168.1.1')
        self.assertEqual(guest_token.user_agent, 'Mozilla/5.0...')
        self.assertTrue(guest_token.is_active)
        self.assertEqual(guest_token.api_calls_count, 0)
        self.assertFalse(guest_token.is_expired)
    
    def test_register_user_success(self):
        """Test successful user registration."""
        user_data = {
            'email': self.test_email,
            'password': self.test_password,
            'display_name': self.test_display_name,
            'phone_number': self.test_phone
        }
        
        customer_user = CustomerAuthService.register_user(**user_data)
        
        self.assertIsInstance(customer_user, CustomerUser)
        self.assertEqual(customer_user.user.email, self.test_email)
        self.assertEqual(customer_user.display_name, self.test_display_name)
        self.assertEqual(customer_user.phone_number, self.test_phone)
        self.assertFalse(customer_user.is_deleted)
        self.assertIsNotNone(customer_user.created_at)
    
    def test_register_user_duplicate_email(self):
        """Test registration with duplicate email."""
        # Create existing user
        User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        
        user_data = {
            'email': self.test_email,
            'password': self.test_password,
            'display_name': self.test_display_name
        }
        
        with self.assertRaises(ValueError) as context:
            CustomerAuthService.register_user(**user_data)
        
        self.assertIn('email already exists', str(context.exception))
    
    def test_register_user_invalid_email(self):
        """Test registration with invalid email."""
        user_data = {
            'email': 'invalid-email',
            'password': self.test_password,
            'display_name': self.test_display_name
        }
        
        with self.assertRaises(ValueError) as context:
            CustomerAuthService.register_user(**user_data)
        
        self.assertIn('valid email', str(context.exception))
    
    def test_register_user_weak_password(self):
        """Test registration with weak password."""
        user_data = {
            'email': self.test_email,
            'password': '123',  # Too weak
            'display_name': self.test_display_name
        }
        
        with self.assertRaises(ValueError) as context:
            CustomerAuthService.register_user(**user_data)
        
        self.assertIn('password', str(context.exception).lower())
    
    def test_login_user_success(self):
        """Test successful user login."""
        # Create user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        
        login_data = CustomerAuthService.login_user(
            email=self.test_email,
            password=self.test_password
        )
        
        self.assertIn('access_token', login_data)
        self.assertIn('refresh_token', login_data)
        self.assertIn('user', login_data)
        self.assertEqual(login_data['user']['email'], self.test_email)
        self.assertEqual(login_data['user']['display_name'], self.test_display_name)
    
    def test_login_user_invalid_credentials(self):
        """Test login with invalid credentials."""
        # Create user
        User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        
        with self.assertRaises(ValueError) as context:
            CustomerAuthService.login_user(
                email=self.test_email,
                password='wrongpassword'
            )
        
        self.assertIn('invalid credentials', str(context.exception))
    
    def test_login_user_nonexistent(self):
        """Test login with non-existent user."""
        with self.assertRaises(ValueError) as context:
            CustomerAuthService.login_user(
                email='nonexistent@example.com',
                password=self.test_password
            )
        
        self.assertIn('invalid credentials', str(context.exception))
    
    def test_login_user_deleted(self):
        """Test login with deleted user."""
        # Create and soft delete user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        customer_user.soft_delete()
        
        with self.assertRaises(ValueError) as context:
            CustomerAuthService.login_user(
                email=self.test_email,
                password=self.test_password
            )
        
        self.assertIn('account deleted', str(context.exception))
    
    def test_upgrade_guest_to_user(self):
        """Test upgrading guest to registered user."""
        # Create guest token
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        # Create guest user with data
        guest_user = CustomerUser.objects.create(
            guest_token=guest_token.token,
            display_name='Guest User',
            behavioral_data={'search_count': 5}
        )
        
        # Register new user
        new_user_data = {
            'email': self.test_email,
            'password': self.test_password,
            'display_name': self.test_display_name
        }
        
        upgraded_user = CustomerAuthService.upgrade_guest_to_user(
            guest_token=guest_token.token,
            **new_user_data
        )
        
        self.assertIsInstance(upgraded_user, CustomerUser)
        self.assertEqual(upgraded_user.user.email, self.test_email)
        self.assertEqual(upgraded_user.display_name, self.test_display_name)
        # Guest data should be preserved
        self.assertEqual(upgraded_user.behavioral_data, {'search_count': 5})
        self.assertIsNone(upgraded_user.guest_token)
        
        # Guest token should be deactivated
        guest_token.refresh_from_db()
        self.assertFalse(guest_token.is_active)
    
    def test_validate_guest_token_valid(self):
        """Test valid guest token validation."""
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        is_valid = CustomerAuthService.validate_guest_token(guest_token.token)
        self.assertTrue(is_valid)
    
    def test_validate_guest_token_expired(self):
        """Test expired guest token validation."""
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        # Manually expire token
        guest_token.expires_at = timezone.now() - timedelta(days=1)
        guest_token.save()
        
        is_valid = CustomerAuthService.validate_guest_token(guest_token.token)
        self.assertFalse(is_valid)
    
    def test_validate_guest_token_inactive(self):
        """Test inactive guest token validation."""
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        # Deactivate token
        guest_token.is_active = False
        guest_token.save()
        
        is_valid = CustomerAuthService.validate_guest_token(guest_token.token)
        self.assertFalse(is_valid)
    
    def test_validate_guest_token_nonexistent(self):
        """Test non-existent guest token validation."""
        fake_token = uuid.uuid4()
        
        is_valid = CustomerAuthService.validate_guest_token(fake_token)
        self.assertFalse(is_valid)
    
    def test_record_consent(self):
        """Test consent recording."""
        # Create user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        
        consent = CustomerAuthService.record_consent(
            user=customer_user,
            consent_type='LOCATION',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...',
            context={'source': 'mobile_app'}
        )
        
        self.assertIsInstance(consent, ConsentRecord)
        self.assertEqual(consent.user, customer_user)
        self.assertEqual(consent.consent_type, 'LOCATION')
        self.assertTrue(consent.consented)
        self.assertEqual(consent.consent_version, '1.0')
        self.assertEqual(consent.ip_address, '192.168.1.1')
        self.assertEqual(consent.user_agent, 'Mozilla/5.0...')
        self.assertEqual(consent.context, {'source': 'mobile_app'})
        self.assertIsNotNone(consent.consented_at)
    
    def test_record_consent_guest(self):
        """Test consent recording for guest."""
        guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        consent = CustomerAuthService.record_consent(
            guest_token=guest_token.token,
            consent_type='ANALYTICS',
            consented=False,
            consent_version='1.0',
            ip_address='192.168.1.2'
        )
        
        self.assertIsInstance(consent, ConsentRecord)
        self.assertEqual(consent.guest_token, guest_token.token)
        self.assertEqual(consent.consent_type, 'ANALYTICS')
        self.assertFalse(consent.consented)
        self.assertIsNone(consent.user)
    
    def test_get_user_consent_history(self):
        """Test getting user consent history."""
        # Create user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        
        # Record multiple consents
        CustomerAuthService.record_consent(
            user=customer_user,
            consent_type='LOCATION',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1'
        )
        
        CustomerAuthService.record_consent(
            user=customer_user,
            consent_type='ANALYTICS',
            consented=False,
            consent_version='1.0',
            ip_address='192.168.1.1'
        )
        
        consent_history = CustomerAuthService.get_user_consent_history(customer_user)
        
        self.assertEqual(len(consent_history), 2)
        self.assertEqual(consent_history[0].consent_type, 'ANALYTICS')  # Most recent first
        self.assertEqual(consent_history[1].consent_type, 'LOCATION')
    
    def test_soft_delete_user(self):
        """Test user soft deletion."""
        # Create user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name,
            phone_number=self.test_phone,
            behavioral_data={'search_count': 10}
        )
        
        # Soft delete
        CustomerAuthService.soft_delete_user(customer_user)
        
        customer_user.refresh_from_db()
        self.assertTrue(customer_user.is_deleted)
        self.assertIsNotNone(customer_user.deleted_at)
        self.assertIsNone(customer_user.display_name)
        self.assertIsNone(customer_user.phone_number)
        self.assertEqual(customer_user.behavioral_data, {})
    
    def test_export_user_data(self):
        """Test user data export."""
        # Create user with data
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name,
            phone_number=self.test_phone,
            behavioral_data={'search_count': 25, 'last_search': 'pizza'}
        )
        
        # Record consents
        CustomerAuthService.record_consent(
            user=customer_user,
            consent_type='LOCATION',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1'
        )
        
        exported_data = CustomerAuthService.export_user_data(customer_user)
        
        self.assertIn('user', exported_data)
        self.assertIn('customer_user', exported_data)
        self.assertIn('consent_records', exported_data)
        self.assertIn('search_history', exported_data)
        self.assertIn('vendor_interactions', exported_data)
        
        # Check user data
        self.assertEqual(exported_data['user']['email'], self.test_email)
        self.assertEqual(exported_data['customer_user']['display_name'], self.test_display_name)
        self.assertEqual(exported_data['customer_user']['phone_number'], self.test_phone)
        self.assertEqual(exported_data['customer_user']['behavioral_data'], {'search_count': 25, 'last_search': 'pizza'})
        
        # Check consent records
        self.assertEqual(len(exported_data['consent_records']), 1)
        self.assertEqual(exported_data['consent_records'][0]['consent_type'], 'LOCATION')


class AuthenticationAPITest(APITestCase):
    """Test cases for authentication API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = 'test@example.com'
        self.test_password = 'testpass123'
        self.test_display_name = 'Test User'
        self.test_phone = '+1234567890'
    
    def test_guest_auth_endpoint(self):
        """Test guest authentication endpoint."""
        url = reverse('customer_auth:guest-auth')
        data = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0...'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('guest_token', response.data)
        self.assertIn('expires_at', response.data)
        self.assertIsInstance(uuid.UUID(response.data['guest_token']), uuid.UUID)
    
    def test_register_endpoint_success(self):
        """Test successful registration endpoint."""
        url = reverse('customer_auth:register')
        data = {
            'email': self.test_email,
            'password': self.test_password,
            'display_name': self.test_display_name,
            'phone_number': self.test_phone
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.test_email)
        self.assertEqual(response.data['user']['display_name'], self.test_display_name)
    
    def test_register_endpoint_validation_error(self):
        """Test registration endpoint with validation errors."""
        url = reverse('customer_auth:register')
        data = {
            'email': 'invalid-email',
            'password': '123',  # Too weak
            'display_name': '',  # Required
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
    
    def test_login_endpoint_success(self):
        """Test successful login endpoint."""
        # Create user first
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        
        url = reverse('customer_auth:login')
        data = {
            'email': self.test_email,
            'password': self.test_password
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.test_email)
    
    def test_login_endpoint_invalid_credentials(self):
        """Test login endpoint with invalid credentials."""
        url = reverse('customer_auth:login')
        data = {
            'email': self.test_email,
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_logout_endpoint_success(self):
        """Test successful logout endpoint."""
        # Create and authenticate user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        customer_user = CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        
        # Get tokens
        refresh = RefreshToken.for_user(user)
        
        url = reverse('customer_auth:logout')
        data = {'refresh_token': str(refresh)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_refresh_token_endpoint_success(self):
        """Test successful token refresh endpoint."""
        # Create user
        user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        CustomerUser.objects.create(
            user=user,
            display_name=self.test_display_name
        )
        
        # Get refresh token
        refresh = RefreshToken.for_user(user)
        
        url = reverse('customer_auth:refresh')
        data = {'refresh_token': str(refresh)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
    
    def test_refresh_token_endpoint_invalid(self):
        """Test token refresh endpoint with invalid token."""
        url = reverse('customer_auth:refresh')
        data = {'refresh_token': 'invalid-token'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_send_otp_endpoint(self):
        """Test send OTP endpoint."""
        url = reverse('customer_auth:send-otp')
        data = {
            'phone_number': self.test_phone,
            'purpose': 'LOGIN'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.send_otp') as mock_send_otp:
            mock_send_otp.return_value = {'session_id': 'test-session', 'expires_at': timezone.now() + timedelta(minutes=5)}
            
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('session_id', response.data)
        self.assertIn('expires_at', response.data)
    
    def test_verify_otp_endpoint_success(self):
        """Test successful OTP verification endpoint."""
        url = reverse('customer_auth:verify-otp')
        data = {
            'phone_number': self.test_phone,
            'otp_code': '123456',
            'session_id': 'test-session'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.verify_otp') as mock_verify_otp:
            mock_verify_otp.return_value = {
                'verified': True,
                'access_token': 'test-access-token',
                'refresh_token': 'test-refresh-token',
                'user': {'email': self.test_email, 'display_name': self.test_display_name}
            }
            
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('user', response.data)
    
    def test_verify_otp_endpoint_invalid(self):
        """Test OTP verification endpoint with invalid OTP."""
        url = reverse('customer_auth:verify-otp')
        data = {
            'phone_number': self.test_phone,
            'otp_code': '000000',
            'session_id': 'test-session'
        }
        
        with patch('apps.customer_auth.services.CustomerAuthService.verify_otp') as mock_verify_otp:
            mock_verify_otp.return_value = {'verified': False, 'error': 'Invalid OTP'}
            
            response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class JWTTokenTest(TransactionTestCase):
    """Test cases for JWT token functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = 'test@example.com'
        self.test_password = 'testpass123'
        
        # Create user
        self.user = User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password=self.test_password
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
    
    def test_jwt_token_generation(self):
        """Test JWT token generation."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh)
        self.assertIsInstance(str(access_token), str)
        self.assertIsInstance(str(refresh), str)
    
    def test_jwt_token_payload(self):
        """Test JWT token payload."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Decode token to check payload
        payload = access_token.payload
        
        self.assertIn('user_id', payload)
        self.assertEqual(payload['user_id'], self.user.id)
        self.assertIn('exp', payload)  # Expiration time
        self.assertIn('iat', payload)  # Issued at time
    
    def test_jwt_token_refresh(self):
        """Test JWT token refresh."""
        refresh = RefreshToken.for_user(self.user)
        
        # Refresh token
        new_access_token = refresh.access_token
        
        self.assertIsNotNone(new_access_token)
        self.assertNotEqual(str(new_access_token), str(refresh.access_token))
    
    def test_jwt_token_blacklist(self):
        """Test JWT token blacklisting."""
        refresh = RefreshToken.for_user(self.user)
        
        # Blacklist refresh token
        refresh.blacklist()
        
        # Try to use blacklisted token
        with self.assertRaises(Exception):
            # This should raise an exception when trying to use blacklisted token
            refresh.access_token


class ConsentManagementTest(TestCase):
    """Test cases for consent management."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='test@example.com',
            password='testpass123'
        )
        self.customer_user = CustomerUser.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        self.guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
    
    def test_consent_types(self):
        """Test all consent types."""
        consent_types = ['LOCATION', 'ANALYTICS', 'MARKETING', 'TERMS', 'PRIVACY', 'VOICE']
        
        for consent_type in consent_types:
            consent = CustomerAuthService.record_consent(
                user=self.customer_user,
                consent_type=consent_type,
                consented=True,
                consent_version='1.0',
                ip_address='192.168.1.1'
            )
            
            self.assertEqual(consent.consent_type, consent_type)
    
    def test_consent_versioning(self):
        """Test consent versioning."""
        # Record consent with version 1.0
        consent_v1 = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='LOCATION',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1'
        )
        
        # Record consent with version 2.0
        consent_v2 = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='LOCATION',
            consented=False,
            consent_version='2.0',
            ip_address='192.168.1.1'
        )
        
        self.assertEqual(consent_v1.consent_version, '1.0')
        self.assertEqual(consent_v2.consent_version, '2.0')
        self.assertTrue(consent_v1.consented)
        self.assertFalse(consent_v2.consented)
    
    def test_consent_context_storage(self):
        """Test consent context storage."""
        context = {
            'source': 'mobile_app',
            'campaign': 'spring2024',
            'referrer': 'google',
            'user_session_id': 'sess_123456',
            'device_info': {
                'platform': 'ios',
                'version': '1.0.0'
            }
        }
        
        consent = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='MARKETING',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1',
            context=context
        )
        
        self.assertEqual(consent.context, context)
    
    def test_guest_consent_tracking(self):
        """Test guest consent tracking."""
        consent = CustomerAuthService.record_consent(
            guest_token=self.guest_token.token,
            consent_type='ANALYTICS',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.2'
        )
        
        self.assertEqual(consent.guest_token, self.guest_token.token)
        self.assertIsNone(consent.user)
    
    def test_consent_withdrawal(self):
        """Test consent withdrawal."""
        # Record initial consent
        consent = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='MARKETING',
            consented=True,
            consent_version='1.0',
            ip_address='192.168.1.1'
        )
        
        # Withdraw consent
        withdrawn_consent = CustomerAuthService.record_consent(
            user=self.customer_user,
            consent_type='MARKETING',
            consented=False,
            consent_version='1.0',
            ip_address='192.168.1.1'
        )
        
        self.assertTrue(consent.consented)
        self.assertFalse(withdrawn_consent.consented)
        
        # Check consent history
        history = CustomerAuthService.get_user_consent_history(self.customer_user)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].consented, False)  # Most recent first
        self.assertEqual(history[1].consented, True)


class GuestTokenLifecycleTest(TestCase):
    """Test cases for guest token lifecycle."""
    
    def setUp(self):
        """Set up test data."""
        self.guest_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
    
    def test_guest_token_expiration(self):
        """Test guest token expiration."""
        # Initially not expired
        self.assertFalse(self.guest_token.is_expired)
        
        # Manually expire token
        self.guest_token.expires_at = timezone.now() - timedelta(days=1)
        self.guest_token.save()
        
        # Should be expired
        self.assertTrue(self.guest_token.is_expired)
    
    def test_guest_token_extension(self):
        """Test guest token extension."""
        original_expiry = self.guest_token.expires_at
        
        # Extend token
        self.guest_token.extend_expiry(days=7)
        
        self.guest_token.refresh_from_db()
        self.assertGreater(self.guest_token.expires_at, original_expiry)
    
    def test_guest_token_usage_tracking(self):
        """Test guest token usage tracking."""
        # Initially zero usage
        self.assertEqual(self.guest_token.api_calls_count, 0)
        
        # Increment usage
        self.guest_token.api_calls_count += 1
        self.guest_token.save()
        
        self.guest_token.refresh_from_db()
        self.assertEqual(self.guest_token.api_calls_count, 1)
        
        # Check last used timestamp
        self.assertIsNotNone(self.guest_token.last_used_at)
    
    def test_guest_token_deactivation(self):
        """Test guest token deactivation."""
        # Initially active
        self.assertTrue(self.guest_token.is_active)
        
        # Deactivate token
        self.guest_token.is_active = False
        self.guest_token.save()
        
        self.guest_token.refresh_from_db()
        self.assertFalse(self.guest_token.is_active)
    
    def test_guest_token_cleanup(self):
        """Test guest token cleanup."""
        # Create expired token
        expired_token = CustomerAuthService.create_guest_token(
            ip_address='192.168.1.2',
            user_agent='Mozilla/5.0...'
        )
        expired_token.expires_at = timezone.now() - timedelta(days=1)
        expired_token.save()
        
        # Clean up expired tokens
        cleaned_count = CustomerAuthService.cleanup_expired_tokens()
        
        self.assertGreaterEqual(cleaned_count, 1)
        
        # Verify expired token is deleted
        with self.assertRaises(GuestToken.DoesNotExist):
            GuestToken.objects.get(token=expired_token.token)
