import base64
import os
import uuid
from django.conf import settings
from rest_framework import serializers
from .models import ContentIdea, ContentDraft, ScheduledPost

class ContentIdeaSerializer(serializers.ModelSerializer):
    website_name = serializers.CharField(source='website.name', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    
    class Meta:
        model = ContentIdea
        fields = [
            'id', 'website', 'website_name', 'submitted_by', 'submitted_by_name',
            'title', 'context', 'platform', 'meta_tags', 'target_date', 'target_time',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'submitted_by']

class ContentDraftSerializer(serializers.ModelSerializer):
    website_name = serializers.CharField(source='website.name', read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    cover_image = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = ContentDraft
        fields = [
            'id', 'idea', 'website', 'website_name', 'platform', 'platform_display',
            'title', 'body', 'excerpt', 'meta_description', 'meta_title', 'tags', 'word_count',
            'status', 'status_display', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'rejection_reason', 'ai_model', 'generation_prompt',
            'cover_image', 'category', 'is_deleted', 'created_at', 'updated_at',
            'author_name', 'custom_date'
        ]
        read_only_fields = ['id', 'word_count', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        cover_image = data.get('cover_image')
        if cover_image and (cover_image.startswith('data:image/') or cover_image.startswith('data:video/')):
            # Convert internal data to mutable dict copy
            mutable_data = data.copy()
            mutable_data['cover_image'] = self.save_cover_from_base64(cover_image)
            data = mutable_data
            
        return super().to_internal_value(data)

    def save_cover_from_base64(self, base64_data):
        try:
            if ',' in base64_data:
                header, encoded = base64_data.split(",", 1)
            else:
                header, encoded = "", base64_data
                
            ext = "png"
            if "image/svg" in header:
                ext = "svg"
            elif "image/jpeg" in header or "image/jpg" in header:
                ext = "jpg"
            elif "image/gif" in header:
                ext = "gif"
            elif "video/mp4" in header:
                ext = "mp4"
            elif "video/webm" in header:
                ext = "webm"
            elif "video/ogg" in header:
                ext = "ogv"
            elif "video/quicktime" in header:
                ext = "mov"
                
            data = base64.b64decode(encoded)
            
            covers_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers')
            os.makedirs(covers_dir, exist_ok=True)
            
            filename = f"cover_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(covers_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(data)
                
            # Compress image files using Pillow to prevent 413 Payload Too Large errors
            if ext in ["png", "jpg", "jpeg", "svg"]: # svg is text, skip compression
                if ext != "svg":
                    try:
                        from PIL import Image
                        with Image.open(filepath) as img:
                            # Convert to RGB mode (needed for JPEG format)
                            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                # Handle transparency mask
                                mask = img.split()[3] if img.mode == 'RGBA' else None
                                background.paste(img, mask=mask)
                                img = background
                            elif img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Replace filename and filepath with optimized JPEG
                            orig_filepath = filepath
                            filename = f"cover_{uuid.uuid4().hex}.jpg"
                            filepath = os.path.join(covers_dir, filename)
                            img.save(filepath, 'JPEG', quality=85, optimize=True)
                            
                            # Clean up the original uncompressed file if it's different
                            if os.path.exists(orig_filepath) and orig_filepath != filepath:
                                os.remove(orig_filepath)
                    except Exception as compression_err:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Image compression failed, using original file: {compression_err}")
                
            # If it's a video, try uploading to Cloudinary
            if ext in ["mp4", "webm", "ogv", "mov"]:
                try:
                    from content.publisher import upload_video_to_cloudinary
                    cloudinary_url = upload_video_to_cloudinary(filepath)
                    if cloudinary_url:
                        if os.path.exists(filepath):
                            try:
                                os.remove(filepath)
                            except Exception:
                                pass
                        return cloudinary_url
                except Exception as video_upload_err:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to upload video to Cloudinary: {video_upload_err}")
            
            # If it's an image, try uploading to ImgBB
            elif ext in ["png", "jpg", "jpeg", "svg"]:
                try:
                    from content.generator import _upload_bytes_to_imgbb
                    with open(filepath, 'rb') as img_f:
                        public_url = _upload_bytes_to_imgbb(img_f.read(), filename)
                    if public_url:
                        if os.path.exists(filepath):
                            try:
                                os.remove(filepath)
                            except Exception:
                                pass
                        return public_url
                except Exception as img_upload_err:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to upload image to ImgBB: {img_upload_err}")
                
            return f"/static/media/covers/{filename}"
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save base64 cover image/video: {e}")
            return base64_data

class ScheduledPostSerializer(serializers.ModelSerializer):
    draft_title = serializers.CharField(source='draft.title', read_only=True)
    website_name = serializers.CharField(source='draft.website.name', read_only=True)
    platform = serializers.CharField(source='draft.platform', read_only=True)
    
    class Meta:
        model = ScheduledPost
        fields = [
            'id', 'draft', 'draft_title', 'website_name', 'platform',
            'scheduled_for', 'published_at', 'make_response', 'is_published'
        ]
        read_only_fields = ['id', 'published_at', 'make_response', 'is_published']