"""
S3 Pre-signed URL generation for background uploads.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from .oauth_user import get_authenticated_user
from ...utils.username_hash import hash_username


# Router
s3_presigned_router = APIRouter(
    prefix="/api/v1/s3",
    tags=["s3"]
)


class PreSignedUrlRequest(BaseModel):
    """Request for pre-signed URL generation."""
    file_name: str
    file_size: int
    content_type: str = "audio/wav"
    metadata: Dict[str, str] = {}


class PreSignedUrlResponse(BaseModel):
    """Response with pre-signed URL and metadata."""
    upload_url: str
    s3_key: str
    expires_in: int
    method: str = "PUT"


@s3_presigned_router.post("/presigned-url", response_model=PreSignedUrlResponse)
async def get_presigned_upload_url(
    request: PreSignedUrlRequest,
    current_user: str = Depends(get_authenticated_user)
) -> PreSignedUrlResponse:
    """
    Generate a pre-signed URL for S3 upload.
    
    This URL can be used directly for uploading without additional signing.
    The URL is valid for 12 hours to handle background uploads.
    """
    try:
        # Get user hash for S3 path
        user_hash = hash_username(current_user)
        
        # Build S3 key
        s3_key = f"native-audio/{user_hash}/{request.file_name}"
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name='us-east-1'
        )
        
        # Prepare metadata
        metadata = {
            'user': current_user,
            'upload-time': datetime.utcnow().isoformat(),
            **request.metadata
        }
        
        # Generate pre-signed URL valid for 12 hours
        # This gives plenty of time for background uploads to complete
        expires_in = 12 * 3600  # 12 hours
        
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': 'nirva-app-audio',
                'Key': s3_key,
                'ContentType': request.content_type,
                'ContentLength': request.file_size,
                'Metadata': metadata
            },
            ExpiresIn=expires_in
        )
        
        logger.info(f"Generated pre-signed URL for {current_user}: {s3_key}")
        
        return PreSignedUrlResponse(
            upload_url=presigned_url,
            s3_key=s3_key,
            expires_in=expires_in,
            method="PUT"
        )
        
    except ClientError as e:
        logger.error(f"AWS error generating pre-signed URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
    except Exception as e:
        logger.error(f"Error generating pre-signed URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@s3_presigned_router.post("/batch-presigned-urls")
async def get_batch_presigned_urls(
    requests: list[PreSignedUrlRequest],
    current_user: str = Depends(get_authenticated_user)
) -> list[PreSignedUrlResponse]:
    """
    Generate multiple pre-signed URLs in a single request.
    Useful for queuing multiple background uploads at once.
    """
    try:
        urls = []
        for request in requests[:10]:  # Limit to 10 URLs per batch
            url_response = await get_presigned_upload_url(request, current_user)
            urls.append(url_response)
        
        logger.info(f"Generated {len(urls)} pre-signed URLs for {current_user}")
        return urls
        
    except Exception as e:
        logger.error(f"Error generating batch pre-signed URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))