from django.db import models
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .models import (
    User, Season, Monitoring, WeeklyHighlight, Notification, 
    ChatMessage, PlatformSetting
)
from .serializers import (
    UserSerializer, RegisterSerializer, SeasonSerializer, MonitoringSerializer, 
    WeeklyHighlightSerializer, NotificationSerializer, ChatMessageSerializer, 
    PlatformSettingSerializer
)
import requests
import json
import urllib3

# SSL ogohlantirishlarini o'chirish
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IsAdminRole(permissions.BasePermission):
    """Role='admin' bo'lgan foydalanuvchilarga ruxsat beradi"""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', '') == 'admin'
        )

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    serializer = UserSerializer(request.user, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_intra(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    
    # Agar to'liq email kiritilgan bo'lsa, faqat loginni olamiz
    if '@' in username:
        username = username.split('@')[0]
    
    if not username or not password:
        return Response({"detail": "Username va parol kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Avval bazada borligini tekshiramiz
    if User.objects.filter(username=username).exists():
        return Response({"detail": "Siz allaqachon ro'yxatdan o'tgansiz. Iltimos, login orqali kiring."}, status=status.HTTP_400_BAD_REQUEST)
    
    url = "https://auth.21-school.ru/auth/realms/EduPowerKeycloak/protocol/openid-connect/token"
    payload = {
        'client_id': 's21-open-api',
        'username': username,
        'password': password,
        'grant_type': 'password'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    try:
        # verify=False muhim, chunki ba'zi internal maktab tarmoqlarida sertifikatlar xato bo'lishi mumkin
        response = requests.post(url, data=payload, headers=headers, timeout=25, verify=False)
        
        # Debug uchun terminalga chiqarish
        print(f"DEBUG: Keycloak request for '{username}'")
        print(f"DEBUG: Status Code: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            # Userinfo so'rovi
            userinfo_url = "https://auth.21-school.ru/auth/realms/EduPowerKeycloak/protocol/openid-connect/userinfo"
            userinfo_headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': headers['User-Agent']
            }
            userinfo_res = requests.get(userinfo_url, headers=userinfo_headers, timeout=20, verify=False)
            
            fullname = username 
            email = f"{username}@student.21-school.ru"
            
            if userinfo_res.status_code == 200:
                user_details = userinfo_res.json()
                fullname = user_details.get('name') or user_details.get('preferred_username') or username
                email = user_details.get('email') or email
                
            return Response({
                "success": True, 
                "username": username,
                "name": fullname,
                "email": email
            })
        else:
            # Agar 200 bo'lmasa, batafsil xato xabarini yig'ishga harakat qilamiz
            print(f"DEBUG: Keycloak error body: {response.text}")
            msg = f"Status: {response.status_code}. "
            try:
                err_json = response.json()
                # Keycloak usually returns error and error_description
                msg += err_json.get('error_description') or err_json.get('error') or response.text[:100]
            except:
                msg += response.text[:100]
            return Response({"detail": msg}, status=status.HTTP_401_UNAUTHORIZED)
            
    except requests.exceptions.RequestException as e:
        return Response({"detail": f"Ulanishda xatolik: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return User.objects.none()
            
        if user.role == 'admin':
            return User.objects.all()
            
        # Default: approved active users PLUS the user themselves (so they can edit/PATCH themselves)
        base_filter = models.Q(status='active', is_approved=True) | models.Q(id=user.id)
        
        if user.role == 'curator':
            # Curators see students + active users + themselves
            return User.objects.filter(models.Q(role='student') | base_filter).distinct()
            
        return User.objects.filter(base_filter).distinct()

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminRole()]
        return [permissions.IsAuthenticated()]

class MonitoringViewSet(viewsets.ModelViewSet):
    queryset = Monitoring.objects.all()
    serializer_class = MonitoringSerializer
    
    def get_queryset(self):
        user = self.request.user
        qs = Monitoring.objects.all()
        
        season_id = self.request.query_params.get('season')
        week = self.request.query_params.get('week')
        curator = self.request.query_params.get('curator')
        
        if season_id:
            qs = qs.filter(season_id=season_id)
        if week:
            qs = qs.filter(week_number=week)
        if curator:
            qs = qs.filter(curator_id=curator)
            
        if user.role == 'admin':
            return qs
        elif user.role == 'curator':
            return qs.filter(curator=user)
        return qs.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(curator=self.request.user)

class WeeklyHighlightViewSet(viewsets.ModelViewSet):
    queryset = WeeklyHighlight.objects.all()
    serializer_class = WeeklyHighlightSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.all().order_by('-timestamp')
        if getattr(user, 'role', '') == 'admin':
            return qs
        return qs.filter(
            models.Q(target_user=user) | models.Q(target_role='all') | models.Q(target_role=user.role)
        ).distinct()

class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    
    def get_queryset(self):
        return ChatMessage.objects.filter(user=self.request.user).order_by('timestamp')

    def create(self, request, *args, **kwargs):
        # Yuborilgan xabarni saqlash
        user_msg = ChatMessage.objects.create(
            user=request.user,
            role='user',
            text=request.data.get('text', '')
        )
        # Dummy AI javobini saqlash
        ai_msg = ChatMessage.objects.create(
            user=request.user,
            role='model',
            text=f"AI Buddy: Sizning xabaringizni qabul qildim ({user_msg.text}). Qanday yordam berishim mumkin?"
        )
        return Response(ChatMessageSerializer([user_msg, ai_msg], many=True).data)

class PlatformSettingViewSet(viewsets.ModelViewSet):
    queryset = PlatformSetting.objects.all()
    serializer_class = PlatformSettingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'key'

# --- Admin API endpointlar (Extra) ---

@api_view(['GET'])
@permission_classes([IsAdminRole])
def admin_stats(request):
    users_count = User.objects.count()
    monitoring_count = Monitoring.objects.count()
    return Response({
        "total_users": users_count,
        "total_monitorings": monitoring_count,
        "active_curators": User.objects.filter(role='curator', is_approved=True).count(),
    })

@api_view(['PATCH'])
@permission_classes([IsAdminRole])
def admin_user_role(request, pk):
    try:
        user = User.objects.get(pk=pk)
        user.role = request.data.get('role', user.role)
        user.save()
        return Response(UserSerializer(user).data)
    except User.DoesNotExist:
        return Response(status=404)

@api_view(['PATCH'])
@permission_classes([IsAdminRole])
def admin_user_status(request, pk):
    try:
        user = User.objects.get(pk=pk)
        user.status = request.data.get('status', user.status)
        user.save()
        return Response(UserSerializer(user).data)
    except User.DoesNotExist:
        return Response(status=404)

@api_view(['POST'])
@permission_classes([IsAdminRole])
def admin_user_approve(request, pk):
    try:
        user = User.objects.get(pk=pk)
        user.is_approved = True
        user.status = 'active'
        user.save()
        return Response(UserSerializer(user).data)
    except User.DoesNotExist:
        return Response(status=404)

@api_view(['POST'])
@permission_classes([IsAdminRole])
def admin_notification_send(request):
    serializer = NotificationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
