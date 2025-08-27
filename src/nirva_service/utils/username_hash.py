"""Utility for consistent username hashing across the system."""

import hashlib


def hash_username(username: str) -> str:
    """
    Hash a username using SHA-256 for consistent identifiers.
    
    Args:
        username: The username to hash (e.g., email address)
        
    Returns:
        First 16 characters of the SHA-256 hex digest
    """
    if not username:
        return "default_user"
    
    try:
        # Create SHA-256 hash
        hash_obj = hashlib.sha256(username.encode('utf-8'))
        
        # Return first 16 characters of hex digest
        # This provides sufficient uniqueness while keeping reasonable length
        return hash_obj.hexdigest()[:16]
    except Exception:
        return "default_user"