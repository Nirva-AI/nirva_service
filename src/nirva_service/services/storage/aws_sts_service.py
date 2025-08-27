"""
AWS STS Service for generating temporary credentials for S3 uploads.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class STSService:
    """Service for generating temporary AWS credentials using STS."""
    
    def __init__(self):
        """Initialize STS client."""
        self.sts_client = boto3.client(
            'sts',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.bucket_name = os.getenv('AWS_S3_BUCKET', 'nirvaappaudiostorage0e8a7-dev')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
    
    def generate_upload_credentials(
        self, 
        username: str,
        user_id: str,
        duration_seconds: int = 604800  # 7 days in seconds
    ) -> Dict[str, Any]:
        """
        Generate temporary AWS credentials for S3 upload.
        
        Args:
            username: The authenticated username
            user_id: The user's unique ID
            duration_seconds: How long the credentials should be valid (max 7 days)
            
        Returns:
            Dictionary containing temporary AWS credentials and metadata
        """
        # Create user-specific S3 prefixes
        # Allow both native-audio uploads and regular user uploads
        native_audio_prefix = f"native-audio/{username}/"
        user_prefix = f"users/{user_id}/"
        
        # Define the IAM policy for the temporary credentials
        # This policy restricts access to only the user's folders in S3
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.bucket_name}/{native_audio_prefix}*",
                        f"arn:aws:s3:::{self.bucket_name}/{user_prefix}*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Resource": f"arn:aws:s3:::{self.bucket_name}",
                    "Condition": {
                        "StringLike": {
                            "s3:prefix": [
                                f"{native_audio_prefix}*",
                                f"{user_prefix}*"
                            ]
                        }
                    }
                }
            ]
        }
        
        try:
            # Generate temporary credentials using GetSessionToken
            # Note: GetSessionToken doesn't accept inline policies, so the IAM user's
            # permissions will apply. The IAM user should have access to the entire
            # native-audio/* prefix to allow all users to upload.
            max_duration = min(duration_seconds, 129600)  # Max 36 hours for GetSessionToken
            
            response = self.sts_client.get_session_token(
                DurationSeconds=max_duration
            )
            
            credentials = response['Credentials']
            
            # Return the credentials with metadata
            return {
                "access_key_id": credentials['AccessKeyId'],
                "secret_access_key": credentials['SecretAccessKey'],
                "session_token": credentials['SessionToken'],
                "expiration": credentials['Expiration'].isoformat(),
                "bucket": self.bucket_name,
                "prefix": user_prefix,  # Keep user prefix for backward compatibility
                "native_audio_prefix": native_audio_prefix,  # Add native audio prefix
                "region": self.region,
                "duration_seconds": max_duration
            }
            
        except ClientError as e:
            logger.error(f"Error generating STS credentials: {e}")
            raise Exception(f"Failed to generate upload credentials: {str(e)}")


# Singleton instance
sts_service = STSService()


def get_sts_service() -> STSService:
    """Get the singleton STS service instance."""
    return sts_service