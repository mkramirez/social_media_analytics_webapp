"""AWS Secrets Manager integration for secure credential storage."""

import json
import boto3
from typing import Dict, Optional, Any
from botocore.exceptions import ClientError
from app.config import settings


class SecretsManager:
    """AWS Secrets Manager client for managing application secrets."""

    def __init__(self):
        """Initialize AWS Secrets Manager client."""
        self.use_aws = settings.USE_AWS_SECRETS_MANAGER

        if self.use_aws:
            try:
                self.client = boto3.client(
                    'secretsmanager',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID if settings.AWS_ACCESS_KEY_ID else None,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY if settings.AWS_SECRET_ACCESS_KEY else None
                )
                print(f"✅ AWS Secrets Manager initialized (region: {settings.AWS_REGION})")
            except Exception as e:
                print(f"⚠️ AWS Secrets Manager initialization failed: {e}")
                self.use_aws = False
                self.client = None
        else:
            self.client = None
            print("ℹ️ AWS Secrets Manager disabled (using local credential encryption)")

    def create_secret(self, secret_name: str, secret_value: Dict[str, Any], description: str = "") -> bool:
        """
        Create a new secret in AWS Secrets Manager.

        Args:
            secret_name: Name of the secret
            secret_value: Secret data as dictionary
            description: Optional description

        Returns:
            True if successful, False otherwise
        """
        if not self.use_aws or not self.client:
            print("⚠️ AWS Secrets Manager not available")
            return False

        try:
            self.client.create_secret(
                Name=secret_name,
                Description=description,
                SecretString=json.dumps(secret_value)
            )
            print(f"✅ Secret created: {secret_name}")
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print(f"⚠️ Secret already exists: {secret_name}")
                # Try to update instead
                return self.update_secret(secret_name, secret_value)
            else:
                print(f"❌ Error creating secret: {e}")
                return False

        except Exception as e:
            print(f"❌ Error creating secret: {e}")
            return False

    def get_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a secret from AWS Secrets Manager.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret data as dictionary, or None if not found
        """
        if not self.use_aws or not self.client:
            return None

        try:
            response = self.client.get_secret_value(SecretId=secret_name)

            if 'SecretString' in response:
                return json.loads(response['SecretString'])
            else:
                # Binary secrets not supported in this implementation
                print(f"⚠️ Binary secret not supported: {secret_name}")
                return None

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"⚠️ Secret not found: {secret_name}")
            else:
                print(f"❌ Error retrieving secret: {e}")
            return None

        except Exception as e:
            print(f"❌ Error retrieving secret: {e}")
            return None

    def update_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> bool:
        """
        Update an existing secret in AWS Secrets Manager.

        Args:
            secret_name: Name of the secret
            secret_value: New secret data as dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.use_aws or not self.client:
            return False

        try:
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_value)
            )
            print(f"✅ Secret updated: {secret_name}")
            return True

        except ClientError as e:
            print(f"❌ Error updating secret: {e}")
            return False

        except Exception as e:
            print(f"❌ Error updating secret: {e}")
            return False

    def delete_secret(self, secret_name: str, recovery_window_days: int = 30) -> bool:
        """
        Delete a secret from AWS Secrets Manager.

        Args:
            secret_name: Name of the secret
            recovery_window_days: Number of days before permanent deletion (7-30)

        Returns:
            True if successful, False otherwise
        """
        if not self.use_aws or not self.client:
            return False

        try:
            self.client.delete_secret(
                SecretId=secret_name,
                RecoveryWindowInDays=recovery_window_days
            )
            print(f"✅ Secret scheduled for deletion: {secret_name} (recovery window: {recovery_window_days} days)")
            return True

        except ClientError as e:
            print(f"❌ Error deleting secret: {e}")
            return False

        except Exception as e:
            print(f"❌ Error deleting secret: {e}")
            return False

    def list_secrets(self, filters: Optional[Dict] = None) -> list:
        """
        List all secrets in AWS Secrets Manager.

        Args:
            filters: Optional filters for listing

        Returns:
            List of secret metadata
        """
        if not self.use_aws or not self.client:
            return []

        try:
            if filters:
                response = self.client.list_secrets(Filters=filters)
            else:
                response = self.client.list_secrets()

            return response.get('SecretList', [])

        except Exception as e:
            print(f"❌ Error listing secrets: {e}")
            return []

    def rotate_secret(self, secret_name: str, rotation_lambda_arn: str) -> bool:
        """
        Enable automatic rotation for a secret.

        Args:
            secret_name: Name of the secret
            rotation_lambda_arn: ARN of the Lambda function for rotation

        Returns:
            True if successful, False otherwise
        """
        if not self.use_aws or not self.client:
            return False

        try:
            self.client.rotate_secret(
                SecretId=secret_name,
                RotationLambdaARN=rotation_lambda_arn,
                RotationRules={
                    'AutomaticallyAfterDays': 30
                }
            )
            print(f"✅ Secret rotation enabled: {secret_name}")
            return True

        except Exception as e:
            print(f"❌ Error enabling rotation: {e}")
            return False


class ApplicationSecretsManager:
    """High-level secrets management for application credentials."""

    def __init__(self):
        """Initialize application secrets manager."""
        self.secrets_manager = SecretsManager()
        self.secret_prefix = f"{settings.ENVIRONMENT}/social-analytics"

    def _make_secret_name(self, category: str, identifier: str) -> str:
        """
        Create standardized secret name.

        Args:
            category: Category (e.g., 'database', 'api-key', 'encryption')
            identifier: Specific identifier

        Returns:
            Formatted secret name
        """
        return f"{self.secret_prefix}/{category}/{identifier}"

    def store_database_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Store database credentials in Secrets Manager.

        Args:
            credentials: Dict with host, port, username, password, database

        Returns:
            True if successful
        """
        secret_name = self._make_secret_name("database", "main")
        return self.secrets_manager.create_secret(
            secret_name,
            credentials,
            description="Main database credentials"
        )

    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """
        Retrieve database credentials from Secrets Manager.

        Returns:
            Database credentials or None
        """
        secret_name = self._make_secret_name("database", "main")
        return self.secrets_manager.get_secret(secret_name)

    def store_encryption_key(self, key: str) -> bool:
        """
        Store encryption key in Secrets Manager.

        Args:
            key: Encryption key (base64 encoded)

        Returns:
            True if successful
        """
        secret_name = self._make_secret_name("encryption", "fernet-key")
        return self.secrets_manager.create_secret(
            secret_name,
            {"key": key},
            description="Fernet encryption key for credential storage"
        )

    def get_encryption_key(self) -> Optional[str]:
        """
        Retrieve encryption key from Secrets Manager.

        Returns:
            Encryption key or None
        """
        secret_name = self._make_secret_name("encryption", "fernet-key")
        secret = self.secrets_manager.get_secret(secret_name)
        return secret.get("key") if secret else None

    def store_jwt_secret(self, secret: str) -> bool:
        """
        Store JWT secret key in Secrets Manager.

        Args:
            secret: JWT secret key

        Returns:
            True if successful
        """
        secret_name = self._make_secret_name("jwt", "secret-key")
        return self.secrets_manager.create_secret(
            secret_name,
            {"secret": secret},
            description="JWT secret key for token signing"
        )

    def get_jwt_secret(self) -> Optional[str]:
        """
        Retrieve JWT secret key from Secrets Manager.

        Returns:
            JWT secret or None
        """
        secret_name = self._make_secret_name("jwt", "secret-key")
        secret = self.secrets_manager.get_secret(secret_name)
        return secret.get("secret") if secret else None

    def store_platform_api_key(self, platform: str, credentials: Dict[str, str], user_id: str = "system") -> bool:
        """
        Store platform API credentials in Secrets Manager.

        Args:
            platform: Platform name (twitch, twitter, youtube, reddit)
            credentials: API credentials dictionary
            user_id: User identifier (for multi-user support)

        Returns:
            True if successful
        """
        secret_name = self._make_secret_name(f"platform-{platform}", user_id)
        return self.secrets_manager.create_secret(
            secret_name,
            credentials,
            description=f"{platform.title()} API credentials for user {user_id}"
        )

    def get_platform_api_key(self, platform: str, user_id: str = "system") -> Optional[Dict[str, str]]:
        """
        Retrieve platform API credentials from Secrets Manager.

        Args:
            platform: Platform name
            user_id: User identifier

        Returns:
            API credentials or None
        """
        secret_name = self._make_secret_name(f"platform-{platform}", user_id)
        return self.secrets_manager.get_secret(secret_name)


# Global instance
app_secrets_manager = ApplicationSecretsManager()
