"""
SQS Service for sending and receiving video processing messages
"""
import json
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class SQSService:
    """Service for interacting with Amazon SQS"""
    
    def __init__(self):
        """Initialize SQS client"""
<<<<<<< HEAD
        # Build client config - only pass credentials if they're explicitly set
        # Otherwise, let boto3 use IAM Role automatically
        client_config = {
            'region_name': settings.sqs_region
        }
        
        # Only add credentials if they're configured (for cases without IAM Role)
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_config['aws_access_key_id'] = settings.aws_access_key_id
            client_config['aws_secret_access_key'] = settings.aws_secret_access_key
            # Session token is required for temporary credentials (STS)
            if settings.aws_session_token:
                client_config['aws_session_token'] = settings.aws_session_token
        
        self.sqs_client = boto3.client('sqs', **client_config)
=======
        self.sqs_client = boto3.client(
            'sqs',
            region_name=settings.sqs_region,
            aws_access_key_id=settings.aws_access_key_id if settings.aws_access_key_id else None,
            aws_secret_access_key=settings.aws_secret_access_key if settings.aws_secret_access_key else None
        )
>>>>>>> dbebf9ab28b1bd24d092a30f7e9026d3d626b0fc
        self.queue_url = settings.sqs_queue_url
    
    def send_video_processing_message(
        self, 
        video_id: str, 
        video_path: str
    ) -> Optional[str]:
        """
        Send a video processing message to SQS queue
        
        Args:
            video_id: UUID of the video to process
            video_path: Path to the video file (S3 or local)
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.queue_url:
            logger.error("SQS queue URL not configured")
            return None
        
        try:
            # Create message body
            from datetime import datetime
            message_body = {
                "video_id": video_id,
                "video_path": video_path,
                "task_id": str(uuid.uuid4()),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    'video_id': {
                        'StringValue': video_id,
                        'DataType': 'String'
                    },
                    'video_path': {
                        'StringValue': video_path,
                        'DataType': 'String'
                    }
                }
            )
            
            message_id = response.get('MessageId')
            logger.info(f"Video processing message sent to SQS: {message_id} for video {video_id}")
            return message_id
            
        except ClientError as e:
            logger.error(f"Error sending message to SQS: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending message to SQS: {e}")
            return None
    
    def receive_messages(self, max_messages: int = 1) -> list:
        """
        Receive messages from SQS queue
        
        Args:
            max_messages: Maximum number of messages to receive (1-10)
            
        Returns:
            List of messages (each message is a dict with 'Body', 'ReceiptHandle', etc.)
        """
        if not self.queue_url:
            logger.error("SQS queue URL not configured")
            return []
        
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=min(max_messages, 10),  # SQS limit is 10
                WaitTimeSeconds=settings.sqs_wait_time_seconds,  # Long polling
                MessageAttributeNames=['All'],
                VisibilityTimeout=settings.sqs_visibility_timeout
            )
            
            messages = response.get('Messages', [])
            if messages:
                logger.info(f"Received {len(messages)} message(s) from SQS")
            return messages
            
        except ClientError as e:
            logger.error(f"Error receiving messages from SQS: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error receiving messages from SQS: {e}")
            return []
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a message from SQS queue after successful processing
        
        Args:
            receipt_handle: Receipt handle of the message to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.queue_url:
            logger.error("SQS queue URL not configured")
            return False
        
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug(f"Message deleted from SQS: {receipt_handle[:20]}...")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting message from SQS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting message from SQS: {e}")
            return False
    
    def get_queue_attributes(self) -> Optional[Dict[str, Any]]:
        """
        Get queue attributes (useful for monitoring)
        
        Returns:
            Dictionary with queue attributes or None if error
        """
        if not self.queue_url:
            logger.error("SQS queue URL not configured")
            return None
        
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['All']
            )
            return response.get('Attributes', {})
            
        except ClientError as e:
            logger.error(f"Error getting queue attributes: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting queue attributes: {e}")
            return None


# Singleton instance
_sqs_service: Optional[SQSService] = None


def get_sqs_service() -> SQSService:
    """Get or create SQS service singleton"""
    global _sqs_service
    if _sqs_service is None:
        _sqs_service = SQSService()
    return _sqs_service

