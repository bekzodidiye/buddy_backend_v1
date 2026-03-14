from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser, TimestampedModel):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('curator', 'Curator'),
        ('student', 'Student'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student', db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    field = models.CharField(max_length=100, null=True, blank=True)
    long_bio = models.TextField(null=True, blank=True)
    field_description = models.TextField(null=True, blank=True)
    motivation_quote = models.CharField(max_length=150, null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    assigned_curator = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='students'
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
            self.is_approved = True
            self.status = 'active'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta(AbstractUser.Meta):
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role', 'status', 'is_approved'], name='user_role_status_approved_idx'),
        ]


class SocialLink(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_links')
    icon_image = models.ImageField(upload_to='social_icons/', null=True, blank=True)
    link_url = models.URLField()

    def __str__(self):
        return f"{self.user.username} - {self.link_url}"

    class Meta:
        ordering = ['-created_at']


class Season(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveIntegerField(unique=True)
    start_date = models.DateField()
    is_active = models.BooleanField(default=False, db_index=True)
    duration_months = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Mavsum {self.number}"

    class Meta:
        ordering = ['number']


class Monitoring(TimestampedModel):
    STATUS_CHOICES = (
        ('Bajarilmoqda', 'Bajarilmoqda'),
        ('Hal qilindi', 'Hal qilindi'),
        ('Kutilmoqda', 'Kutilmoqda'),
        ('Bajarmadi', 'Bajarmadi'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='curated_reports')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='monitorings')
    week_number = models.IntegerField(db_index=True)
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='progress_reports', null=True
    )
    student_name = models.CharField(max_length=255, null=True, blank=True)
    weekly_goal = models.TextField(null=True, blank=True)
    difficulty = models.TextField(null=True, blank=True)
    solution = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Kutilmoqda', db_index=True)
    meeting_day = models.DateTimeField(null=True, blank=True)
    attended = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student_name} - Hafta {self.week_number}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['season', 'curator'], name='monitoring_season_curator_idx'),
            models.Index(fields=['season', 'week_number'], name='monitoring_season_week_idx'),
            models.Index(fields=['student'], name='monitoring_student_idx'),
        ]


class WeeklyHighlight(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curator = models.ForeignKey(User, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week_number = models.IntegerField(db_index=True)
    photo_url = models.URLField(null=True, blank=True)
    image = models.ImageField(upload_to='highlights/', null=True, blank=True)
    uploaded_by = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Highlight: Season {self.season_id} Week {self.week_number}"

    class Meta:
        ordering = ['-created_at']


class Notification(TimestampedModel):
    TYPE_CHOICES = (
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('urgent', 'Urgent'),
    )
    ROLE_CHOICES = (
        ('all', 'All'),
        ('admin', 'Admin'),
        ('curator', 'Curator'),
        ('student', 'Student'),
        ('none', 'None'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False)
    target_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='all', db_index=True)
    target_user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications'
    )
    sender = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"[{self.type}] {self.title}"

    class Meta:
        ordering = ['-created_at']


class ChatMessage(TimestampedModel):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('model', 'Model'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"[{self.role}] {self.user_id} @ {self.timestamp}"

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='chat_user_created_idx'),
        ]


class PlatformSetting(TimestampedModel):
    key = models.CharField(max_length=255, unique=True, primary_key=True)
    value = models.TextField()
    description = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.key

    class Meta:
        ordering = ['key']
