"""
Upload authentication endpoints for generating S3 upload credentials.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from nirva_service.models.api import S3UploadTokenResponse
from nirva_service.services.storage import get_sts_service
import nirva_service.db.pgsql_user
from .oauth_user import get_authenticated_user


upload_auth_router = APIRouter()


@upload_auth_router.post(
    path="/action/auth/s3-upload-token/v1/",
    response_model=S3UploadTokenResponse
)
async def get_s3_upload_token(
    current_user: str = Depends(get_authenticated_user)
) -> S3UploadTokenResponse:
    """
    Generate temporary AWS credentials for S3 upload.
    
    This endpoint:
    1. Authenticates the user via JWT token
    2. Generates fresh 7-day temporary AWS credentials (actually 36 hours due to STS limitations)
    3. Returns credentials scoped to the user's S3 prefix
    
    The client is responsible for:
    - Caching these credentials locally
    - Implementing any refresh logic (e.g., 12-hour cooldown)
    - Using the credentials to upload directly to S3
    
    Args:
        current_user: The authenticated username from JWT token
        
    Returns:
        S3UploadTokenResponse with temporary AWS credentials
        
    Raises:
        HTTPException: If user not found or credential generation fails
    """
    try:
        # Get user details from database
        user_db = nirva_service.db.pgsql_user.get_user(current_user)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate temporary credentials
        sts_service = get_sts_service()
        credentials = sts_service.generate_upload_credentials(
            username=user_db.username,
            user_id=str(user_db.id),
            duration_seconds=604800  # Request 7 days (will be capped at 36 hours by STS)
        )
        
        logger.info(f"Generated S3 upload token for user: {current_user}")
        
        return S3UploadTokenResponse(**credentials)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating S3 upload token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload credentials: {str(e)}"
        )