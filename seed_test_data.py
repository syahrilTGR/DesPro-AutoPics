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

# ── Data Pengguna & Kartu (Tambahkan kartu baru di sini) ──
users_data = [
    {"name": "Awang",   "balance": 50000, "uid_raw": "A9:36:97:11"},
    {"name": "Syahril", "balance": 50000, "uid_raw": "19:01:92:11"},
    {"name": "Refi",    "balance": 50000, "uid_raw": "09:D9:7D:11"},
    {"name": "Noval",   "balance": 50000, "uid_raw": "29:90:03:07"},
    # CONTOH PENAMBAHAN:
    # {"name": "Tamu 1",  "balance": 10000, "uid_raw": "AA:BB:CC:DD"},
]

def seed_database():
    print("Memulai proses Inject Data ke Supabase...")
    
    for user in users_data:
        print(f"\n--- Memproses Kartu: {user['name']} ---")
        clean_uid = user["uid_raw"].replace(":", "").upper()
        
        # 1. Cek apakah kartu sudah terdaftar (menghindari duplikat)
        cek_rfid = requests.get(f"{SUPABASE_URL}/rest/v1/rfid_cards?uid=eq.{clean_uid}", headers=HEADERS)
        if cek_rfid.status_code == 200 and len(cek_rfid.json()) > 0:
            print(f"⏩ SKIP: Kartu {clean_uid} milik {user['name']} sudah terdaftar sebelumnya.")
            continue
            
        # 2. Daftarkan RFID
        rfid_payload = {
            "uid": clean_uid,
            "card_name": f"Kartu {user['name']}",
        }
        resp_rfid = requests.post(f"{SUPABASE_URL}/rest/v1/rfid_cards", json=rfid_payload, headers=HEADERS)
        
        if resp_rfid.status_code in [200, 201]:
            print(f"✅ Berhasil mendaftarkan kartu RFID: {clean_uid} untuk {user['name']}")
        else:
            print(f"❌ Gagal mendaftarkan kartu RFID {clean_uid}: {resp_rfid.text}")

    print("\n🎉 Proses Inject selesai. Kartu baru siap untuk di-bind melalui aplikasi!")

if __name__ == "__main__":
    seed_database()
