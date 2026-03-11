import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.serializers import UserSerializer
from api.models import User

user = User.objects.last()
if not user:
    user = User.objects.create(username="testuser")

data = {
    "socialLinks": [
        {
            "iconUrl": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
            "linkUrl": "https://example.com"
        }
    ]
}

ser = UserSerializer(user, data=data, partial=True)
if ser.is_valid():
    ser.save()
    print("SAVED:", ser.data['socialLinks'])
else:
    print("ERRORS:", ser.errors)
