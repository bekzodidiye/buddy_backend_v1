from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from rest_framework import serializers

from ..models import User, SocialLink
from .base import Base64ImageField

logger = logging.getLogger(__name__)


class SocialLinkSerializer(serializers.ModelSerializer):
    iconUrl = Base64ImageField(source='icon_image', required=False, allow_null=True)
    linkUrl = serializers.URLField(source='link_url')

    class Meta:
        model = SocialLink
        fields = ['id', 'iconUrl', 'linkUrl']


class UserSerializer(serializers.ModelSerializer):
    socialLinks = SocialLinkSerializer(source='social_links', many=True, required=False)
    # Ba'zan frontend snake_case kutadi
    social_links = SocialLinkSerializer(many=True, read_only=True)
    
    longBio = serializers.CharField(source='long_bio', allow_blank=True, allow_null=True, required=False)
    fieldDescription = serializers.CharField(source='field_description', allow_blank=True, allow_null=True, required=False)
    motivationQuote = serializers.CharField(source='motivation_quote', allow_blank=True, allow_null=True, required=False)
    isApproved = serializers.BooleanField(source='is_approved', read_only=True)
    assignedCuratorId = serializers.UUIDField(source='assigned_curator_id', allow_null=True, required=False)
    startupCuratorId = serializers.UUIDField(source='startup_curator_id', allow_null=True, required=False)
    isSuperCurator = serializers.BooleanField(source='is_super_curator', read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 'role', 'status', 'avatar',
            'field', 'longBio', 'fieldDescription', 'motivationQuote', 'skills',
            'isApproved', 'assignedCuratorId', 'startupCuratorId', 'isSuperCurator', 'socialLinks', 'social_links', 
            'createdAt', 'updatedAt'
        ]
        read_only_fields = ['id', 'username']

    def validate_assignedCuratorId(self, value: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
        if value is None:
            return value
        if not User.objects.filter(pk=value, role='curator').exists():
            raise serializers.ValidationError("Specified curator does not exist.")
        return value

    def update(self, instance: User, validated_data: Dict[str, Any]) -> User:
        social_links_data = validated_data.pop('social_links', None)
        
        # Avatar handling
        if 'avatar' in validated_data and validated_data['avatar'] is None:
            initial_avatar = self.initial_data.get('avatar')
            if isinstance(initial_avatar, str) and initial_avatar != '':
                validated_data.pop('avatar')

        instance = super().update(instance, validated_data)

        # Smart Social Links update
        if social_links_data is not None:
            existing_links = {str(link.id): link for link in instance.social_links.all()}
            preserved_ids = []
            
            # Initial data for checking original values
            initial_sl_list = self.initial_data.get('socialLinks', [])

            for i, sl_data in enumerate(social_links_data[:5]):
                # Support both 'id' from validated_data or matching from initial_data
                link_id = None
                if i < len(initial_sl_list):
                    link_id = str(initial_sl_list[i].get('id', ''))

                if link_id and link_id in existing_links:
                    # Update existing link
                    link_instance = existing_links[link_id]
                    
                    # If icon_image is None, check if we should keep the old one
                    if sl_data.get('icon_image') is None:
                        # Extract from initial to check if it was a URL
                        init_icon = initial_sl_list[i].get('iconUrl')
                        if isinstance(init_icon, str) and init_icon != '' and not init_icon.startswith('data:'):
                            sl_data.pop('icon_image', None) # Don't overwrite with None
                    
                    for attr, value in sl_data.items():
                        setattr(link_instance, attr, value)
                    link_instance.save()
                    preserved_ids.append(link_instance.id)
                else:
                    # Create new link
                    new_link = SocialLink.objects.create(user=instance, **sl_data)
                    preserved_ids.append(new_link.id)

            # Delete orphan links
            instance.social_links.exclude(id__in=preserved_ids).delete()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'name', 'role', 'field']

    def validate_username(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def create(self, validated_data: Dict[str, Any]) -> User:
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            role=validated_data.get('role', 'student'),
            status='pending' if validated_data.get('role') == 'curator' else 'active',
            is_approved=(validated_data.get('role') != 'curator')
        )
