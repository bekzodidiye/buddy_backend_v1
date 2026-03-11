from rest_framework import serializers
import base64
import uuid
from django.core.files.base import ContentFile
from .models import (
    User, SocialLink, Season, Monitoring, 
    WeeklyHighlight, Notification, ChatMessage, PlatformSetting
)

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            # Base64 rasm kelsay
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            id = uuid.uuid4()
            data = ContentFile(base64.b64decode(imgstr), name=f"{id}.{ext}")
        elif isinstance(data, str) and (data.startswith('http') or data.startswith('/media/')):
            # Agar oldindan mavjud rasm URL manzili kesa uni fayl yo'liga (relative path) o'zgartirib qaytarish
            if '/media/' in data:
                return data.split('/media/')[-1]
            return data
        elif not data:
            # Bo'sh string yoki null kelsa
            return None
        return super().to_internal_value(data)

class SocialLinkSerializer(serializers.ModelSerializer):
    iconUrl = Base64ImageField(source='icon_image', required=False, allow_null=True)
    linkUrl = serializers.URLField(source='link_url')
    
    class Meta:
        model = SocialLink
        fields = ['id', 'iconUrl', 'linkUrl']

class UserSerializer(serializers.ModelSerializer):
    socialLinks = SocialLinkSerializer(source='social_links', many=True, required=False)
    longBio = serializers.CharField(source='long_bio', allow_blank=True, allow_null=True, required=False)
    fieldDescription = serializers.CharField(source='field_description', allow_blank=True, allow_null=True, required=False)
    motivationQuote = serializers.CharField(source='motivation_quote', allow_blank=True, allow_null=True, required=False)
    isApproved = serializers.BooleanField(source='is_approved', required=False)
    assignedCuratorId = serializers.PrimaryKeyRelatedField(source='assigned_curator', queryset=User.objects.all(), allow_null=True, required=False)
    avatar = Base64ImageField(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    field = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    username = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    createdAt = serializers.DateTimeField(source='date_joined', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 'role', 'status', 'avatar', 
            'field', 'longBio', 'fieldDescription', 'motivationQuote', 'skills', 
            'isApproved', 'assignedCuratorId', 'socialLinks', 'createdAt', 'password'
        ]
    def update(self, instance, validated_data):
        # Parolni xavfsiz saqlash
        password = validated_data.pop('password', None)
        if password: # Bo'sh bo'lmasa
            instance.set_password(password)

        # Ijtimoiy tarmoqlar
        social_links_data = validated_data.pop('social_links', None)
        
        # Avatar agar URL bo'lib kelsa, uni rasm sifatida qayta saqlamaymiz
        if 'avatar' in validated_data and validated_data['avatar'] is None:
            # Agar frontend URL yoki null yuborgan bo'lsa (Base64ImageField None qaytaradi)
            # biz faqat haqiqiy File ob'ekti kelsagina yangilaymiz.
            if not self.initial_data.get('avatar'):
                 # Bu holatda foydalanuvchi rasmni o'chirgan bo'lishi mumkin
                 instance.avatar = None
            else:
                 # Aks holda, mavjud rasm qolaversin
                 validated_data.pop('avatar')

        # Qolgan maydonlarni yangilash
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Ijtimoiy tarmoqlarni yangilash
        if social_links_data is not None:
            instance.social_links.all().delete()
            # Max 5 links
            for sl_data in social_links_data[:5]:
                # sl_data keys will be 'icon_url' and 'link_url' thanks to Serializer source
                sl_data.pop('id', None) # ID ni olib tashlaymiz, chunki yangi yaratamiz
                SocialLink.objects.create(user=instance, **sl_data)

        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'name', 'role', 'field']
        
    def validate_username(self, value):
        if ' ' in value:
            raise serializers.ValidationError("Username tarkibida bo'sh joy bo'lishi mumkin emas")
        return value.lower()

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            role=validated_data.get('role', 'student'),
            status='pending' if validated_data.get('role') == 'curator' else 'active',
            field=validated_data.get('field', '')
        )
        return user

class SeasonSerializer(serializers.ModelSerializer):
    durationInMonths = serializers.IntegerField(source='duration_months', required=False)
    startDate = serializers.DateField(source='start_date')
    isActive = serializers.BooleanField(source='is_active')
    
    class Meta:
        model = Season
        fields = ['id', 'number', 'startDate', 'isActive', 'durationInMonths']

class MonitoringSerializer(serializers.ModelSerializer):
    curatorId = serializers.PrimaryKeyRelatedField(source='curator', queryset=User.objects.all())
    seasonId = serializers.PrimaryKeyRelatedField(source='season', queryset=Season.objects.all())
    studentId = serializers.PrimaryKeyRelatedField(source='student', queryset=User.objects.all(), required=False, allow_null=True)
    weekNumber = serializers.IntegerField(source='week_number')
    studentName = serializers.CharField(source='student_name', allow_blank=True, allow_null=True, required=False)
    weeklyGoal = serializers.CharField(source='weekly_goal', allow_blank=True, allow_null=True, required=False)
    difficulty = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    solution = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    meetingDay = serializers.DateTimeField(source='meeting_day', allow_null=True, required=False)
    
    class Meta:
        model = Monitoring
        fields = [
            'id', 'curatorId', 'seasonId', 'weekNumber', 'studentId', 
            'studentName', 'weeklyGoal', 'difficulty', 'solution', 
            'status', 'meetingDay', 'attended'
        ]

class WeeklyHighlightSerializer(serializers.ModelSerializer):
    curatorId = serializers.PrimaryKeyRelatedField(source='curator', queryset=User.objects.all())
    seasonId = serializers.PrimaryKeyRelatedField(source='season', queryset=Season.objects.all())
    weekNumber = serializers.IntegerField(source='week_number')
    photoUrl = serializers.URLField(source='photo_url', allow_blank=True, allow_null=True, required=False)
    uploadedBy = serializers.CharField(source='uploaded_by', allow_blank=True, allow_null=True, required=False)
    
    class Meta:
        model = WeeklyHighlight
        fields = ['id', 'curatorId', 'seasonId', 'weekNumber', 'photoUrl', 'image', 'uploadedBy']

class NotificationSerializer(serializers.ModelSerializer):
    targetRole = serializers.CharField(source='target_role', default='all', required=False)
    targetUserId = serializers.PrimaryKeyRelatedField(
        source='target_user', 
        queryset=User.objects.all(), 
        required=False, 
        allow_null=True
    )
    isRead = serializers.BooleanField(source='is_read', default=False)
    timestamp = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'timestamp', 'isRead', 'targetRole', 'targetUserId', 'sender']
        read_only_fields = ['id', 'timestamp']

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'

class PlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = '__all__'
