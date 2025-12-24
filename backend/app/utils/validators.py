"""Input validation utilities."""

import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or len(email) > 255:
        return False, "Email address is required and must be less than 255 characters"

    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False, "Invalid email address format"

    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format.

    Requirements:
    - 3-50 characters
    - Alphanumeric and underscores only
    - Must start with a letter

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 50:
        return False, "Username must be less than 50 characters"

    if not username[0].isalpha():
        return False, "Username must start with a letter"

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"

    return True, ""


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing potentially dangerous characters.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace('\x00', '')

    # Trim to max length
    if len(text) > max_length:
        text = text[:max_length]

    # Strip leading/trailing whitespace
    text = text.strip()

    return text
