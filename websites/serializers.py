from rest_framework import serializers
from .models import Website, SocialConnection, ScrapeResult, SampleContent

class SocialConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialConnection
        fields = ['id', 'platform', 'make_webhook_url', 'is_active', 'connected_at']
        read_only_fields = ['id', 'connected_at']

class ScrapeResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapeResult
        fields = [
            'id', 'page_url', 'page_title', 'raw_text', 'heading_structure',
            'meta_title', 'meta_description', 'og_properties', 'publication_date',
            'author', 'categories_tags', 'image_alts', 'page_type',
            'readability_metrics', 'sentiment_metrics', 'entities', 'key_phrases',
            'comments', 'ctas', 'main_content', 'crawled_at'
        ]

class WebsiteSerializer(serializers.ModelSerializer):
    social_connections = SocialConnectionSerializer(many=True, read_only=True)
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    logo_upload = serializers.CharField(required=False, write_only=True)
    
    class Meta:
        model = Website
        fields = [
            'id', 'name', 'domain', 'url', 'industry', 'tone', 'topics',
            'status', 'color', 'brand_colors', 'avg_read_time', 'owner', 'owner_email', 'owner_name',
            'created_at', 'updated_at', 'scrape_summary', 'scrape_status',
            'last_crawled', 'social_connections', 'style_guide', 'needs_crawl',
            'contact_email', 'contact_phone', 'logo_url', 'logo_upload', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner']

    def create(self, validated_data):
        logo_upload = validated_data.pop('logo_upload', None)
        logo_url = validated_data.get('logo_url', '')
        instance = super().create(validated_data)
        
        if logo_upload:
            from .crawler import save_logo_from_base64
            instance.logo_url = save_logo_from_base64(instance, logo_upload)
            instance.save(update_fields=['logo_url'])
        elif logo_url:
            from .crawler import download_and_save_logo
            instance.logo_url = download_and_save_logo(instance, logo_url)
            instance.save(update_fields=['logo_url'])
            
        return instance

    def update(self, instance, validated_data):
        logo_upload = validated_data.pop('logo_upload', None)
        logo_url = validated_data.get('logo_url', None)
        
        instance = super().update(instance, validated_data)
        
        updated = False
        if logo_upload:
            from .crawler import save_logo_from_base64
            instance.logo_url = save_logo_from_base64(instance, logo_upload)
            updated = True
        elif logo_url is not None:
            from .crawler import download_and_save_logo
            instance.logo_url = download_and_save_logo(instance, logo_url)
            updated = True
            
        if updated:
            instance.save(update_fields=['logo_url'])
            
        return instance


class SampleContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleContent
        fields = ['id', 'platform', 'title', 'content', 'file_name', 'uploaded_at', 'is_active']
        read_only_fields = ['id', 'uploaded_at']