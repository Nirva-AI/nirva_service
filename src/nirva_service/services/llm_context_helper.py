"""
Helper module for injecting user context into LLM prompts.
This module prepends local time information based on user's timezone.
"""
from datetime import datetime
from typing import Optional

import pytz
from loguru import logger

import nirva_service.db.redis_user_context


def inject_user_context(prompt: str, username: str) -> str:
    """
    Inject user context (local time) into the prompt.
    
    Args:
        prompt: Original prompt text
        username: User's username to fetch context
        
    Returns:
        Prompt with prepended local time context
    """
    try:
        # Get user context from Redis
        context = nirva_service.db.redis_user_context.get_user_context(username)
        
        if not context:
            logger.warning(f"No context found for user {username}, using original prompt")
            return prompt
        
        timezone_str = context.get("timezone", "UTC")
        
        # Validate timezone format
        if timezone_str in ["PDT", "PST", "EDT", "EST"]:  # Common abbreviations that should be IANA
            logger.warning(f"Invalid timezone abbreviation '{timezone_str}' for user {username}. Should be IANA format (e.g., 'America/Los_Angeles')")
        
        # Get current time in user's timezone (timezone should already be normalized)
        try:
            tz = pytz.timezone(timezone_str)
            local_time = datetime.now(tz)
            
            # Format local time context with more detailed information
            time_context = (
                f"Current local time for user: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                f"(Time zone: {timezone_str}, Hour: {local_time.hour})\n\n"
            )
            
            # Prepend context to prompt
            enhanced_prompt = time_context + prompt
            
            
            return enhanced_prompt
            
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone '{timezone_str}' for user {username}. Context: {context}")
            return prompt
            
    except Exception as e:
        logger.error(f"Error injecting context for user {username}: {e}")
        return prompt