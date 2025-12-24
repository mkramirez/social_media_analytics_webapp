"""Service for encrypting and decrypting API credentials."""

import json
from cryptography.fernet import Fernet
from typing import Dict, Any
from app.config import settings


class CredentialService:
    """Service for secure credential management."""

    def __init__(self):
        """Initialize credential service with encryption key."""
        # In production, this key should be stored in AWS Secrets Manager
        # For now, derive it from the SECRET_KEY
        self.cipher = self._get_cipher()

    def _get_cipher(self) -> Fernet:
        """
        Get Fernet cipher for encryption/decryption.

        Returns:
            Fernet cipher instance
        """
        # Derive a key from the SECRET_KEY
        # In production, use a dedicated encryption key from AWS Secrets Manager
        import base64
        import hashlib

        # Create a 32-byte key from SECRET_KEY
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key_b64 = base64.urlsafe_b64encode(key)

        return Fernet(key_b64)

    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        Encrypt credentials dictionary.

        Args:
            credentials: Dictionary of credentials to encrypt

        Returns:
            Encrypted credentials as string
        """
        # Convert to JSON
        json_data = json.dumps(credentials)

        # Encrypt
        encrypted = self.cipher.encrypt(json_data.encode())

        # Return as string
        return encrypted.decode()

    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """
        Decrypt credentials string.

        Args:
            encrypted_credentials: Encrypted credentials string

        Returns:
            Decrypted credentials dictionary

        Raises:
            ValueError: If decryption fails
        """
        try:
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted_credentials.encode())

            # Parse JSON
            credentials = json.loads(decrypted.decode())

            return credentials
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")

    def validate_twitch_credentials(self, credentials: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate Twitch API credentials.

        Args:
            credentials: Credentials dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["client_id", "client_secret"]

        for field in required_fields:
            if field not in credentials:
                return False, f"Missing required field: {field}"

            if not credentials[field] or not isinstance(credentials[field], str):
                return False, f"Invalid {field}"

        return True, ""

    def validate_twitter_credentials(self, credentials: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate Twitter API credentials.

        Args:
            credentials: Credentials dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["bearer_token"]

        for field in required_fields:
            if field not in credentials:
                return False, f"Missing required field: {field}"

            if not credentials[field] or not isinstance(credentials[field], str):
                return False, f"Invalid {field}"

        return True, ""

    def validate_youtube_credentials(self, credentials: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate YouTube API credentials.

        Args:
            credentials: Credentials dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["api_key"]

        for field in required_fields:
            if field not in credentials:
                return False, f"Missing required field: {field}"

            if not credentials[field] or not isinstance(credentials[field], str):
                return False, f"Invalid {field}"

        return True, ""

    def validate_reddit_credentials(self, credentials: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate Reddit API credentials.

        Args:
            credentials: Credentials dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["client_id", "client_secret", "user_agent"]

        for field in required_fields:
            if field not in credentials:
                return False, f"Missing required field: {field}"

            if not credentials[field] or not isinstance(credentials[field], str):
                return False, f"Invalid {field}"

        return True, ""

    def validate_credentials(self, platform: str, credentials: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate credentials for a specific platform.

        Args:
            platform: Platform name ('twitch', 'twitter', 'youtube', 'reddit')
            credentials: Credentials dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        validators = {
            "twitch": self.validate_twitch_credentials,
            "twitter": self.validate_twitter_credentials,
            "youtube": self.validate_youtube_credentials,
            "reddit": self.validate_reddit_credentials
        }

        validator = validators.get(platform.lower())
        if not validator:
            return False, f"Unknown platform: {platform}"

        return validator(credentials)
