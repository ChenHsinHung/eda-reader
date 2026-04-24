"""
Encryption module for secure credential storage
Uses Fernet symmetric encryption
"""

import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging


class CredentialManager:
    """Manages encrypted credentials storage and retrieval"""

    def __init__(self, credentials_dir):
        self.credentials_dir = credentials_dir
        self.key_file = os.path.join(credentials_dir, "key.bin")
        self.credentials_file = os.path.join(credentials_dir, "credentials.enc")
        self.logger = logging.getLogger('elearning_bot')

    def _generate_key(self):
        """Generate a new encryption key"""
        return Fernet.generate_key()

    def _load_key(self):
        """Load encryption key from file"""
        if not os.path.exists(self.key_file):
            raise FileNotFoundError("Encryption key not found. Run setup.py first.")

        with open(self.key_file, 'rb') as f:
            key = f.read()

        return key

    def _save_key(self, key):
        """Save encryption key to file"""
        os.makedirs(self.credentials_dir, exist_ok=True)

        with open(self.key_file, 'wb') as f:
            f.write(key)

        # Set restrictive permissions on Windows
        if os.name == 'nt':
            try:
                import win32api
                import win32con
                win32api.SetFileAttributes(self.key_file, win32con.FILE_ATTRIBUTE_HIDDEN)
            except ImportError:
                pass  # win32api not available, skip

    def _get_fernet(self):
        """Get Fernet cipher instance"""
        key = self._load_key()
        return Fernet(key)

    def save_credentials(self, account_id, password):
        """Encrypt and save credentials"""
        # Generate new key
        key = self._generate_key()
        self._save_key(key)

        # Encrypt credentials
        fernet = Fernet(key)
        credentials = f"{account_id}|{password}"
        encrypted = fernet.encrypt(credentials.encode())

        # Save encrypted credentials
        os.makedirs(self.credentials_dir, exist_ok=True)
        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted)

        self.logger.info("Credentials encrypted and saved successfully")

    def load_credentials(self):
        """Load and decrypt credentials"""
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError("Credentials file not found. Run setup.py first.")

        try:
            fernet = self._get_fernet()

            with open(self.credentials_file, 'rb') as f:
                encrypted = f.read()

            decrypted = fernet.decrypt(encrypted).decode()
            account_id, password = decrypted.split('|', 1)

            return account_id, password

        except InvalidToken:
            self.logger.error("Invalid encryption key or corrupted credentials file")
            raise ValueError("Failed to decrypt credentials. Key may be corrupted.")
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            raise

    def reset_credentials(self):
        """Reset/delete all credential files"""
        try:
            if os.path.exists(self.key_file):
                os.remove(self.key_file)
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
            self.logger.info("Credentials reset successfully")
        except Exception as e:
            self.logger.error(f"Failed to reset credentials: {e}")
            raise

    def credentials_exist(self):
        """Check if credentials are already set up"""
        return os.path.exists(self.key_file) and os.path.exists(self.credentials_file)


def get_credential_manager():
    """Get credential manager instance"""
    from config import CREDENTIALS_DIR
    return CredentialManager(CREDENTIALS_DIR)