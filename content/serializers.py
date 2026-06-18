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
    
    class Meta:
        model = ContentDraft
        fields = [
            'id', 'idea', 'website', 'website_name', 'platform', 'platform_display',
            'title', 'body', 'excerpt', 'meta_description', 'tags', 'word_count',
            'status', 'status_display', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'rejection_reason', 'ai_model', 'generation_prompt',
            'cover_image', 'category', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'word_count', 'created_at', 'updated_at']

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