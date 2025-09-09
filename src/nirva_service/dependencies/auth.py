"""
Authentication dependencies for API endpoints.
"""
from fastapi import Depends

from ..services.app_services.oauth_user import get_authenticated_user


async def get_current_user_id(username: str = Depends(get_authenticated_user)) -> str:
    """
    Get the current authenticated user's ID (username).
    
    This is a wrapper around get_authenticated_user for consistency
    with the mental state API naming conventions.
    """
    return username