import sys
import time
import requests

# Kredensial diambil dari konfigurasi AutoPics
SUPABASE_URL = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def clear_screen():
    print("\033[H\033[J", end="")

def main():
    while True:
        clear_screen()
        print("========================================")
        print("    AUTOPICS - ADMIN KIOSK (TOP-UP)     ")
        print("========================================")
        
        uid = input("\nMasukkan UID Kartu (atau ketik 'exit' untuk keluar): ").strip().upper()
        if uid == 'EXIT':
            break
        if not uid:
            continue
            
        print("\nMencari data kartu...")
        # Get card and related user
        url_rfid = f"{SUPABASE_URL}/rest/v1/rfid_cards?uid=eq.{uid}&select=user_id,users(id,name,balance)"
        try:
            res = requests.get(url_rfid, headers=headers)
            res.raise_for_status()
            data = res.json()
            
            if not data:
                print(f"❌ ERROR: Kartu dengan UID '{uid}' tidak terdaftar!")
                time.sleep(2)
                continue
                
            card_data = data[0]
            user_data = card_data.get('users')
            
            if not user_data:
                print(f"❌ ERROR: Kartu terdaftar tapi tidak terhubung ke User (Data Korup)!")
                time.sleep(2)
                continue
                
            user_id = user_data['id']
            name = user_data.get('name', 'Unknown')
            current_balance = user_data.get('balance', 0)
            
            print("----------------------------------------")
            print(f" Nama Pemilik : {name}")
            print(f" Saldo Saat Ini: Rp {current_balance:,}")
            print("----------------------------------------")
            
            # Meminta input nominal
            amount_str = input("Masukkan nominal top-up (Rp): ")
            if not amount_str.isdigit():
                print("❌ ERROR: Nominal harus berupa angka!")
                time.sleep(2)
                continue
                
            amount = int(amount_str)
            if amount <= 0:
                print("❌ ERROR: Nominal harus lebih besar dari 0!")
                time.sleep(2)
                continue
                
            new_balance = current_balance + amount
            confirm = input(f"\nTop-up Rp {amount:,} untuk {name}? (Y/N): ").strip().upper()
            
            if confirm == 'Y':
                print("\nMemproses transaksi...")
                # 1. Update Saldo
                url_user = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}"
                patch_data = {"balance": new_balance}
                
                res_patch = requests.patch(url_user, headers=headers, json=patch_data)
                res_patch.raise_for_status()
                
                # 2. Catat Riwayat Transaksi
                url_trans = f"{SUPABASE_URL}/rest/v1/transactions"
                post_data = {
                    "user_id": user_id,
                    "amount": amount,
                    "transaction_type": "TOPUP"
                }
                res_post = requests.post(url_trans, headers=headers, json=post_data)
                
                if res_post.status_code in [200, 201]:
                    print(f"✅ BERHASIL! Saldo {name} sekarang: Rp {new_balance:,}")
                else:
                    print(f"⚠️ PERINGATAN: Saldo bertambah, tapi gagal mencatat riwayat transaksi. Code: {res_post.status_code}")
                    print(res_post.text)
                    
            else:
                print("Dibatalkan.")
                
        except Exception as e:
            print(f"❌ Terjadi kesalahan jaringan/sistem: {e}")
            
        input("\nTekan Enter untuk melanjutkan...")

if __name__ == "__main__":
    main()
