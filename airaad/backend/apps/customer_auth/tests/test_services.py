"""
Unit tests for Customer Authentication services.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError

from ..services import CustomerAuthService
from ..models import CustomerUser, ConsentRecord, GuestToken
from ..security import SecurityUtils
from ..exceptions import (
    AuthenticationFailedException,
    InvalidTokenException,
    UserAlreadyExistsException,
    PasswordValidationException,
)

User = get_user_model()


class CustomerAuthServiceTest(TestCase):
    """Test cases for CustomerAuthService."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = 'test@example.com'
        self.test_password = 'TestPass123!'
        self.test_ip = '192.168.1.1'
        self.test_user_agent = 'TestAgent/1.0'
        
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test."""
        cache.clear()
    
    def test_create_guest_token(self):
        """Test guest token creation."""
        result = CustomerAuthService.create_guest_token(
            ip_address=self.test_ip,
            user_agent=self.test_user_agent
        )
        
        self.assertIn('guest_token', result)
        self.assertIn('expires_at', result)
        self.assertIn('expires_in_seconds', result)
        
        # Verify token exists in database
        guest_token_uuid = uuid.UUID(result['guest_token'])
        guest_token = GuestToken.objects.get(token=guest_token_uuid)
        
        self.assertTrue(guest_token.is_active)
        self.assertEqual(guest_token.ip_address, SecurityUtils.hash_ip_address(self.test_ip))
        self.assertEqual(guest_token.user_agent, self.test_user_agent)
    
    def test_validate_guest_token_valid(self):
        """Test valid guest token validation."""
        # Create guest token
        result = CustomerAuthService.create_guest_token()
        guest_token_str = result['guest_token']
        
        # Validate token
        guest_token_obj = CustomerAuthService.validate_guest_token(guest_token_str)
        
        self.assertIsNotNone(guest_token_obj)
        self.assertTrue(guest_token_obj.is_active)
        self.assertFalse(guest_token_obj.is_expired)
    
    def test_validate_guest_token_invalid(self):
        """Test invalid guest token validation."""
        invalid_token = str(uuid.uuid4())
        
        result = CustomerAuthService.validate_guest_token(invalid_token)
        
        self.assertIsNone(result)
    
    def test_validate_guest_token_expired(self):
        """Test expired guest token validation."""
        # Create expired guest token
        expired_token = GuestToken.objects.create(
            token=uuid.uuid4(),
            expires_at=timezone.now() - timedelta(days=1),
        )
        
        result = CustomerAuthService.validate_guest_token(str(expired_token.token))
        
        self.assertIsNone(result)
        
        # Token should be marked as inactive
        expired_token.refresh_from_db()
        self.assertFalse(expired_token.is_active)
    
    def test_register_customer_success(self):
        """Test successful customer registration."""
        result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            display_name='Test User',
            phone_number='+1234567890',
            ip_address=self.test_ip,
            user_agent=self.test_user_agent
        )
        
        self.assertIn('customer_user', result)
        self.assertIn('tokens', result)
        self.assertTrue(result['requires_email_verification'])
        
        # Check customer user was created
        customer_user = result['customer_user']
        self.assertEqual(customer_user.user.email, self.test_email)
        self.assertEqual(customer_user.display_name, 'Test User')
        self.assertEqual(customer_user.phone_number, '+1234567890')
        
        # Check tokens were generated
        tokens = result['tokens']
        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
        
        # Check consent records were created
        consent_records = ConsentRecord.objects.filter(user=customer_user)
        self.assertEqual(consent_records.count(), 2)  # TERMS and ANALYTICS
    
    def test_register_customer_existing_email(self):
        """Test registration with existing email."""
        # Create existing user
        User.objects.create_user(
            email=self.test_email,
            username=self.test_email,
            password='existingpass'
        )
        
        with self.assertRaises(UserAlreadyExistsException):
            CustomerAuthService.register_customer(
                email=self.test_email,
                password=self.test_password,
                ip_address=self.test_ip
            )
    
    def test_register_customer_weak_password(self):
        """Test registration with weak password."""
        weak_passwords = ['123', 'password', 'weak', 'test']
        
        for weak_password in weak_passwords:
            with self.assertRaises(PasswordValidationException):
                CustomerAuthService.register_customer(
                    email='test2@example.com',
                    password=weak_password,
                    ip_address=self.test_ip
                )
    
    def test_register_customer_with_guest_token(self):
        """Test registration with guest token migration."""
        # Create guest token
        guest_result = CustomerAuthService.create_guest_token()
        guest_token_str = guest_result['guest_token']
        
        # Register customer with guest token
        result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            guest_token_str=guest_token_str,
            ip_address=self.test_ip
        )
        
        self.assertIn('customer_user', result)
        
        # Guest token should be invalidated
        guest_token_obj = CustomerAuthService.validate_guest_token(guest_token_str)
        self.assertIsNone(guest_token_obj)
    
    def test_login_customer_success(self):
        """Test successful customer login."""
        # Create customer first
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        
        # Activate the user (bypass email verification for test)
        customer_user = register_result['customer_user']
        customer_user.user.is_active = True
        customer_user.user.save()
        
        # Login
        result = CustomerAuthService.login_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip,
            user_agent=self.test_user_agent
        )
        
        self.assertIn('customer_user', result)
        self.assertIn('tokens', result)
        self.assertFalse(result['is_new_user'])
        
        # Check tokens
        tokens = result['tokens']
        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
    
    def test_login_customer_invalid_credentials(self):
        """Test login with invalid credentials."""
        with self.assertRaises(AuthenticationFailedException):
            CustomerAuthService.login_customer(
                email=self.test_email,
                password='wrongpassword',
                ip_address=self.test_ip
            )
    
    def test_login_customer_inactive_user(self):
        """Test login with inactive user."""
        # Create customer but keep inactive
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        
        with self.assertRaises(AuthenticationFailedException):
            CustomerAuthService.login_customer(
                email=self.test_email,
                password=self.test_password,
                ip_address=self.test_ip
            )
    
    def test_login_customer_with_guest_token(self):
        """Test login with guest token migration."""
        # Create guest token
        guest_result = CustomerAuthService.create_guest_token()
        guest_token_str = guest_result['guest_token']
        
        # Create and activate customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        customer_user.user.is_active = True
        customer_user.user.save()
        
        # Login with guest token
        result = CustomerAuthService.login_customer(
            email=self.test_email,
            password=self.test_password,
            guest_token_str=guest_token_str,
            ip_address=self.test_ip
        )
        
        self.assertIn('customer_user', result)
        
        # Guest token should be invalidated
        guest_token_obj = CustomerAuthService.validate_guest_token(guest_token_str)
        self.assertIsNone(guest_token_obj)
    
    def test_verify_email_success(self):
        """Test successful email verification."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        
        # Generate verification token (mock JWT)
        with patch('rest_framework_simplejwt.tokens.AccessToken') as mock_token:
            mock_token.return_value.payload = {'user_id': register_result['customer_user'].user.id}
            mock_token.return_value.get.return_value = 'user-portal'
            
            token = 'mock_verification_token'
            result = CustomerAuthService.verify_email(token)
            
            self.assertTrue(result)
    
    def test_verify_email_invalid_token(self):
        """Test email verification with invalid token."""
        with patch('rest_framework_simplejwt.tokens.AccessToken') as mock_token:
            mock_token.side_effect = Exception("Invalid token")
            
            token = 'invalid_token'
            result = CustomerAuthService.verify_email(token)
            
            self.assertFalse(result)
    
    def test_refresh_token_success(self):
        """Test successful token refresh."""
        # Create customer and login
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        customer_user.user.is_active = True
        customer_user.user.save()
        
        login_result = CustomerAuthService.login_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        refresh_token = login_result['tokens']['refresh_token']
        
        # Refresh token
        result = CustomerAuthService.refresh_token(refresh_token)
        
        self.assertIn('access_token', result)
        self.assertIn('access_token_expires_in', result)
    
    def test_refresh_token_invalid(self):
        """Test token refresh with invalid token."""
        with self.assertRaises(InvalidTokenException):
            CustomerAuthService.refresh_token('invalid_refresh_token')
    
    def test_logout_customer_success(self):
        """Test successful customer logout."""
        # Create customer and login
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        customer_user.user.is_active = True
        customer_user.user.save()
        
        login_result = CustomerAuthService.login_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        refresh_token = login_result['tokens']['refresh_token']
        
        # Logout
        result = CustomerAuthService.logout_customer(refresh_token)
        
        self.assertTrue(result)
    
    def test_logout_customer_invalid_token(self):
        """Test logout with invalid token."""
        result = CustomerAuthService.logout_customer('invalid_refresh_token')
        
        self.assertFalse(result)
    
    def test_request_password_reset_success(self):
        """Test successful password reset request."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        customer_user.user.is_active = True
        customer_user.user.save()
        
        result = CustomerAuthService.request_password_reset(self.test_email)
        
        self.assertIsNotNone(result)
        self.assertIn('reset_token', result)
        self.assertIn('expires_in', result)
    
    def test_request_password_reset_nonexistent_email(self):
        """Test password reset for non-existent email."""
        result = CustomerAuthService.request_password_reset('nonexistent@example.com')
        
        # Should return None but not raise exception (security)
        self.assertIsNone(result)
    
    def test_confirm_password_reset_success(self):
        """Test successful password reset confirmation."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        customer_user.user.is_active = True
        customer_user.user.save()
        
        # Request reset
        reset_result = CustomerAuthService.request_password_reset(self.test_email)
        reset_token = reset_result['reset_token']
        
        # Confirm reset
        new_password = 'NewPassword123!'
        result = CustomerAuthService.confirm_password_reset(reset_token, new_password)
        
        self.assertTrue(result)
        
        # Verify password was changed
        user = User.objects.get(email=self.test_email)
        self.assertTrue(user.check_password(new_password))
    
    def test_confirm_password_reset_invalid_token(self):
        """Test password reset with invalid token."""
        with self.assertRaises(Exception):  # Should raise ValueError
            CustomerAuthService.confirm_password_reset('invalid_token', 'NewPassword123!')
    
    def test_export_user_data_success(self):
        """Test successful user data export."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        
        # Export data
        export_data = CustomerAuthService.export_user_data(customer_user)
        
        self.assertIn('account', export_data)
        self.assertIn('preferences', export_data)
        self.assertIn('consent_records', export_data)
        self.assertIn('search_history', export_data)
        self.assertIn('interactions', export_data)
        self.assertIn('reel_views', export_data)
        
        # Check export request was recorded
        customer_user.refresh_from_db()
        self.assertIsNotNone(customer_user.data_export_requested_at)
    
    def test_delete_user_account_success(self):
        """Test successful user account deletion."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        
        # Generate deletion code
        deletion_code = '123456'  # In real implementation, this would be sent via email
        
        # Delete account
        result = CustomerAuthService.delete_user_account(customer_user, deletion_code)
        
        self.assertTrue(result)
        
        # Verify soft delete
        customer_user.refresh_from_db()
        self.assertTrue(customer_user.is_deleted)
        self.assertIsNotNone(customer_user.deleted_at)
        
        # Verify user is deactivated
        user = User.objects.get(email=self.test_email)
        self.assertFalse(user.is_active)
    
    def test_delete_user_account_invalid_code(self):
        """Test account deletion with invalid confirmation code."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        
        # Try deletion with wrong code
        with self.assertRaises(Exception):  # Should raise ValueError
            CustomerAuthService.delete_user_account(customer_user, 'wrongcode')
    
    def test_record_consent_authenticated_user(self):
        """Test recording consent for authenticated user."""
        # Create customer
        register_result = CustomerAuthService.register_customer(
            email=self.test_email,
            password=self.test_password,
            ip_address=self.test_ip
        )
        customer_user = register_result['customer_user']
        
        # Record consent
        CustomerAuthService.record_consent(
            user_or_guest=customer_user.user,
            consent_type='MARKETING',
            consented=True,
            ip_address=self.test_ip,
            user_agent=self.test_user_agent,
            context={'source': 'registration'}
        )
        
        # Verify consent record
        consent = ConsentRecord.objects.get(
            user=customer_user,
            consent_type='MARKETING'
        )
        self.assertTrue(consent.consented)
        self.assertEqual(consent.ip_address, SecurityUtils.hash_ip_address(self.test_ip))
    
    def test_record_consent_guest_user(self):
        """Test recording consent for guest user."""
        guest_token = uuid.uuid4()
        
        # Record consent
        CustomerAuthService.record_consent(
            user_or_guest=guest_token,
            consent_type='MARKETING',
            consented=True,
            ip_address=self.test_ip,
            user_agent=self.test_user_agent
        )
        
        # Verify consent record
        consent = ConsentRecord.objects.get(
            guest_token=guest_token,
            consent_type='MARKETING'
        )
        self.assertTrue(consent.consented)
        self.assertEqual(consent.ip_address, SecurityUtils.hash_ip_address(self.test_ip))


class CustomerAuthServiceSecurityTest(TestCase):
    """Security-focused tests for CustomerAuthService."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = 'test@example.com'
        self.test_password = 'SecurePass123!'
        self.test_ip = '192.168.1.1'
    
    def test_password_validation_strong_password(self):
        """Test strong password validation."""
        strong_passwords = [
            'SecurePass123!',
            'MyP@ssw0rd',
            'Complex#Pass123',
            'Str0ng!Pass'
        ]
        
        for password in strong_passwords:
            try:
                SecurityUtils.validate_password_strength(password)
            except ValidationError:
                self.fail(f"Strong password '{password}' failed validation")
    
    def test_password_validation_weak_password(self):
        """Test weak password validation."""
        weak_passwords = [
            '123456',
            'password',
            'weak',
            'test',
            'abc123',
            'qwerty',
            'admin',
            'user'
        ]
        
        for password in weak_passwords:
            with self.assertRaises(ValidationError):
                SecurityUtils.validate_password_strength(password)
    
    def test_password_validation_length_requirements(self):
        """Test password length requirements."""
        # Too short
        with self.assertRaises(ValidationError):
            SecurityUtils.validate_password_strength('Ab1!')
        
        # Too long
        with self.assertRaises(ValidationError):
            SecurityUtils.validate_password_strength('A' * 129 + '1!')
    
    def test_password_validation_character_requirements(self):
        """Test password character requirements."""
        # Missing uppercase
        with self.assertRaises(ValidationError):
            SecurityUtils.validate_password_strength('lowercase1!')
        
        # Missing lowercase
        with self.assertRaises(ValidationError):
            SecurityUtils.validate_password_strength('UPPERCASE1!')
        
        # Missing digit
        with self.assertRaises(ValidationError):
            SecurityUtils.validate_password_strength('NoDigits!')
        
        # Missing special character
        with self.assertRaises(ValidationError):
            SecurityUtils.validate_password_strength('NoSpecialChar1')
    
    def test_ip_address_hashing(self):
        """Test IP address hashing for privacy."""
        ip = '192.168.1.1'
        hashed_ip = SecurityUtils.hash_ip_address(ip)
        
        # Hash should be consistent
        hashed_ip2 = SecurityUtils.hash_ip_address(ip)
        self.assertEqual(hashed_ip, hashed_ip2)
        
        # Hash should be different from original
        self.assertNotEqual(hashed_ip, ip)
        
        # Hash should be a valid SHA-256 hash
        self.assertEqual(len(hashed_ip), 64)  # SHA-256 hex length
        self.assertTrue(all(c in '0123456789abcdef' for c in hashed_ip))
    
    def test_email_format_validation(self):
        """Test email format validation."""
        # Valid emails
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            self.assertTrue(SecurityUtils.validate_email_format(email))
        
        # Invalid emails
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user@.com',
            'user@domain.',
            'user..name@domain.com',
            'user@domain..com'
        ]
        
        for email in invalid_emails:
            self.assertFalse(SecurityUtils.validate_email_format(email))
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = SecurityUtils.generate_secure_token()
        token2 = SecurityUtils.generate_secure_token()
        
        # Tokens should be different
        self.assertNotEqual(token1, token2)
        
        # Tokens should be URL-safe
        for token in [token1, token2]:
            self.assertTrue(all(c.isalnum() or c in '-_' for c in token))
    
    def test_data_classification(self):
        """Test data classification."""
        # Test different data types
        email_data = SecurityUtils.classify_data('email', 'test@example.com')
        self.assertEqual(email_data, 'CONFIDENTIAL')
        
        phone_data = SecurityUtils.classify_data('phone_number', '+1234567890')
        self.assertEqual(phone_data, 'CONFIDENTIAL')
        
        guest_token_data = SecurityUtils.classify_data('guest_token', str(uuid.uuid4()))
        self.assertEqual(guest_token_data, 'RESTRICTED')
        
        public_data = SecurityUtils.classify_data('display_name', 'John Doe')
        self.assertEqual(public_data, 'PUBLIC')
    
    def test_input_sanitization(self):
        """Test input sanitization."""
        # Test HTML removal
        html_input = '<script>alert("xss")</script>Hello World'
        sanitized = SecurityUtils.sanitize_input(html_input)
        self.assertEqual(sanitized, 'Hello World')
        
        # Test JavaScript removal
        js_input = 'javascript:alert("xss")'
        sanitized = SecurityUtils.sanitize_input(js_input)
        self.assertEqual(sanitized, 'alert')
        
        # Test dict sanitization
        dict_input = {
            'name': '<b>John</b>',
            'description': '<script>alert("xss")</script>Test'
        }
        sanitized = SecurityUtils.sanitize_input(dict_input)
        self.assertEqual(sanitized['name'], 'John')
        self.assertEqual(sanitized['description'], 'Test')
    
    def test_pii_masking(self):
        """Test PII masking for logging."""
        # Email masking
        masked_email = SecurityUtils.mask_pii('test@example.com', 'CONFIDENTIAL')
        self.assertEqual(masked_email, 'te***@example.com')
        
        # Phone masking
        masked_phone = SecurityUtils.mask_pii('+1234567890', 'CONFIDENTIAL')
        self.assertEqual(masked_phone, '***-7890')
        
        # General confidential data
        masked_general = SecurityUtils.mask_pii('sensitive_data', 'CONFIDENTIAL')
        self.assertEqual(masked_general, 'se***')
        
        # Public data (should not be masked)
        public_data = SecurityUtils.mask_pii('public_info', 'PUBLIC')
        self.assertEqual(public_data, 'public_info')
