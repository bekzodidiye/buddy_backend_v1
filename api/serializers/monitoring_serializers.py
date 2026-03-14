from __future__ import annotations

import logging
from typing import Any, Dict

from rest_framework import serializers

from ..models import User, Season, Monitoring, WeeklyHighlight

logger = logging.getLogger(__name__)


class SeasonSerializer(serializers.ModelSerializer):
    durationInMonths = serializers.IntegerField(source='duration_months', required=False)
    startDate = serializers.DateField(source='start_date')
    isActive = serializers.BooleanField(source='is_active')

    class Meta:
        model = Season
        fields = ['id', 'number', 'startDate', 'isActive', 'durationInMonths']


class MonitoringSerializer(serializers.ModelSerializer):
    curatorId = serializers.UUIDField(source='curator_id', read_only=True)
    seasonId = serializers.UUIDField(source='season_id', read_only=True)
    studentId = serializers.UUIDField(source='student_id', allow_null=True, required=False)

    curator = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    season = serializers.PrimaryKeyRelatedField(queryset=Season.objects.all(), write_only=True, required=False)
    student = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='student'), 
        write_only=True, 
        allow_null=True, 
        required=False
    )

    weekNumber = serializers.IntegerField(source='week_number')
    studentName = serializers.CharField(source='student_name', allow_blank=True, allow_null=True, required=False)
    weeklyGoal = serializers.CharField(source='weekly_goal', allow_blank=True, allow_null=True, required=False)
    meetingDay = serializers.DateTimeField(source='meeting_day', allow_null=True, required=False)

    class Meta:
        model = Monitoring
        fields = [
            'id', 'curatorId', 'seasonId', 'weekNumber', 'studentId',
            'studentName', 'weeklyGoal', 'difficulty', 'solution',
            'status', 'meetingDay', 'attended',
            'curator', 'season', 'student',
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

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        photo_url = data.get('photo_url') or (self.instance.photo_url if self.instance else None)
        image = data.get('image') or (self.instance.image if self.instance else None)
        
        if not photo_url and not image:
            raise serializers.ValidationError("Either a photo URL or an image file must be provided.")
        return data
