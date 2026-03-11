#!/bin/bash

# Migratsiyalarni amalga oshirish
echo "Running migrations..."
python manage.py migrate --noinput

# Serverni ishga tushirish
echo "Starting Daphne server..."
daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application
