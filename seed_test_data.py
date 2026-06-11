import requests
import json
import urllib3
urllib3.disable_warnings()

# ── Konfigurasi Supabase ──
SUPABASE_URL = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ── Data Pengguna & Kartu ──
users_data = [
    {"name": "Awang", "balance": 50000, "uid_raw": "A9:36:97:11", "vehicle": "Motor"},
    {"name": "Syahril", "balance": 50000, "uid_raw": "19:01:92:11", "vehicle": "Mobil"},
    {"name": "Refi", "balance": 50000, "uid_raw": "09:D9:7D:11", "vehicle": "Motor"},
    {"name": "Noval", "balance": 50000, "uid_raw": "29:90:03:07", "vehicle": "Mobil"},
]

def seed_database():
    print("Memulai proses Seeding Data ke Supabase...")
    
    for user in users_data:
        print(f"\n--- Memproses User: {user['name']} ---")
        
        user_payload = {
            "name": user["name"],
            "balance": user["balance"]
        }
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/users", json=user_payload, headers=HEADERS)
        
        if resp.status_code in [200, 201]:
            created_user = resp.json()[0]
            user_id = created_user["id"]
            print(f"Berhasil membuat user: {user['name']} (ID: {user_id})")
            
            clean_uid = user["uid_raw"].replace(":", "").upper()
            
            rfid_payload = {
                "uid": clean_uid,
                "user_id": user_id,
                "card_name": f"Kartu {user['name']}",
                "vehicle_type": user["vehicle"],
            }
            resp_rfid = requests.post(f"{SUPABASE_URL}/rest/v1/rfid_cards", json=rfid_payload, headers=HEADERS)
            
            if resp_rfid.status_code in [200, 201]:
                print(f"Berhasil mendaftarkan kartu RFID: {clean_uid} untuk {user['name']}")
            else:
                print(f"Gagal mendaftarkan kartu RFID {clean_uid}: {resp_rfid.text}")
                
        else:
            print(f"Gagal membuat user {user['name']}: {resp.text}")

    print("\nProses seeding selesai. Silakan cek tabel 'users' dan 'rfid_cards' di Supabase!")

if __name__ == "__main__":
    seed_database()
