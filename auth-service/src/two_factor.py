"""
TOTP-based Two-Factor Authentication Service

Provides complete 2FA functionality using Time-based One-Time Passwords (TOTP)
compatible with Google Authenticator and Microsoft Authenticator.
"""

import secrets
import string
import json
from io import BytesIO
from typing import Tuple, List, Optional

import pyotp
import qrcode

import json
import secrets
from io import BytesIO
from typing import List, Optional, Tuple
from urllib.parse import quote

import pyotp
import qrcode


class TwoFactorAuthService:
    """Service for managing Two-Factor Authentication using TOTP."""
    
    def __init__(self, app_name: str = "Eunice Research Platform"):
        self.app_name = app_name
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret key."""
        return pyotp.random_base32()
    
    def generate_backup_codes(self, count: int = 8) -> List[str]:
        """Generate backup codes for 2FA recovery."""
        backup_codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            backup_codes.append(code)
        return backup_codes
    
    def get_provisioning_uri(self, secret: str, user_email: str) -> str:
        """Generate TOTP provisioning URI for QR code."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=self.app_name
        )
    
    def generate_qr_code(self, provisioning_uri: str) -> BytesIO:
        """Generate QR code for TOTP setup."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, 'PNG')
        img_buffer.seek(0)
        return img_buffer
    
    def verify_totp_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verify TOTP code.
        
        Args:
            secret: The TOTP secret key
            code: The 6-digit TOTP code
            window: Time window for verification (default 1 = ±30 seconds)
        """
        if not code or len(code) != 6 or not code.isdigit():
            return False
        
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    
    def verify_backup_code(self, stored_backup_codes: str, provided_code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify backup code and remove it from the list.
        
        Returns:
            Tuple of (is_valid, updated_backup_codes_json)
        """
        if not stored_backup_codes or not provided_code:
            return False, stored_backup_codes
        
        try:
            backup_codes = json.loads(stored_backup_codes)
        except json.JSONDecodeError:
            return False, stored_backup_codes
        
        provided_code = provided_code.upper().strip()
        
        if provided_code in backup_codes:
            # Remove used backup code
            backup_codes.remove(provided_code)
            updated_codes = json.dumps(backup_codes)
            return True, updated_codes
        
        return False, stored_backup_codes
    
    def has_remaining_backup_codes(self, stored_backup_codes: Optional[str]) -> bool:
        """Check if user has remaining backup codes."""
        if not stored_backup_codes:
            return False
        
        try:
            backup_codes = json.loads(stored_backup_codes)
            return len(backup_codes) > 0
        except json.JSONDecodeError:
            return False
    
    def count_remaining_backup_codes(self, stored_backup_codes: Optional[str]) -> int:
        """Count remaining backup codes."""
        if not stored_backup_codes:
            return 0
        
        try:
            backup_codes = json.loads(stored_backup_codes)
            return len(backup_codes)
        except json.JSONDecodeError:
            return 0
    
    def regenerate_backup_codes(self, count: int = 8) -> str:
        """Generate new backup codes and return as JSON string."""
        new_codes = self.generate_backup_codes(count)
        return json.dumps(new_codes)
    
    def get_current_totp_code(self, secret: str) -> str:
        """Get current TOTP code (for testing purposes)."""
        totp = pyotp.TOTP(secret)
        return totp.now()
