import hashlib
import hmac
from typing import Optional
from django.conf import settings


def hash_ip_address(ip_address: str, salt: Optional[str] = None) -> str:
    """
    Hash IP address for privacy compliance.
    Uses HMAC-SHA256 with configurable salt.
    
    Args:
        ip_address: IP address to hash
        salt: Optional salt for additional security
        
    Returns:
        Hashed IP address (hex string)
    """
    if not ip_address:
        return ''
    
    # Use configured salt or default
    salt = salt or getattr(settings, 'IP_HASH_SALT', 'default-ip-salt')
    
    # Create HMAC-SHA256 hash
    hash_obj = hmac.new(
        salt.encode(),
        ip_address.encode(),
        hashlib.sha256
    )
    
    return hash_obj.hexdigest()


def anonymize_ip_address(ip_address: str) -> str:
    """
    Anonymize IP address by zeroing out the last octet/segment.
    Complies with GDPR and other privacy regulations.
    
    Args:
        ip_address: IP address to anonymize
        
    Returns:
        Anonymized IP address
    """
    if not ip_address:
        return ''
    
    try:
        if '.' in ip_address:
            # IPv4: zero out last octet
            parts = ip_address.split('.')
            if len(parts) == 4:
                parts[-1] = '0'
                return '.'.join(parts)
        elif ':' in ip_address:
            # IPv6: zero out last segment
            parts = ip_address.split(':')
            if len(parts) >= 2:
                parts[-1] = '0'
                return ':'.join(parts)
    except Exception:
        pass
    
    return ip_address


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email address
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    # Mask local part - keep first 2 characters and last character
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[:2] + '*' * (len(local) - 3) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_phone_number(phone: str) -> str:
    """
    Mask phone number for privacy.
    
    Args:
        phone: Phone number to mask
        
    Returns:
        Masked phone number
    """
    if not phone:
        return phone
    
    # Remove non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) <= 4:
        return '*' * len(phone)
    
    # Keep last 4 digits, mask the rest
    masked_digits = '*' * (len(digits) - 4) + digits[-4:]
    
    # Reformat with original non-digit characters
    result = ''
    digit_index = 0
    
    for char in phone:
        if char.isdigit():
            if digit_index < len(masked_digits):
                result += masked_digits[digit_index]
                digit_index += 1
            else:
                result += char
        else:
            result += char
    
    return result


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        Hex-encoded secure token
    """
    import secrets
    return secrets.token_hex(length)


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify HMAC signature of payload.
    
    Args:
        payload: Original payload
        signature: HMAC signature to verify
        secret: Secret key used for signing
        
    Returns:
        True if signature is valid
    """
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


def create_signature(payload: str, secret: str) -> str:
    """
    Create HMAC signature for payload.
    
    Args:
        payload: Payload to sign
        secret: Secret key for signing
        
    Returns:
        HMAC signature (hex string)
    """
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
