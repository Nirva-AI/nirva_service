"""
SQS Service for polling S3 event notifications.
"""

import json
import os
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SQSService:
    """Service for polling and processing SQS messages from S3 events."""
    
    def __init__(self, queue_url: Optional[str] = None):
        """
        Initialize SQS client.
        
        Args:
            queue_url: The SQS queue URL. If not provided, will use environment variable.
        """
        self.sqs_client = boto3.client(
            'sqs',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        self.queue_url = queue_url or os.getenv('SQS_QUEUE_URL', '')
        if not self.queue_url:
            logger.warning("SQS_QUEUE_URL not configured. SQS polling will not work.")
    
    def poll_messages(
        self, 
        max_messages: int = 10,
        wait_time_seconds: int = 20,
        visibility_timeout: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Poll messages from SQS queue.
        
        Args:
            max_messages: Maximum number of messages to retrieve (1-10)
            wait_time_seconds: Long polling wait time (0-20 seconds)
            visibility_timeout: Time in seconds the message is hidden from other consumers
            
        Returns:
            List of message dictionaries with parsed S3 event information
        """
        if not self.queue_url:
            logger.error("No SQS queue URL configured")
            return []
        
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout,
                MessageAttributeNames=['All'],
                AttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            parsed_messages = []
            
            for message in messages:
                try:
                    # Parse the message body (S3 event notification)
                    body = json.loads(message['Body'])
                    
                    # Handle S3 event structure
                    if 'Records' in body:
                        for record in body['Records']:
                            if record.get('eventSource') == 'aws:s3':
                                s3_info = record['s3']
                                parsed_message = {
                                    'message_id': message['MessageId'],
                                    'receipt_handle': message['ReceiptHandle'],
                                    'event_name': record['eventName'],
                                    'event_time': record['eventTime'],
                                    'bucket': s3_info['bucket']['name'],
                                    'key': s3_info['object']['key'],
                                    'size': s3_info['object'].get('size', 0),
                                    'etag': s3_info['object'].get('eTag', ''),
                                    'raw_message': message
                                }
                                parsed_messages.append(parsed_message)
                                logger.info(f"Received S3 event: {parsed_message['event_name']} for {parsed_message['key']}")
                    else:
                        # Handle non-S3 event messages (for testing)
                        parsed_message = {
                            'message_id': message['MessageId'],
                            'receipt_handle': message['ReceiptHandle'],
                            'body': body,
                            'raw_message': message
                        }
                        parsed_messages.append(parsed_message)
                        logger.info(f"Received non-S3 message: {message['MessageId']}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message body: {e}")
                except KeyError as e:
                    logger.error(f"Missing expected field in message: {e}")
            
            if parsed_messages:
                logger.info(f"Polled {len(parsed_messages)} messages from SQS")
            
            return parsed_messages
            
        except ClientError as e:
            logger.error(f"Error polling SQS messages: {e}")
            return []
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from the SQS queue after successful processing.
        
        Args:
            receipt_handle: The receipt handle of the message to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.queue_url:
            logger.error("No SQS queue URL configured")
            return False
        
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug(f"Deleted message with receipt handle: {receipt_handle[:20]}...")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting SQS message: {e}")
            return False
    
    def delete_messages_batch(self, receipt_handles: List[str]) -> Dict[str, Any]:
        """
        Delete multiple messages from the SQS queue in a batch.
        
        Args:
            receipt_handles: List of receipt handles to delete
            
        Returns:
            Dictionary with successful and failed deletions
        """
        if not self.queue_url:
            logger.error("No SQS queue URL configured")
            return {'Successful': [], 'Failed': receipt_handles}
        
        if not receipt_handles:
            return {'Successful': [], 'Failed': []}
        
        # Prepare batch delete entries
        entries = [
            {
                'Id': str(i),
                'ReceiptHandle': handle
            }
            for i, handle in enumerate(receipt_handles[:10])  # Max 10 per batch
        ]
        
        try:
            response = self.sqs_client.delete_message_batch(
                QueueUrl=self.queue_url,
                Entries=entries
            )
            
            successful = [e['Id'] for e in response.get('Successful', [])]
            failed = [e['Id'] for e in response.get('Failed', [])]
            
            logger.info(f"Batch delete: {len(successful)} successful, {len(failed)} failed")
            return response
            
        except ClientError as e:
            logger.error(f"Error in batch delete: {e}")
            return {'Successful': [], 'Failed': entries}
    
    def send_message(self, message_body: Dict[str, Any], delay_seconds: int = 0) -> Optional[str]:
        """
        Send a message to the SQS queue (useful for testing).
        
        Args:
            message_body: Dictionary to send as message body
            delay_seconds: Delay before the message becomes visible (0-900 seconds)
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.queue_url:
            logger.error("No SQS queue URL configured")
            return None
        
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                DelaySeconds=delay_seconds
            )
            
            message_id = response['MessageId']
            logger.info(f"Sent message to SQS: {message_id}")
            return message_id
            
        except ClientError as e:
            logger.error(f"Error sending message to SQS: {e}")
            return None


# Singleton instance
_sqs_service: Optional[SQSService] = None


def get_sqs_service(queue_url: Optional[str] = None) -> SQSService:
    """Get or create the singleton SQS service instance."""
    global _sqs_service
    if _sqs_service is None:
        _sqs_service = SQSService(queue_url)
    return _sqs_service