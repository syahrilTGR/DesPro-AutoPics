import requests
import json
import urllib3
import sys
import io

# Force UTF-8 for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

urllib3.disable_warnings()

SUPABASE_URL = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

print("\n--- RIWAYAT PARKIR TERBARU ---")
resp = requests.get(f"{SUPABASE_URL}/rest/v1/parking_history?order=time_in.desc&limit=1", headers=HEADERS)
if resp.status_code == 200:
    data = resp.json()
    if data:
        print(json.dumps(data[0], indent=2))
    else:
        print("Kosong.")

print("\n--- SALDO USER (UID 19019211) ---")
resp_user = requests.get(f"{SUPABASE_URL}/rest/v1/users?select=name,balance,rfid_cards(uid)&rfid_cards.uid=eq.19019211", headers=HEADERS)
if resp_user.status_code == 200:
    for u in resp_user.json():
        if u.get('rfid_cards'):
            print(f"Nama: {u['name']} | Saldo Saat Ini: Rp {u['balance']}")
