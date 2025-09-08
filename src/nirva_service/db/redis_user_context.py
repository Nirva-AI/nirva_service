"""
Redis storage for user session context (timezone and locale).
Separate from chat session to keep it lightweight.
"""
import json
from datetime import datetime
from typing import Optional

from loguru import logger

import nirva_service.db.redis_client


def _user_context_key(username: str) -> str:
    """Generate user context key name"""
    assert username != "", "username cannot be an empty string."
    return f"context:{username}"


def set_user_context(username: str, timezone: str, locale: str) -> None:
    """
    Store user context in Redis with 7-day TTL.
    
    Args:
        username: User's username
        timezone: User's timezone (e.g., 'America/Los_Angeles')
        locale: User's locale (e.g., 'en-US')
    """
    assert username != "", "username cannot be an empty string."
    
    context = {
        "username": username,
        "timezone": timezone,
        "locale": locale,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    key = _user_context_key(username)
    # Store with 7-day TTL (604800 seconds)
    nirva_service.db.redis_client.redis_setex(
        key, 
        604800, 
        json.dumps(context)
    )
    
    logger.info(f"Stored context for user {username}: timezone={timezone}, locale={locale}")


def get_user_context(username: str) -> Optional[dict]:
    """
    Get user context from Redis.
    
    Args:
        username: User's username
        
    Returns:
        Dict with username, timezone, locale, updated_at or None if not found
    """
    assert username != "", "username cannot be an empty string."
    
    key = _user_context_key(username)
    data = nirva_service.db.redis_client.redis_get(key)
    
    if data:
        try:
            context = json.loads(data)
            logger.debug(f"Retrieved context for user {username}: {context}")
            return context
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode context JSON for user {username}: {e}")
            return None
    
    logger.debug(f"No context found for user {username}")
    return None


def delete_user_context(username: str) -> None:
    """
    Delete user context from Redis.
    
    Args:
        username: User's username
    """
    assert username != "", "username cannot be an empty string."
    
    key = _user_context_key(username)
    nirva_service.db.redis_client.redis_delete(key)
    logger.info(f"Deleted context for user {username}")