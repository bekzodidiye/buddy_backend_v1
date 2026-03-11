# Python imayji
FROM python:3.12-slim

# Muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Ishchi katalogni belgilash
WORKDIR /app

# Kutubxonalarni o'rnatish uchun zarur bo'lgan tizim paketlari
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Talablarni ko'chirish va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini ko'chirish
COPY . .

# Statik fayllarni yig'ish
RUN python manage.py collectstatic --noinput

# Portni ochish
EXPOSE 8000

# Server va Keep-alive skriptini ishga tushirish
# '&' belgisi keep_alive.py ni fonda (background) ishga tushiradi
CMD ["sh", "-c", "python keep_alive.py & daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]
