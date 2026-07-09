from rest_framework import serializers
from .models import LoginLog, ActivityLog

class LoginLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LoginLog
        fields = [
            'id', 'user', 'user_email', 'user_name', 'email', 'ip_address',
            'user_agent', 'location_city', 'location_country', 'success', 'timestamp'
        ]

class ActivityLogSerializer(serializers.ModelSerializer):
    actor_name_display = serializers.CharField(source='actor_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'actor', 'actor_name', 'actor_name_display', 'action',
            'action_display', 'target_description', 'ip_address', 'metadata', 'timestamp'
        ]