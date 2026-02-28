"""
Security utilities for Customer Authentication.
Implements GDPR compliance, data protection, and security best practices.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
import re

logger = logging.getLogger(__name__)


class SecurityUtils:
    """
    Security utilities for data protection and GDPR compliance.
    """
    
    # Data classification levels
    DATA_CLASSIFICATION = {
        'CONFIDENTIAL': ['email', 'phone_number', 'behavioral_data'],
        'RESTRICTED': ['guest_token', 'consent_records'],
        'INTERNAL': ['search_history', 'preferences'],
        'PUBLIC': ['display_name', 'avatar_url', 'preferences'],
    }
    
    # Password requirements
    PASSWORD_REQUIREMENTS = {
        'min_length': 8,
        'max_length': 128,
        'require_uppercase': True,
        'require_lowercase': True,
        'require_digit': True,
        'require_special': True,
        'forbidden_patterns': [
            'password', '123456', 'qwerty', 'admin', 'user',
            'airad', 'guest', 'test', 'demo'
        ]
    }
    
    @classmethod
    def hash_ip_address(cls, ip_address):
        """
        Hash IP address for privacy compliance.
        Uses SHA-256 with salt for one-way hashing.
        """
        if not ip_address:
            return None
        
        salt = getattr(settings, 'IP_HASH_SALT', 'default_ip_hash_salt')
        hash_input = f"{ip_address}:{salt}"
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    @classmethod
    def validate_password_strength(cls, password):
        """
        Validate password strength according to security requirements.
        """
        errors = []
        
        # Length requirements
        if len(password) < cls.PASSWORD_REQUIREMENTS['min_length']:
            errors.append(f"Password must be at least {cls.PASSWORD_REQUIREMENTS['min_length']} characters long")
        
        if len(password) > cls.PASSWORD_REQUIREMENTS['max_length']:
            errors.append(f"Password cannot exceed {cls.PASSWORD_REQUIREMENTS['max_length']} characters")
        
        # Character requirements
        if cls.PASSWORD_REQUIREMENTS['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if cls.PASSWORD_REQUIREMENTS['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if cls.PASSWORD_REQUIREMENTS['require_digit'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if cls.PASSWORD_REQUIREMENTS['require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Forbidden patterns
        password_lower = password.lower()
        for pattern in cls.PASSWORD_REQUIREMENTS['forbidden_patterns']:
            if pattern in password_lower:
                errors.append(f"Password cannot contain common patterns like '{pattern}'")
        
        # Sequential characters
        if cls._has_sequential_chars(password):
            errors.append("Password cannot contain sequential characters (e.g., '123', 'abc')")
        
        # Repeated characters
        if cls._has_repeated_chars(password):
            errors.append("Password cannot contain repeated characters (e.g., 'aaa', '111')")
        
        if errors:
            raise ValidationError(errors)
        
        return True
    
    @classmethod
    def _has_sequential_chars(cls, password):
        """Check for sequential characters."""
        for i in range(len(password) - 2):
            char1 = ord(password[i])
            char2 = ord(password[i + 1])
            char3 = ord(password[i + 2])
            
            # Check for ascending sequence
            if char2 == char1 + 1 and char3 == char2 + 1:
                return True
            
            # Check for descending sequence
            if char2 == char1 - 1 and char3 == char2 - 1:
                return True
        
        return False
    
    @classmethod
    def _has_repeated_chars(cls, password):
        """Check for repeated characters."""
        for i in range(len(password) - 2):
            if password[i] == password[i + 1] == password[i + 2]:
                return True
        return False
    
    @classmethod
    def generate_secure_token(cls, length=32):
        """
        Generate cryptographically secure random token.
        """
        return secrets.token_urlsafe(length)
    
    @classmethod
    def classify_data(cls, field_name, value):
        """
        Classify data according to sensitivity levels.
        """
        for classification, fields in cls.DATA_CLASSIFICATION.items():
            if field_name in fields:
                return classification
        
        # Default classification based on content
        if '@' in str(value) and '.' in str(value):
            return 'CONFIDENTIAL'  # Email
        elif re.match(r'^[\d\s\-\+\(\)]+$', str(value)):
            return 'CONFIDENTIAL'  # Phone number
        else:
            return 'INTERNAL'
    
    @classmethod
    def sanitize_input(cls, input_data):
        """
        Sanitize user input to prevent XSS and injection attacks.
        """
        if isinstance(input_data, str):
            # Remove potential XSS patterns
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', input_data, flags=re.IGNORECASE | re.DOTALL)
            sanitized = re.sub(r'<[^>]+>', '', sanitized)  # Remove all HTML tags
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
            
            return sanitized.strip()
        
        elif isinstance(input_data, dict):
            return {key: cls.sanitize_input(value) for key, value in input_data.items()}
        
        elif isinstance(input_data, list):
            return [cls.sanitize_input(item) for item in input_data]
        
        else:
            return input_data
    
    @classmethod
    def validate_email_format(cls, email):
        """
        Validate email format with strict rules.
        """
        if not email:
            return False
        
        # Basic format check
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        # Additional checks
        if email.count('@') != 1:
            return False
        
        local, domain = email.split('@')
        
        # Local part restrictions
        if len(local) < 1 or len(local) > 64:
            return False
        
        if local.startswith('.') or local.endswith('.'):
            return False
        
        if '..' in local:
            return False
        
        # Domain part restrictions
        if len(domain) < 4 or len(domain) > 253:
            return False
        
        if domain.startswith('.') or domain.endswith('.'):
            return False
        
        if '..' in domain:
            return False
        
        return True
    
    @classmethod
    def mask_pii(cls, value, classification=None):
        """
        Mask personally identifiable information for logging.
        """
        if not value:
            return '[REDACTED]'
        
        if classification is None:
            classification = cls.classify_data('value', value)
        
        if classification == 'CONFIDENTIAL':
            if '@' in str(value):  # Email
                local, domain = str(value).split('@')
                return f"{local[:2]}***@{domain}"
            elif re.match(r'^[\d\s\-\+\(\)]+', str(value)):  # Phone
                return f"***-{str(value)[-4:]}"
            else:
                return f"{str(value)[:2]}***"
        
        elif classification == 'RESTRICTED':
            return f"{str(value)[:4]}***"
        
        else:
            return value


class GDPRCompliance:
    """
    GDPR compliance utilities for data protection.
    """
    
    @classmethod
    def generate_consent_record(cls, user_or_guest, consent_type, consented, 
                                consent_version='1.0', ip_address=None, user_agent=None, context=None):
        """
        Generate GDPR-compliant consent record.
        """
        from .models import ConsentRecord
        
        consent_data = {
            'consent_type': consent_type,
            'consented': consented,
            'consent_version': consent_version,
            'ip_address': SecurityUtils.hash_ip_address(ip_address) if ip_address else None,
            'user_agent': user_agent or '',
            'context': context or {},
        }
        
        # Add user identification
        if hasattr(user_or_guest, 'customer_profile'):
            consent_data['user'] = user_or_guest.customer_profile
        else:
            consent_data['guest_token'] = user_or_guest
        
        return ConsentRecord.objects.create(**consent_data)
    
    @classmethod
    def export_user_data(cls, customer_user):
        """
        Export all user data in GDPR-compliant format.
        """
        from .services import CustomerAuthService
        from apps.user_preferences.services import (
            UserPreferenceService, SearchHistoryService, InteractionService, ReelViewService
        )
        
        export_data = {
            'export_info': {
                'user_id': str(customer_user.id),
                'email': customer_user.user.email,
                'export_date': timezone.now().isoformat(),
                'format_version': '1.0',
            },
            'account_data': {
                'email': customer_user.user.email,
                'display_name': customer_user.display_name,
                'avatar_url': customer_user.avatar_url,
                'created_at': customer_user.created_at.isoformat(),
                'last_login': customer_user.user.last_login.isoformat() if customer_user.user.last_login else None,
                'is_deleted': customer_user.is_deleted,
                'deleted_at': customer_user.deleted_at.isoformat() if customer_user.deleted_at else None,
            },
            'preferences': UserPreferenceService.get_preferences(customer_user) or {},
            'consent_records': [
                {
                    'consent_type': record.consent_type,
                    'consented': record.consented,
                    'consent_version': record.consent_version,
                    'consented_at': record.consented_at.isoformat(),
                    'ip_address_hash': record.ip_address,
                    'user_agent': record.user_agent,
                    'context': record.context,
                }
                for record in customer_user.consentrecord_set.all().order_by('-consented_at')
            ],
            'search_history': SearchHistoryService.get_search_history(customer_user, limit=1000),
            'interactions': InteractionService.get_recent_interactions(customer_user, limit=1000),
            'reel_views': ReelViewService.get_view_stats(customer_user, days=365),
        }
        
        return export_data
    
    @classmethod
    def anonymize_user_data(cls, customer_user):
        """
        Anonymize user data while preserving analytics structure.
        """
        # Clear PII but keep structure for analytics
        customer_user.display_name = None
        customer_user.phone_number = None
        customer_user.behavioral_data = {}
        # Anonymize email (keep domain for analytics)
        email_parts = customer_user.user.email.split('@')
        anonymized_email = f"user_{customer_user.id}@{email_parts[1]}"
        customer_user.user.email = anonymized_email
        
        customer_user.save()
        customer_user.user.save()
        
        return True
    
    @classmethod
    def check_data_retention_compliance(cls):
        """
        Check data retention compliance with GDPR requirements.
        """
        from datetime import timedelta
        from .models import CustomerUser, ConsentRecord
        from apps.user_preferences.models import UserSearchHistory, UserVendorInteraction
        
        compliance_report = {
            'check_date': timezone.now().isoformat(),
            'issues': [],
            'recommendations': [],
        }
        
        # Check for deleted users past retention period
        retention_days = getattr(settings, 'GDPR_DATA_RETENTION_DAYS', 365)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # Check soft-deleted users past retention period
        deleted_users = CustomerUser.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        ).count()
        
        if deleted_users > 0:
            compliance_report['issues'].append({
                'type': 'data_retention',
                'message': f'{deleted_users} deleted users past {retention_days}-day retention period',
                'severity': 'high'
            })
            compliance_report['recommendations'].append(
                'Schedule immediate data purge for deleted users past retention period'
            )
        
        # Check consent records for inactive users
        inactive_cutoff = timezone.now() - timedelta(days=730)  # 2 years
        old_consents = ConsentRecord.objects.filter(
            consented_at__lt=inactive_cutoff
        ).count()
        
        if old_consents > 0:
            compliance_report['issues'].append({
                'type': 'consent_retention',
                'message': f'{old_consents} consent records older than 2 years',
                'severity': 'medium'
            })
            compliance_report['recommendations'].append(
                'Archive or delete old consent records according to retention policy'
            )
        
        return compliance_report


class TokenSecurity:
    """
    JWT token security utilities.
    """
    
    JWT_AUDIENCE = "user-portal"
    TOKEN_BLACKLIST_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def validate_token_audience(cls, token):
        """
        Validate JWT token audience claim.
        """
        try:
            payload = token.payload
            audience = payload.get('aud')
            
            if audience != cls.JWT_AUDIENCE:
                return False, f"Invalid token audience: {audience}"
            
            return True, "Valid audience"
            
        except Exception as e:
            return False, f"Token validation error: {e}"
    
    @classmethod
    def blacklist_token(cls, refresh_token):
        """
        Add refresh token to blacklist.
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Add to our own blacklist cache for additional security
            token_jti = token.get('jti')
            if token_jti:
                cache_key = f"blacklisted_token:{token_jti}"
                cache.set(cache_key, True, timeout=cls.TOKEN_BLACKLIST_TIMEOUT)
            
            return True
            
        except Exception as e:
            logger.error(f"Token blacklisting failed: {e}")
            return False
    
    @classmethod
    def is_token_blacklisted(cls, token_jti):
        """
        Check if token is blacklisted.
        """
        cache_key = f"blacklisted_token:{token_jti}"
        return cache.get(cache_key, False)
    
    @classmethod
    def generate_secure_headers(cls):
        """
        Generate security headers for API responses.
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        }


class AuditLogger:
    """
    Security audit logging for compliance and monitoring.
    """
    
    @classmethod
    def log_security_event(cls, event_type, user_or_guest, details=None, 
                          ip_address=None, user_agent=None):
        """
        Log security event for audit trail.
        """
        from apps.audit.models import AuditLog
        
        # Determine user identification
        user_id = None
        if hasattr(user_or_guest, 'customer_profile'):
            user_id = user_or_guest.customer_profile.id
        elif hasattr(user_or_guest, 'id'):
            user_id = user_or_guest.id
        
        # Log the security event
        AuditLog.log_action(
            user_id=user_id,
            action=f"SECURITY_{event_type}",
            entity_type="SECURITY_EVENT",
            metadata={
                'event_type': event_type,
                'details': details or {},
                'ip_address': SecurityUtils.hash_ip_address(ip_address) if ip_address else None,
                'user_agent': user_agent or '',
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    @classmethod
    def log_authentication_event(cls, event_type, user_or_guest, success=True, 
                               details=None, ip_address=None, user_agent=None):
        """
        Log authentication event.
        """
        event_details = {
            'success': success,
            'details': details or {},
        }
        
        cls.log_security_event(
            f"AUTH_{event_type}_{'SUCCESS' if success else 'FAILURE'}",
            user_or_guest,
            event_details,
            ip_address,
            user_agent
        )
    
    @classmethod
    def log_data_access_event(cls, data_type, user_or_guest, record_id=None, 
                              action='READ', ip_address=None, user_agent=None):
        """
        Log data access event for GDPR compliance.
        """
        event_details = {
            'data_type': data_type,
            'record_id': str(record_id) if record_id else None,
            'action': action,
        }
        
        cls.log_security_event(
            f"DATA_ACCESS_{action}",
            user_or_guest,
            event_details,
            ip_address,
            user_agent
        )
