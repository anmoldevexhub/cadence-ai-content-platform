from rest_framework import serializers
from .models import Website, SocialConnection, ScrapeResult, SampleContent

class SocialConnectionSerializer(serializers.ModelSerializer):
    auth_payload = serializers.SerializerMethodField()
    auth_payload_write = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = SocialConnection
        fields = ['id', 'platform', 'make_webhook_url', 'is_active', 'connected_at', 'auth_type', 'auth_payload', 'auth_payload_write']
        read_only_fields = ['id', 'connected_at', 'auth_payload']

    def get_auth_payload(self, obj):
        if not obj.auth_payload:
            return {}
        try:
            from websites.utils import decrypt_value
            import json
            decrypted = decrypt_value(obj.auth_payload)
            data = json.loads(decrypted)
            masked = {}
            for k, v in data.items():
                # Mask sensitive key names but keep name fields visible (like api_key_name)
                if any(sec in k.lower() for sec in ['value', 'password', 'token', 'secret', 'pass']) and 'name' not in k.lower():
                    masked[k] = "••••••••" if v else ""
                else:
                    masked[k] = v
            return masked
        except Exception:
            return {}

    def create(self, validated_data):
        auth_payload_write = validated_data.pop('auth_payload_write', None)
        instance = super().create(validated_data)
        if auth_payload_write:
            from websites.utils import encrypt_value
            import json
            instance.auth_payload = encrypt_value(json.dumps(auth_payload_write))
            instance.save(update_fields=['auth_payload'])
        return instance

    def update(self, instance, validated_data):
        auth_payload_write = validated_data.pop('auth_payload_write', None)
        instance = super().update(instance, validated_data)
        if auth_payload_write is not None:
            from websites.utils import encrypt_value, decrypt_value
            import json
            
            existing_data = {}
            if instance.auth_payload:
                try:
                    existing_data = json.loads(decrypt_value(instance.auth_payload))
                except Exception:
                    pass
            
            # Merge and preserve old values if placeholder is sent
            merged_data = {}
            for k, v in auth_payload_write.items():
                if v == "••••••••" and k in existing_data:
                    merged_data[k] = existing_data[k]
                else:
                    merged_data[k] = v
            
            instance.auth_payload = encrypt_value(json.dumps(merged_data))
            instance.save(update_fields=['auth_payload'])
        return instance

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
    domain = serializers.CharField(max_length=200)
    
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

    def validate_domain(self, value):
        domain_val = value.strip()
        qs = Website.objects.filter(domain=domain_val, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("website with this domain already exists.")
        return domain_val

    def create(self, validated_data):
        domain = validated_data.get('domain')
        if domain:
            Website.objects.filter(domain=domain, is_deleted=True).delete()

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
        domain = validated_data.get('domain')
        if domain:
            Website.objects.filter(domain=domain, is_deleted=True).exclude(pk=instance.pk).delete()

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