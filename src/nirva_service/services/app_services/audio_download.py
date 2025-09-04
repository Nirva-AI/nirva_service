"""
Audio download endpoints for generating presigned S3 URLs.
"""

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from typing import Optional
import os

from nirva_service.models.api import AudioPresignedUrlResponse
import nirva_service.db.pgsql_audio
from .oauth_user import get_authenticated_user


audio_download_router = APIRouter()


def get_s3_client():
    """Get configured S3 client."""
    return boto3.client(
        's3',
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    )


@audio_download_router.get(
    path="/action/audio/presigned-url/v1/",
    response_model=AudioPresignedUrlResponse
)
async def get_audio_presigned_url(
    s3_key: str,
    audio_file_id: Optional[str] = None,
    current_user: str = Depends(get_authenticated_user)
) -> AudioPresignedUrlResponse:
    """
    Generate a presigned URL for downloading audio from S3.
    
    This endpoint:
    1. Verifies the user has access to the audio file
    2. Generates a presigned URL valid for 1 hour
    3. Returns the URL for client-side playback/download
    
    Args:
        s3_key: The S3 object key for the audio file
        audio_file_id: Optional database ID of the audio file for verification
        current_user: The authenticated username from JWT token
        
    Returns:
        AudioPresignedUrlResponse with presigned URL and metadata
        
    Raises:
        HTTPException: If file not found or access denied
    """
    try:
        # If audio_file_id provided, verify ownership
        if audio_file_id:
            audio_file = nirva_service.db.pgsql_audio.get_audio_file(audio_file_id)
            if not audio_file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Audio file not found"
                )
            
            # Verify the audio file belongs to the user
            if audio_file.username != current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this audio file"
                )
            
            # Use the s3_key from database if available
            s3_key = audio_file.s3_key
            bucket_name = audio_file.s3_bucket
        else:
            # Default bucket if not specified
            bucket_name = os.getenv('AWS_S3_BUCKET', 'nirvaappaudiostorage0e8a7-dev')
            
            # Basic validation - ensure the key contains the username for security
            if current_user not in s3_key:
                logger.warning(f"User {current_user} attempting to access s3_key without username: {s3_key}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this audio file"
                )
        
        # Generate presigned URL
        s3_client = get_s3_client()
        
        try:
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=3600  # 1 hour expiration
            )
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Audio file not found in storage"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
        logger.info(f"Generated presigned URL for user {current_user}, s3_key: {s3_key}")
        
        return AudioPresignedUrlResponse(
            presigned_url=presigned_url,
            expires_in_seconds=3600,
            s3_key=s3_key,
            filename=s3_key.split('/')[-1] if '/' in s3_key else s3_key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_audio_presigned_url: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )