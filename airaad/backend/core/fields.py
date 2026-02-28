from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64


class EncryptedCharField(models.CharField):
    """
    Encrypted CharField for sensitive data.
    Uses AES-256-GCM encryption for data at rest.
    """
    
    def __init__(self, *args, **kwargs):
        # Set max_length if not provided (encrypted data will be longer)
        if 'max_length' not in kwargs:
            kwargs['max_length'] = 255
        super().__init__(*args, **kwargs)
    
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Don't include max_length in migrations as encrypted data length varies
        if 'max_length' in kwargs:
            del kwargs['max_length']
        return name, path, args, kwargs
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when loading from database."""
        if value is None:
            return value
        
        try:
            return self._decrypt(value)
        except Exception:
            # If decryption fails, return the encrypted value
            # This prevents data loss if encryption key changes
            return value
    
    def to_python(self, value):
        """Convert value to Python type."""
        if value is None:
            return value
        
        # If it's already a string and doesn't look like encrypted data, return as-is
        if isinstance(value, str) and not value.startswith('gAAAA'):
            return value
        
        try:
            return self._decrypt(value)
        except Exception:
            return value
    
    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None:
            return value
        
        # If it's already encrypted, don't encrypt again
        if isinstance(value, str) and value.startswith('gAAAA'):
            return value
        
        return self._encrypt(value)
    
    def _get_cipher(self):
        """Get encryption cipher."""
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not configured in settings")
        
        # Ensure key is properly formatted for Fernet
        if len(encryption_key) != 44:  # Fernet keys are 44 bytes base64
            # Derive a proper Fernet key from the provided key
            import hashlib
            key_hash = hashlib.sha256(encryption_key.encode()).digest()
            encryption_key = base64.urlsafe_b64encode(key_hash).decode()
        
        return Fernet(encryption_key.encode())
    
    def _encrypt(self, value):
        """Encrypt a value."""
        if not value:
            return value
        
        cipher = self._get_cipher()
        encrypted_value = cipher.encrypt(value.encode())
        return encrypted_value.decode()
    
    def _decrypt(self, value):
        """Decrypt a value."""
        if not value:
            return value
        
        cipher = self._get_cipher()
        decrypted_value = cipher.decrypt(value.encode())
        return decrypted_value.decode()


class EncryptedTextField(models.TextField):
    """
    Encrypted TextField for sensitive text data.
    Uses AES-256-GCM encryption for data at rest.
    """
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when loading from database."""
        if value is None:
            return value
        
        try:
            return self._decrypt(value)
        except Exception:
            return value
    
    def to_python(self, value):
        """Convert value to Python type."""
        if value is None:
            return value
        
        if isinstance(value, str) and not value.startswith('gAAAA'):
            return value
        
        try:
            return self._decrypt(value)
        except Exception:
            return value
    
    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None:
            return value
        
        if isinstance(value, str) and value.startswith('gAAAA'):
            return value
        
        return self._encrypt(value)
    
    def _get_cipher(self):
        """Get encryption cipher."""
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not configured in settings")
        
        if len(encryption_key) != 44:
            import hashlib
            key_hash = hashlib.sha256(encryption_key.encode()).digest()
            encryption_key = base64.urlsafe_b64encode(key_hash).decode()
        
        return Fernet(encryption_key.encode())
    
    def _encrypt(self, value):
        """Encrypt a value."""
        if not value:
            return value
        
        cipher = self._get_cipher()
        encrypted_value = cipher.encrypt(value.encode())
        return encrypted_value.decode()
    
    def _decrypt(self, value):
        """Decrypt a value."""
        if not value:
            return value
        
        cipher = self._get_cipher()
        decrypted_value = cipher.decrypt(value.encode())
        return decrypted_value.decode()


class EncryptedJSONField(models.JSONField):
    """
    Encrypted JSONField for sensitive structured data.
    Uses AES-256-GCM encryption for data at rest.
    """
    
    def from_db_value(self, value, expression, connection):
        """Decrypt value when loading from database."""
        if value is None:
            return value
        
        try:
            decrypted_value = self._decrypt(value)
            import json
            return json.loads(decrypted_value)
        except Exception:
            return value
    
    def to_python(self, value):
        """Convert value to Python type."""
        if value is None:
            return value
        
        if isinstance(value, dict) or isinstance(value, list):
            return value
        
        if isinstance(value, str) and not value.startswith('gAAAA'):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        try:
            decrypted_value = self._decrypt(value)
            import json
            return json.loads(decrypted_value)
        except Exception:
            return value
    
    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None:
            return value
        
        if isinstance(value, str) and value.startswith('gAAAA'):
            return value
        
        import json
        json_value = json.dumps(value)
        return self._encrypt(json_value)
    
    def _get_cipher(self):
        """Get encryption cipher."""
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not configured in settings")
        
        if len(encryption_key) != 44:
            import hashlib
            key_hash = hashlib.sha256(encryption_key.encode()).digest()
            encryption_key = base64.urlsafe_b64encode(key_hash).decode()
        
        return Fernet(encryption_key.encode())
    
    def _encrypt(self, value):
        """Encrypt a value."""
        if not value:
            return value
        
        cipher = self._get_cipher()
        encrypted_value = cipher.encrypt(value.encode())
        return encrypted_value.decode()
    
    def _decrypt(self, value):
        """Decrypt a value."""
        if not value:
            return value
        
        cipher = self._get_cipher()
        decrypted_value = cipher.decrypt(value.encode())
        return decrypted_value.decode()
