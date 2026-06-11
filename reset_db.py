import requests
import urllib3
urllib3.disable_warnings()

# ── Konfigurasi Supabase ──
SUPABASE_URL = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

def reset_db():
    print("[1/2] Menghapus seluruh riwayat parkir...")
    resp_del = requests.delete(f"{SUPABASE_URL}/rest/v1/parking_history?id=not.is.null", headers=HEADERS)
    if resp_del.status_code in [200, 204]:
        print("OK: Riwayat parkir berhasil dibersihkan!")
    else:
        print("FAIL: Gagal menghapus riwayat:", resp_del.text)

    print("[2/2] Mereset saldo seluruh User ke Rp 50.000...")
    headers_patch = HEADERS.copy()
    headers_patch["Content-Type"] = "application/json"
    
    resp_patch = requests.patch(f"{SUPABASE_URL}/rest/v1/users?id=not.is.null", json={"balance": 50000}, headers=headers_patch)
    if resp_patch.status_code in [200, 204]:
        print("OK: Saldo berhasil di-reset!")
    else:
        print("FAIL: Gagal mereset saldo:", resp_patch.text)

if __name__ == "__main__":
    reset_db()
