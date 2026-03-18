from __future__ import annotations

import base64
import uuid
import logging
from typing import Any

from django.core.files.base import ContentFile
from rest_framework import serializers

logger = logging.getLogger(__name__)

class Base64ImageField(serializers.Field):
    """
    Custom field that handles:
    1. Base64 strings (as new uploads)
    2. File objects (from multipart forms)
    3. Existing URLs (as 'no data change')
    """
    def to_internal_value(self, data: Any) -> Any:
        # Bo'sh ma'lumotlar
        if data in (None, '', [], {}, 'null', 'undefined'):
            return None

        # Agar bu allaqachon fayl bo'lsa (masalan, Admin paneldan yuklanganda)
        if hasattr(data, 'size') or hasattr(data, 'read'):
            return data

        # Agar bu string bo'lsa
        if isinstance(data, str):
            # Base64 rasm yuklash
            if data.startswith('data:image'):
                try:
                    fmt, imgstr = data.split(';base64,')
                    ext = fmt.split('/')[-1].split('+')[0]
                    content = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                    return content
                except Exception as exc:
                    logger.error("Base64 decoding failed: %s", exc)
                    raise serializers.ValidationError("Rasm formati noto'g'ri.")

            # Agar bu URL bo'lsa (Ya'ni rasm o'zgarmagan)
            # URLni modelga saqlashga urinmasligi uchun None qaytaramiz
            # UserSerializer.update buni handled qilishi kerak
            if data.startswith('http') or '/media/' in data or 'ui-avatars.com' in data:
                return None

        # Boshqa holatlarda ham rasm o'zgarmagan deb hisoblaymiz (masalan, noto'g'ri string kelsa)
        return None

    def to_representation(self, value: Any) -> Any:
        if not value:
            return None
        
        # Nisbiy URL (masalan, /media/avatars/...)
        url = value.url if hasattr(value, 'url') else str(value)
        
        # Agarda serializer context-ida 'request' bo'lsa, to'liq URL (Absolute) yasaymiz
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(url)
            
        return url
