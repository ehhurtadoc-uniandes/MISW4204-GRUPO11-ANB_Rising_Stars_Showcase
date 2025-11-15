"""
SQS Worker for processing video tasks from Amazon SQS
Replaces Celery worker for Entrega 4
"""
import json
import os
import uuid
import time
import signal
import sys
from typing import Optional, Dict, Any
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.video_service import VideoService
from app.services.file_storage import get_file_storage
from app.services.sqs_service import get_sqs_service
from app.models.video import VideoStatus
from app.core.config import settings
import logging

# Fix for PIL.Image.ANTIALIAS compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_flag
    logger.info("Received shutdown signal, finishing current tasks...")
    shutdown_flag = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def create_anb_logo():
    """Create a simple ANB logo as placeholder"""
    # Create a simple logo since we don't have the actual ANB logo
    img = Image.new('RGBA', (200, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw ANB text
    try:
        # Try to use a default font, fallback to default if not available
        font = ImageFont.load_default()
    except:
        font = None
    
    # Draw background rectangle
    draw.rectangle([10, 10, 190, 90], fill=(255, 0, 0, 200))  # Red background
    draw.text((60, 40), "ANB", fill=(255, 255, 255, 255), font=font)
    
    return img


def process_video(video_id: str, video_path: str) -> bool:
    """
    Process video: trim, resize, add watermark
    
    Args:
        video_id: UUID of the video to process
        video_path: Path to the video file (S3 or local)
        
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    file_storage = get_file_storage()
    local_video_path = None
    
    try:
        # Update status to processing
        VideoService.update_video_status(db, video_id, VideoStatus.processing)
        db.commit()
        
        # Handle S3 paths: download to local temp file if needed
        if video_path.startswith('s3://'):
            logger.info(f"Downloading video from S3: {video_path}")
            local_video_path = f"/tmp/{uuid.uuid4()}.mp4"
            if not file_storage.download_file(video_path, local_video_path):
                raise Exception(f"Failed to download video from S3: {video_path}")
            video_path_to_use = local_video_path
        else:
            video_path_to_use = video_path
        
        # Load video
        video_clip = VideoFileClip(video_path_to_use)
        
        # Get video duration and trim to max 30 seconds
        duration = min(video_clip.duration, settings.video_max_duration)
        video_clip = video_clip.subclip(0, duration)
        
        # Resize to 720p with 16:9 aspect ratio
        target_width = 1280
        target_height = 720
        
        # Resize maintaining aspect ratio
        video_clip = video_clip.resize(height=target_height)
        
        # If width is different from target, crop or pad
        if video_clip.w != target_width:
            if video_clip.w > target_width:
                # Crop from center
                x_center = video_clip.w / 2
                x_start = x_center - target_width / 2
                video_clip = video_clip.crop(x1=x_start, x2=x_start + target_width)
            else:
                # Add padding (black bars)
                video_clip = video_clip.margin(
                    left=(target_width - video_clip.w) // 2,
                    right=(target_width - video_clip.w) // 2,
                    color=(0, 0, 0)
                )
        
        # Remove audio
        video_clip = video_clip.without_audio()
        
        # Create ANB logo watermark
        logo_image = create_anb_logo()
        logo_path = f"/tmp/anb_logo_{uuid.uuid4()}.png"
        logo_image.save(logo_path)
        
        # Create intro clip (2.5 seconds)
        intro_clip = ImageClip(logo_path, duration=2.5).resize(
            width=target_width, height=target_height
        )
        
        # Create outro clip (2.5 seconds)  
        outro_clip = ImageClip(logo_path, duration=2.5).resize(
            width=target_width, height=target_height
        )
        
        # Create watermark (small logo in corner)
        watermark = ImageClip(logo_path).set_duration(video_clip.duration).resize(
            width=100
        ).set_position(('right', 'bottom')).set_opacity(0.7)
        
        # Composite video with watermark
        video_with_watermark = CompositeVideoClip([video_clip, watermark])
        
        # Concatenate intro + video + outro
        final_video = CompositeVideoClip([
            intro_clip,
            video_with_watermark.set_start(2.5),
            outro_clip.set_start(2.5 + video_clip.duration)
        ])
        
        # Generate output filename
        output_filename = f"processed_{uuid.uuid4()}.mp4"
        local_output_path = os.path.join("/tmp", output_filename)
        
        # Export processed video to local temp file
        final_video.write_videofile(
            local_output_path,
            codec='libx264',
            audio_codec='aac' if final_video.audio else None,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=24
        )
        
        # Upload processed video to S3 if using cloud storage
        if settings.storage_type == 'cloud':
            logger.info(f"Uploading processed video to S3")
            with open(local_output_path, 'rb') as f:
                processed_file_data = f.read()
            
            # Save to S3 and get the S3 path
            s3_path = file_storage.save_file(
                processed_file_data,
                output_filename,
                settings.processed_dir
            )
            
            # Get the public URL for the processed video
            # Extract filename from output_filename to get the public URL
            processed_path = file_storage.get_file_path(
                output_filename,
                settings.processed_dir
            )
            logger.info(f"Processed video saved to S3, public URL: {processed_path}")
            
            # Clean up local temp file
            if os.path.exists(local_output_path):
                os.remove(local_output_path)
        else:
            # Local storage: use local path
            processed_path = local_output_path
        
        # Clean up
        video_clip.close()
        final_video.close()
        intro_clip.close()
        outro_clip.close()
        if os.path.exists(logo_path):
            os.remove(logo_path)
        
        # Clean up downloaded original video if it was from S3
        if local_video_path and os.path.exists(local_video_path):
            os.remove(local_video_path)
        
        # Update database with success
        VideoService.update_video_status(
            db, video_id, VideoStatus.processed, processed_path=processed_path
        )
        db.commit()
        
        logger.info(f"Video {video_id} processed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {str(e)}")
        
        # Update database with error
        try:
            VideoService.update_video_status(
                db, video_id, VideoStatus.failed, error_message=str(e)
            )
            db.commit()
        except Exception as db_error:
            logger.error(f"Error updating database: {db_error}")
        
        return False
        
    finally:
        db.close()


def process_message(message: Dict[str, Any]) -> bool:
    """
    Process a single SQS message
    
    Args:
        message: SQS message dictionary with 'Body', 'ReceiptHandle', etc.
        
    Returns:
        True if message should be deleted, False if it should be retried
    """
    try:
        # Parse message body
        body = json.loads(message['Body'])
        video_id = body.get('video_id')
        video_path = body.get('video_path')
        task_id = body.get('task_id', 'unknown')
        
        if not video_id or not video_path:
            logger.error(f"Invalid message format: missing video_id or video_path")
            return True  # Delete invalid message
        
        logger.info(f"Processing video {video_id} (task: {task_id})")
        
        # Process the video
        success = process_video(video_id, video_path)
        
        if success:
            logger.info(f"Successfully processed video {video_id}")
            return True  # Delete message after successful processing
        else:
            logger.warning(f"Failed to process video {video_id}, will retry")
            return False  # Don't delete, let SQS retry
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing message body: {e}")
        return True  # Delete malformed message
    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        return False  # Don't delete, let SQS retry


def run_worker():
    """Main worker loop - continuously poll SQS and process messages"""
    global shutdown_flag
    
    logger.info("Starting SQS worker...")
    logger.info(f"SQS Queue URL: {settings.sqs_queue_url}")
    logger.info(f"SQS Region: {settings.sqs_region}")
    
    if not settings.sqs_queue_url:
        logger.error("SQS queue URL not configured. Please set SQS_QUEUE_URL environment variable.")
        sys.exit(1)
    
    sqs_service = get_sqs_service()
    consecutive_empty_polls = 0
    max_empty_polls = 10  # After 10 empty polls, log status
    
    while not shutdown_flag:
        try:
            # Receive messages from SQS
            messages = sqs_service.receive_messages(max_messages=1)
            
            if not messages:
                consecutive_empty_polls += 1
                if consecutive_empty_polls >= max_empty_polls:
                    logger.debug(f"No messages in queue (polled {consecutive_empty_polls} times)")
                    consecutive_empty_polls = 0
                continue
            
            # Reset empty poll counter
            consecutive_empty_polls = 0
            
            # Process each message
            for message in messages:
                if shutdown_flag:
                    logger.info("Shutdown requested, stopping message processing")
                    break
                
                receipt_handle = message.get('ReceiptHandle')
                if not receipt_handle:
                    logger.warning("Message missing ReceiptHandle, skipping")
                    continue
                
                # Process the message
                should_delete = process_message(message)
                
                if should_delete:
                    # Delete message from queue after successful processing
                    sqs_service.delete_message(receipt_handle)
                    logger.debug("Message deleted from queue")
                else:
                    # Message will become visible again after visibility timeout
                    logger.debug("Message will be retried after visibility timeout")
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            shutdown_flag = True
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            time.sleep(5)  # Wait before retrying
    
    logger.info("SQS worker stopped")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run worker
    run_worker()

