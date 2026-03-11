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

# Entrypoint skriptini ko'chirish va huquq berish
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Portni ochish
EXPOSE 8000

# Entrypoint skriptini ishga tushirish
ENTRYPOINT ["/app/entrypoint.sh"]

