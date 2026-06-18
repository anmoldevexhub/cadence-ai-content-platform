from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    initials = serializers.ReadOnlyField()
    full_name = serializers.SerializerMethodField()
    website_count = serializers.SerializerMethodField()
    last_login_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'full_name', 'role', 'is_active', 'avatar_color',
                  'initials', 'website_count', 'last_login_display',
                  'date_joined']
        read_only_fields = ['date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_website_count(self, obj):
        return obj.websites.count()

    def get_last_login_display(self, obj):
        if obj.last_login:
            from django.utils.timesince import timesince
            return f"{timesince(obj.last_login)} ago"
        return 'Never'


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'first_name', 'last_name',
                  'password', 'role', 'avatar_color']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()




from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
    

