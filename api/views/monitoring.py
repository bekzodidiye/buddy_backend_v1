from __future__ import annotations

from rest_framework import permissions, viewsets
from rest_framework.request import Request

from ..models import Season, WeeklyHighlight
from ..permissions import IsAdminRole
from ..serializers import (
    MonitoringSerializer,
    SeasonSerializer,
    WeeklyHighlightSerializer,
)
from ..services.monitoring_service import (
    get_monitoring_queryset,
)


class SeasonViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return Season.objects.all().order_by("number")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminRole()]
        return [permissions.IsAuthenticatedOrReadOnly()]


class MonitoringViewSet(viewsets.ModelViewSet):
    """
    Monitoring CRUD — role-scoped via service layer.
    """
    serializer_class = MonitoringSerializer
    pagination_class = None

    def get_queryset(self):
        qs = get_monitoring_queryset(self.request.user)
        
        season_id = self.request.query_params.get("season")
        week = self.request.query_params.get("week")
        curator = self.request.query_params.get("curator")

        if season_id: qs = qs.filter(season_id=season_id)
        if week: qs = qs.filter(week_number=week)
        if curator: qs = qs.filter(curator_id=curator)

        return qs

    def perform_create(self, serializer: MonitoringSerializer) -> None:
        serializer.save(curator=self.request.user)


class WeeklyHighlightViewSet(viewsets.ModelViewSet):
    serializer_class = WeeklyHighlightSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return WeeklyHighlight.objects.select_related("curator", "season")
