import os
import uuid
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
from celery import current_task
from sqlalchemy.orm import Session
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.video_service import VideoService
from app.services.file_storage import get_file_storage
from app.models.video import VideoStatus
from app.core.config import settings
import logging

# Fix for PIL.Image.ANTIALIAS compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)


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


@celery_app.task(bind=True)
def process_video_task(self, video_id: str, video_path: str):
    """Process video: trim, resize, add watermark"""
    db = SessionLocal()
    file_storage = get_file_storage()
    
    try:
        # Update status to processing
        VideoService.update_video_status(db, video_id, VideoStatus.processing)
        
        # Load video
        video_clip = VideoFileClip(video_path)
        
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
        output_path = os.path.join(settings.processed_dir, output_filename)
        
        # Ensure output directory exists
        os.makedirs(settings.processed_dir, exist_ok=True)
        
        # Export processed video
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac' if final_video.audio else None,
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=24
        )
        
        # Clean up
        video_clip.close()
        final_video.close()
        intro_clip.close()
        outro_clip.close()
        if os.path.exists(logo_path):
            os.remove(logo_path)
        
        # Update database with success
        VideoService.update_video_status(
            db, video_id, VideoStatus.processed, processed_path=output_path
        )
        
        logger.info(f"Video {video_id} processed successfully")
        return f"Video processed successfully: {output_path}"
        
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {str(e)}")
        
        # Update database with error
        VideoService.update_video_status(
            db, video_id, VideoStatus.failed, error_message=str(e)
        )
        
        # Re-raise the exception so Celery can handle retries
        raise self.retry(exc=e, countdown=60, max_retries=3)
        
    finally:
        db.close()