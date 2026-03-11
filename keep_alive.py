import os
import time
import requests

# Render platformasida RENDER_EXTERNAL_URL muhit o'zgaruvchisi avtomat mavjud bo'lishi mumkin, 
# bo'lmasa uni o'zingiz qo'lda o'rnatishingiz kerak.
url = os.getenv("RENDER_EXTERNAL_URL")

def ping_self():
    if not url:
        print("KEEP_ALIVE: RENDER_EXTERNAL_URL o'zgaruvchisi topilmadi. Skript to'xtatildi.")
        return

    print(f"KEEP_ALIVE: {url} manziliga ping yuborish boshlandi...")
    
    while True:
        try:
            response = requests.get(url)
            print(f"KEEP_ALIVE: Ping yuborildi. Status: {response.status_code}")
        except Exception as e:
            print(f"KEEP_ALIVE: Xatolik yuz berdi: {e}")
        
        # 14 minut (840 soniya) kutish
        time.sleep(840)

if __name__ == "__main__":
    # Server to'liq yuklanishi uchun 30 soniya kutamiz
    time.sleep(30)
    ping_self()
