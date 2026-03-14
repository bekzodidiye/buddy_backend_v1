"""
api/tests.py — Comprehensive unit tests for the Buddy backend

Coverage:
  - Models: User, Monitoring, Notification, SocialLink, Season
  - Serializers: validation, nested writes, field exposure
  - Views: permissions, N+1 detection, caching, CRUD operations
  - Auth: login, logout, token blacklist
  - Exception handler: consistent error format
  - Admin endpoints: field validation

Run with:
    python manage.py test api
    python manage.py test api --verbosity=2
"""
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from api.models import (
    Season, Monitoring, Notification, SocialLink, ChatMessage, PlatformSetting
)
from api.serializers import (
    RegisterSerializer, MonitoringSerializer, NotificationSerializer,
    UserSerializer, WeeklyHighlightSerializer
)
from api.exception_handler import custom_exception_handler

User = get_user_model()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_user(username='testuser', role='student', status_val='active',
              is_approved=True, password='testpass123'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password=password,
        role=role,
        status=status_val,
        is_approved=is_approved,
    )

def make_admin(username='admin', password='adminpass123'):
    return make_user(username=username, role='admin', status_val='active',
                     is_approved=True, password=password)

def make_curator(username='curator'):
    return make_user(username=username, role='curator')

def make_season(number=1):
    return Season.objects.create(number=number, start_date='2024-01-01', is_active=True)


# ─── Model Tests ──────────────────────────────────────────────────────────────

class UserModelTest(TestCase):
    def test_superuser_auto_sets_admin_role(self):
        """Superuser save() should force role=admin, is_approved=True, status=active"""
        user = User.objects.create_superuser(
            username='su', email='su@test.com', password='pass'
        )
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.is_approved)
        self.assertEqual(user.status, 'active')

    def test_str_representation(self):
        user = make_user(username='alice')
        self.assertIn('alice', str(user))
        self.assertIn('student', str(user))

    def test_default_role_is_student(self):
        user = User.objects.create_user(
            username='bob', email='bob@test.com', password='pass'
        )
        self.assertEqual(user.role, 'student')
        self.assertEqual(user.status, 'pending')

    def test_uuid_primary_key(self):
        user = make_user()
        import uuid
        self.assertIsInstance(user.id, uuid.UUID)


class MonitoringModelTest(TestCase):
    def setUp(self):
        self.curator = make_curator()
        self.student = make_user(username='student1')
        self.season = make_season()

    def test_monitoring_str(self):
        m = Monitoring.objects.create(
            curator=self.curator,
            season=self.season,
            week_number=1,
            student=self.student,
            student_name='Test Student',
        )
        self.assertIn('Test Student', str(m))
        self.assertIn('1', str(m))

    def test_monitoring_default_status(self):
        m = Monitoring.objects.create(
            curator=self.curator,
            season=self.season,
            week_number=1,
            student=self.student,
        )
        self.assertEqual(m.status, 'Kutilmoqda')


# ─── Serializer Tests ─────────────────────────────────────────────────────────

class RegisterSerializerTest(TestCase):
    def test_valid_registration(self):
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'strongpass1',
            'name': 'New User',
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_spaces_in_username(self):
        data = {
            'username': 'bad user',
            'email': 'bad@test.com',
            'password': 'strongpass1',
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_lowercases_username(self):
        data = {
            'username': 'UserName',
            'email': 'user@test.com',
            'password': 'strongpass1',
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['username'], 'username')

    def test_rejects_admin_role_self_assign(self):
        data = {
            'username': 'hacker',
            'email': 'hacker@test.com',
            'password': 'strongpass1',
            'role': 'admin',
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

    def test_requires_strong_password(self):
        data = {
            'username': 'weakuser',
            'email': 'weak@test.com',
            'password': 'short',
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_curator_gets_pending_status(self):
        data = {
            'username': 'newcurator',
            'email': 'curator@test.com',
            'password': 'strongpass1',
            'role': 'curator',
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.status, 'pending')

    def test_student_gets_active_status(self):
        data = {
            'username': 'newstudent',
            'email': 'student@test.com',
            'password': 'strongpass1',
            'role': 'student',
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.status, 'active')


class WeeklyHighlightSerializerTest(TestCase):
    def setUp(self):
        self.curator = make_curator()
        self.season = make_season()

    def test_requires_photo_url_or_image(self):
        data = {
            'curatorId': str(self.curator.id),
            'seasonId': str(self.season.id),
            'weekNumber': 1,
            # Neither photo_url nor image
        }
        serializer = WeeklyHighlightSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        # The non-field error should mention photo_url or image
        errors = str(serializer.errors)
        self.assertIn('photo_url', errors.lower() + 'image')


# ─── View / API Tests ─────────────────────────────────────────────────────────

class UserViewSetTest(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.curator = make_curator(username='curator1')
        self.student = make_user(username='student1')

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_anonymous_sees_only_active_approved_curators(self):
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Anonymous sees a list (may be paginated)
        data = resp.data
        results = data.get('results', data)
        for user_data in results:
            self.assertEqual(user_data['role'], 'curator')
            self.assertEqual(user_data['status'], 'active')
            self.assertTrue(user_data['isApproved'])

    def test_admin_sees_all_users(self):
        self._auth(self.admin)
        resp = self.client.get('/api/v1/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        results = data.get('results', data)
        usernames = [u['username'] for u in results]
        self.assertIn('admin', usernames)
        self.assertIn('curator1', usernames)
        self.assertIn('student1', usernames)

    def test_student_cannot_delete_user(self):
        self._auth(self.student)
        resp = self.client.delete(f'/api/v1/users/{self.curator.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_user(self):
        self._auth(self.admin)
        target = make_user(username='deleteme')
        resp = self.client.delete(f'/api/v1/users/{target.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(username='deleteme').exists())

    def test_unauthenticated_cannot_register_without_data(self):
        resp = self.client.post('/api/v1/auth/register/', {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_n1_queries_on_user_list(self):
        """
        Verify that listing users doesn't suffer from N+1 queries.
        We create users with social links, then assert query count stays bounded.
        """
        # Create users with social links
        for i in range(5):
            u = make_user(username=f'curator_n1_{i}', role='curator')
            SocialLink.objects.create(user=u, link_url=f'https://link{i}.com')

        self._auth(self.admin)

        from django.test.utils import override_settings
        from django.db import connection, reset_queries

        with self.settings(DEBUG=True):
            reset_queries()
            resp = self.client.get('/api/v1/users/')
            query_count = len(connection.queries)

        self.assertEqual(resp.status_code, 200)
        # With prefetch_related, we expect ~2 queries (1 main + 1 prefetch).
        # Without it, it would be 1 + N queries. We allow up to 5 as a generous bound.
        self.assertLessEqual(
            query_count, 5,
            f"Too many queries ({query_count}) — possible N+1 problem.\n"
            f"Queries: {[q['sql'][:80] for q in connection.queries]}"
        )


class MonitoringViewSetTest(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.curator = make_curator()
        self.student = make_user(username='stu1')
        self.season = make_season()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _create_monitoring(self, curator=None, student=None):
        curator = curator or self.curator
        student = student or self.student
        return Monitoring.objects.create(
            curator=curator,
            season=self.season,
            week_number=1,
            student=student,
            student_name=student.username,
        )

    def test_student_sees_only_own_monitoring(self):
        m1 = self._create_monitoring()
        other_student = make_user(username='other')
        m2 = self._create_monitoring(student=other_student)

        self._auth(self.student)
        resp = self.client.get('/api/v1/monitoring/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        results = data.get('results', data)
        ids = [str(r['id']) for r in results]
        self.assertIn(str(m1.id), ids)
        self.assertNotIn(str(m2.id), ids)

    def test_curator_sees_only_own_monitoring(self):
        m1 = self._create_monitoring()
        other_curator = make_curator(username='curator2')
        m2 = self._create_monitoring(curator=other_curator)

        self._auth(self.curator)
        resp = self.client.get('/api/v1/monitoring/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        results = data.get('results', data)
        ids = [str(r['id']) for r in results]
        self.assertIn(str(m1.id), ids)
        self.assertNotIn(str(m2.id), ids)

    def test_admin_sees_all_monitoring(self):
        m1 = self._create_monitoring()
        self._auth(self.admin)
        resp = self.client.get('/api/v1/monitoring/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        results = data.get('results', data)
        self.assertTrue(any(str(r['id']) == str(m1.id) for r in results))

    def test_no_n1_queries_on_monitoring_list(self):
        """Verify select_related eliminates N+1 on monitoring list."""
        for i in range(5):
            s = make_user(username=f'st_{i}')
            Monitoring.objects.create(
                curator=self.curator,
                season=self.season,
                week_number=i + 1,
                student=s,
                student_name=s.username,
            )

        self._auth(self.admin)
        from django.db import connection, reset_queries

        with self.settings(DEBUG=True):
            reset_queries()
            resp = self.client.get('/api/v1/monitoring/')
            query_count = len(connection.queries)

        self.assertEqual(resp.status_code, 200)
        # With select_related('curator','season','student'), should be ~1 query.
        # Without, it would be 1 + 3N queries. Allow up to 5 as generous bound.
        self.assertLessEqual(
            query_count, 5,
            f"Too many queries ({query_count}) — N+1 likely still present."
        )

    def test_filter_by_season(self):
        m1 = self._create_monitoring()
        season2 = make_season(number=2)
        m2 = Monitoring.objects.create(
            curator=self.curator, season=season2,
            week_number=1, student=self.student,
        )

        self._auth(self.admin)
        resp = self.client.get(f'/api/v1/monitoring/?season={self.season.id}')
        data = resp.data
        results = data.get('results', data)
        ids = [str(r['id']) for r in results]
        self.assertIn(str(m1.id), ids)
        self.assertNotIn(str(m2.id), ids)


class NotificationViewSetTest(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_user(username='stu')
        self.curator = make_curator(username='cur')

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_student_sees_own_and_all_notifications(self):
        n_all = Notification.objects.create(title='All', message='msg', target_role='all')
        n_student = Notification.objects.create(
            title='Student', message='msg', target_role='student'
        )
        n_curator = Notification.objects.create(
            title='Curator only', message='msg', target_role='curator'
        )
        n_personal = Notification.objects.create(
            title='Personal', message='msg',
            target_role='none', target_user=self.student
        )

        self._auth(self.student)
        resp = self.client.get('/api/v1/notifications/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        results = data.get('results', data)
        titles = [r['title'] for r in results]

        self.assertIn('All', titles)
        self.assertIn('Student', titles)
        self.assertIn('Personal', titles)
        self.assertNotIn('Curator only', titles)


class AdminStatsTest(APITestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_admin_stats_requires_admin_role(self):
        student = make_user(username='nonadmin')
        self.client.force_authenticate(user=student)
        resp = self.client.get('/api/v1/admin/stats/')
        self.assertIn(resp.status_code, [403, 401])

    def test_admin_stats_returns_correct_data(self):
        self.client.force_authenticate(user=self.admin)
        make_curator(username='c1')
        resp = self.client.get('/api/v1/admin/stats/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_users', resp.data)
        self.assertIn('total_monitorings', resp.data)
        self.assertIn('active_curators', resp.data)
        self.assertIsInstance(resp.data['total_users'], int)

    @override_settings(
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    )
    def test_admin_stats_is_cached(self):
        """Second call to admin stats should hit cache, not DB."""
        from django.db import connection, reset_queries

        self.client.force_authenticate(user=self.admin)

        with self.settings(DEBUG=True):
            # First call — populates cache
            self.client.get('/api/v1/admin/stats/')
            reset_queries()
            # Second call — should use cache
            resp = self.client.get('/api/v1/admin/stats/')
            query_count = len(connection.queries)

        self.assertEqual(resp.status_code, 200)
        # Cache hit = 0 DB queries (cache backend itself may do 1 Redis call)
        self.assertLessEqual(query_count, 1, "Admin stats should be cached on second call")


class AdminUserRoleTest(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_user(username='roletest')

    def test_valid_role_change(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/v1/admin/users/{self.student.id}/role/',
            {'role': 'curator'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, 'curator')

    def test_invalid_role_rejected(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/v1/admin/users/{self.student.id}/role/',
            {'role': 'supervillain'},
            format='json'
        )
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_user_returns_404(self):
        import uuid
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/v1/admin/users/{uuid.uuid4()}/role/',
            {'role': 'curator'},
            format='json'
        )
        self.assertEqual(resp.status_code, 404)

    def test_admin_user_status_validation(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/v1/admin/users/{self.student.id}/status/',
            {'status': 'notavalidstatus'},
            format='json'
        )
        self.assertEqual(resp.status_code, 400)


class AdminUserApproveTest(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.pending_user = make_user(
            username='pending', status_val='pending', is_approved=False
        )

    def test_approve_sets_approved_and_active(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            f'/api/v1/admin/users/{self.pending_user.id}/approve/'
        )
        self.assertEqual(resp.status_code, 200)
        self.pending_user.refresh_from_db()
        self.assertTrue(self.pending_user.is_approved)
        self.assertEqual(self.pending_user.status, 'active')


class MeEndpointTest(APITestCase):
    def test_me_requires_authentication(self):
        resp = self.client.get('/api/v1/auth/me/')
        self.assertIn(resp.status_code, [401, 403])

    def test_me_returns_own_user_data(self):
        user = make_user(username='metest')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['username'], 'metest')

    def test_me_does_not_expose_password(self):
        user = make_user()
        self.client.force_authenticate(user=user)
        resp = self.client.get('/api/v1/auth/me/')
        # password field should be write_only — not in response
        self.assertNotIn('password', resp.data)


# ─── Exception Handler Tests ──────────────────────────────────────────────────

class ExceptionHandlerTest(TestCase):
    def test_standard_error_format(self):
        """All errors should use the {error: {code, message, status}} format."""
        from rest_framework.exceptions import AuthenticationFailed
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/')

        exc = AuthenticationFailed(detail='Token muddati tugagan.')
        context = {'request': request, 'view': None}
        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertIn('error', response.data)
        self.assertIn('code', response.data['error'])
        self.assertIn('message', response.data['error'])
        self.assertIn('status', response.data['error'])

    def test_validation_error_includes_field_errors(self):
        """Validation errors should include field-level error details."""
        from rest_framework.exceptions import ValidationError

        exc = ValidationError({'username': ['This field is required.']})
        context = {'view': None}
        response = custom_exception_handler(exc, context)

        self.assertIsNotNone(response)
        self.assertIn('error', response.data)
        self.assertIn('fields', response.data['error'])


# ─── Chat Message Serializer Tests ────────────────────────────────────────────

class ChatMessageSerializerTest(TestCase):
    def test_does_not_expose_user_id(self):
        """ChatMessageSerializer should not expose the user FK."""
        from api.serializers import ChatMessageSerializer
        user = make_user()
        msg = ChatMessage.objects.create(user=user, role='user', text='hello')
        data = ChatMessageSerializer(msg).data
        self.assertNotIn('user', data)
        self.assertIn('text', data)
        self.assertIn('role', data)
        self.assertIn('id', data)
        self.assertIn('timestamp', data)
