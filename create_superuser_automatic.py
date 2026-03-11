import os
import django

# Django muhitini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin():
    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

    if not password:
        print("SUPERUSER: DJANGO_SUPERUSER_PASSWORD topilmadi. Superuser yaratilmaydi.")
        return

    if not User.objects.filter(username=username).exists():
        print(f"SUPERUSER: {username} foydalanuvchisi yaratilmoqda...")
        User.objects.create_superuser(username=username, email=email, password=password)
        print("SUPERUSER: Muvaffaqiyatli yaratildi!")
    else:
        print(f"SUPERUSER: {username} foydalanuvchisi allaqachon mavjud.")

if __name__ == "__main__":
    create_admin()
