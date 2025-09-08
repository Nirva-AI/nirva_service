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
            logger.debug(f"No context found for user {username}, using original prompt")
            return prompt
        
        timezone_str = context.get("timezone", "UTC")
        
        # Get current time in user's timezone
        try:
            tz = pytz.timezone(timezone_str)
            local_time = datetime.now(tz)
            
            # Format local time context
            time_context = (
                f"Current local time for user: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
            )
            
            # Prepend context to prompt
            enhanced_prompt = time_context + prompt
            
            logger.debug(f"Injected time context for user {username}: {timezone_str}")
            return enhanced_prompt
            
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {timezone_str} for user {username}")
            return prompt
            
    except Exception as e:
        logger.error(f"Error injecting context for user {username}: {e}")
        return prompt