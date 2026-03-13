import os
import django
import random

# Django muhitini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

NAMES = ['Ali', 'Vali', 'Gani', 'Salim', 'Karim', 'Jasur', 'Bekzod', 'Sardor', 'Doston', 'Aziz', 'Hasan', 'Husan', 'Botir', 'Rustam', 'Olim', 'Farhod', 'Zafar', 'Umid', 'Murod', 'Oybek']
SURNAMES = ['Aliyev', 'Valiyev', 'Ganiyev', 'Salimov', 'Karimov', 'Jasurov', 'Bekzodov', 'Sardorov', 'Dostonov', 'Azizov', 'Hasanov', 'Husanov', 'Botirov', 'Rustamov', 'Olimov', 'Farhodov', 'Zafarov', 'Umidov', 'Murodov', 'Oybekov']
FIELDS = ['Frontend Developer', 'Backend Developer', 'UX/UI Designer', 'Data Scientist', 'Project Manager', 'DevOps Engineer']

def create_fake_students(count=40):
    print(f"Boshlandi: {count} ta fake student yaratilmoqda...")
    
    created_count = 0
    for i in range(count):
        first_name = random.choice(NAMES)
        last_name = random.choice(SURNAMES)
        username = f"{first_name.lower()}_{last_name.lower()}_{random.randint(1000, 9999)}"
        
        while User.objects.filter(username=username).exists():
            username = f"{first_name.lower()}_{last_name.lower()}_{random.randint(1000, 9999)}"
            
        skills = ["Python", "JavaScript", "HTML/CSS"] if random.choice([True, False]) else ["React", "Django"]
        
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            name=f"{first_name} {last_name}",
            role='student',
            status='active',
            is_approved=True,
            field=random.choice(FIELDS),
            long_bio=f"Men {first_name} {last_name}. Dasturlash bilan qiziqishim juda yuqori va doimo o'z ustimda ishlashga, yangi bilimlarni o'rganishga tayyorman.",
            field_description=f"O'z sohamda malakali va kuchli mutaxassis bo'lishni, tajribali jamoalarda ishlashni maqsad qilganman.",
            motivation_quote="Hech qachon taslim bo'lma, eng zo'ri bo'l!",
            skills=skills
        )
        # Barcha fake o'quvchilarga bir xil parol beramiz
        user.set_password("student123")
        try:
            user.save()
            created_count += 1
            print(f"{created_count}. {username} muvaffaqiyatli yaratildi (Parol: student123).")
        except Exception as e:
            print(f"Xatolik: {username} yaratishda muammo yuzaga keldi - {e}")
            
    print(f"\nJarayon muvaffaqiyatli yakunlandi! Jami {created_count} ta o'quvchi qo'shildi.")

if __name__ == '__main__':
    create_fake_students(40)
