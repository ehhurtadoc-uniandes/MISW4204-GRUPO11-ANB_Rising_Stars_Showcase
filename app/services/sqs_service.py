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
        self.queue_url = settings.sqs_queue_url
        self._create_client()
    
    def _create_client(self):
        """Create or recreate SQS client with current credentials"""
        # Import settings here to get the latest values (especially after reload)
        from app.core.config import settings as current_settings
        
        # Build client config - only pass credentials if they're explicitly set
        # Otherwise, let boto3 use IAM Role automatically
        client_config = {
            'region_name': current_settings.sqs_region
        }
        
        # Only add credentials if they're configured (for cases without IAM Role)
        if current_settings.aws_access_key_id and current_settings.aws_secret_access_key:
            client_config['aws_access_key_id'] = current_settings.aws_access_key_id
            client_config['aws_secret_access_key'] = current_settings.aws_secret_access_key
            # Session token is required for temporary credentials (STS)
            if current_settings.aws_session_token:
                client_config['aws_session_token'] = current_settings.aws_session_token
        
        self.sqs_client = boto3.client('sqs', **client_config)
        logger.debug("SQS client created/recreated")
    
    def _handle_credential_error(self, error: Exception) -> bool:
        """
        Handle credential-related errors by recreating the client
        
        Returns:
            True if error was handled (client recreated), False otherwise
        """
        error_code = None
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', '')
        
        # Check for credential expiration errors
        credential_errors = [
            'InvalidClientTokenId',
            'InvalidUserID.NotFound',
            'ExpiredToken',
            'TokenRefreshRequired'
        ]
        
        if error_code in credential_errors or 'token' in str(error).lower() or 'credential' in str(error).lower():
            logger.warning(f"Detected credential error ({error_code}), attempting to recreate client...")
            logger.warning("NOTE: If credentials have expired, you need to:")
            logger.warning("1. Update the .env file on the EC2 instance with new credentials")
            logger.warning("2. Restart the worker container: docker restart anb-worker-sqs")
            try:
                # Try to reload settings from .env file
                # Pydantic Settings should automatically reload if the file changed
                # But we need to force a reload by accessing the settings again
                import importlib
                from app.core import config
                importlib.reload(config)
                
                # Update queue_url in case it changed
                self.queue_url = config.settings.sqs_queue_url
                
                # Recreate client with potentially updated credentials
                self._create_client()
                logger.info("SQS client recreated successfully (credentials may still be expired - check .env file)")
                return True
            except Exception as recreate_error:
                logger.error(f"Failed to recreate SQS client: {recreate_error}")
                logger.error("Please manually update .env file and restart the container")
                return False
        
        return False
    
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
            # Try to handle credential errors by recreating client
            if self._handle_credential_error(e):
                # Retry once after recreating client
                try:
                    from datetime import datetime
                    message_body = {
                        "video_id": video_id,
                        "video_path": video_path,
                        "task_id": str(uuid.uuid4()),
                        "created_at": datetime.utcnow().isoformat()
                    }
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
                    logger.info(f"Video processing message sent to SQS after credential refresh: {message_id}")
                    return message_id
                except Exception as retry_error:
                    logger.error(f"Error sending message to SQS after credential refresh: {retry_error}")
                    return None
            else:
                logger.error(f"Error sending message to SQS: {e}")
                return None
        except Exception as e:
            # Try to handle credential errors even for non-ClientError exceptions
            if self._handle_credential_error(e):
                # Retry once after recreating client
                try:
                    from datetime import datetime
                    message_body = {
                        "video_id": video_id,
                        "video_path": video_path,
                        "task_id": str(uuid.uuid4()),
                        "created_at": datetime.utcnow().isoformat()
                    }
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
                    logger.info(f"Video processing message sent to SQS after credential refresh: {message_id}")
                    return message_id
                except Exception as retry_error:
                    logger.error(f"Error sending message to SQS after credential refresh: {retry_error}")
                    return None
            else:
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
            # Try to handle credential errors by recreating client
            if self._handle_credential_error(e):
                # Retry once after recreating client
                try:
                    response = self.sqs_client.receive_message(
                        QueueUrl=self.queue_url,
                        MaxNumberOfMessages=min(max_messages, 10),
                        WaitTimeSeconds=settings.sqs_wait_time_seconds,
                        MessageAttributeNames=['All'],
                        VisibilityTimeout=settings.sqs_visibility_timeout
                    )
                    messages = response.get('Messages', [])
                    if messages:
                        logger.info(f"Received {len(messages)} message(s) from SQS after credential refresh")
                    return messages
                except Exception as retry_error:
                    logger.error(f"Error receiving messages from SQS after credential refresh: {retry_error}")
                    return []
            else:
                logger.error(f"Error receiving messages from SQS: {e}")
                return []
        except Exception as e:
            # Try to handle credential errors even for non-ClientError exceptions
            if self._handle_credential_error(e):
                # Retry once after recreating client
                try:
                    response = self.sqs_client.receive_message(
                        QueueUrl=self.queue_url,
                        MaxNumberOfMessages=min(max_messages, 10),
                        WaitTimeSeconds=settings.sqs_wait_time_seconds,
                        MessageAttributeNames=['All'],
                        VisibilityTimeout=settings.sqs_visibility_timeout
                    )
                    messages = response.get('Messages', [])
                    if messages:
                        logger.info(f"Received {len(messages)} message(s) from SQS after credential refresh")
                    return messages
                except Exception as retry_error:
                    logger.error(f"Error receiving messages from SQS after credential refresh: {retry_error}")
                    return []
            else:
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

