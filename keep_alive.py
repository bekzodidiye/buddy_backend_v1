import os
import time
import requests

# Render external url, qo'lda yozib qo'yamiz (ishonchliroq)
url = os.getenv("RENDER_EXTERNAL_URL", "https://buddy-backend-v1-1.onrender.com")

def ping_self():
    ping_url = f"{url}/api/v1/users/"  # Oddiy public yoki 401 qaytaradigan API olsa ham URL ga hit bo'ladi
    print(f"KEEP_ALIVE: {ping_url} manziliga ping yuborish boshlandi...")
    
    while True:
        try:
            # 5 minut kutish (Render 15 minutdan so'ng uxlaydi, 5 minut kafolat)
            time.sleep(300)
            
            response = requests.get(ping_url, timeout=10)
            print(f"KEEP_ALIVE: Ping yuborildi. Status: {response.status_code}")
        except Exception as e:
            print(f"KEEP_ALIVE: Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    # Server to'liq yuklanishi uchun 30 soniya kutamiz
    time.sleep(30)
    ping_self()
