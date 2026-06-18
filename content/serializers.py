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
            'title', 'body', 'excerpt', 'meta_description', 'tags', 'word_count',
            'status', 'status_display', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'rejection_reason', 'ai_model', 'generation_prompt',
            'cover_image', 'category', 'is_deleted', 'created_at', 'updated_at',
            'author_name', 'custom_date'
        ]
        read_only_fields = ['id', 'word_count', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        cover_image = data.get('cover_image')
        if cover_image and cover_image.startswith('data:image/'):
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
                
            data = base64.b64decode(encoded)
            
            covers_dir = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers')
            os.makedirs(covers_dir, exist_ok=True)
            
            filename = f"cover_{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(covers_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(data)
                
            return f"/static/media/covers/{filename}"
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save base64 cover image: {e}")
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