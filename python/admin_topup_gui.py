import customtkinter as ctk
import requests
import threading

# Kredensial diambil dari konfigurasi AutoPics
SUPABASE_URL = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AutoPics - Admin Kiosk (Top-Up)")
        self.geometry("600x650")
        
        self.current_user_id = None
        self.current_balance = 0
        self.current_name = ""

        # Title
        self.title_label = ctk.CTkLabel(self, text="AUTOPICS KIOSK TOP-UP", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=20)

        # Frame for UID Search
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(pady=10, padx=20, fill="x")
        
        self.uid_label = ctk.CTkLabel(self.search_frame, text="Masukkan UID Kartu:", font=ctk.CTkFont(size=14))
        self.uid_label.pack(pady=(10,0))
        
        self.uid_entry = ctk.CTkComboBox(self.search_frame, values=["Memuat data..."], width=300, font=ctk.CTkFont(size=16))
        self.uid_entry.pack(pady=10)
        
        # Mulai memuat data pengguna di latar belakang
        threading.Thread(target=self.load_users_data, daemon=True).start()
        
        self.search_btn = ctk.CTkButton(self.search_frame, text="Cari Data", command=self.search_card)
        self.search_btn.pack(pady=(0, 10))

        # Frame for User Info
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(pady=10, padx=20, fill="x")
        
        self.name_label = ctk.CTkLabel(self.info_frame, text="Nama Pemilik: -", font=ctk.CTkFont(size=16))
        self.name_label.pack(pady=(10, 5))
        
        self.balance_label = ctk.CTkLabel(self.info_frame, text="Saldo Saat Ini: Rp 0", font=ctk.CTkFont(size=16, weight="bold"))
        self.balance_label.pack(pady=(5, 10))

        # Frame for Transaction
        self.trans_frame = ctk.CTkFrame(self)
        self.trans_frame.pack(pady=10, padx=20, fill="x")
        
        self.amount_label = ctk.CTkLabel(self.trans_frame, text="Nominal Top-Up (Rp):", font=ctk.CTkFont(size=14))
        self.amount_label.pack(pady=(10, 0))
        
        self.amount_entry = ctk.CTkEntry(self.trans_frame, placeholder_text="Contoh: 50000", width=300, font=ctk.CTkFont(size=16))
        self.amount_entry.pack(pady=10)
        self.amount_entry.bind('<Return>', lambda event: self.process_topup())
        
        self.topup_btn = ctk.CTkButton(self.trans_frame, text="Top-Up Sekarang", fg_color="green", hover_color="darkgreen", font=ctk.CTkFont(size=16, weight="bold"), command=self.process_topup)
        self.topup_btn.pack(pady=(0, 10))

        # Log Area
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.pack(pady=10, padx=20, fill="both", expand=True)
        self.log_textbox.insert("0.0", "Siap digunakan...\n")
        self.log_textbox.configure(state="disabled")

        # Set focus to UID entry initially
        self.uid_entry.focus_set()

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def load_users_data(self):
        try:
            url_rfid = f"{SUPABASE_URL}/rest/v1/rfid_cards?select=uid,users(name)"
            res = requests.get(url_rfid, headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            
            combo_values = []
            for item in data:
                uid = item.get("uid", "")
                user_info = item.get("users")
                name = user_info.get("name", "Unknown") if user_info else "Unknown"
                combo_values.append(f"{uid} - {name}")
                
            if not combo_values:
                combo_values = ["Tidak ada data RFID"]
                
            self.after(0, self._update_combo, combo_values)
        except Exception as e:
            self.after(0, self.log, f"❌ Gagal memuat daftar RFID: {e}")
            self.after(0, self._update_combo, ["Gagal memuat data"])

    def _update_combo(self, values):
        self.uid_entry.configure(values=values)
        self.uid_entry.set(values[0])

    def search_card(self):
        raw_val = self.uid_entry.get().strip()
        if not raw_val or raw_val in ["Memuat data...", "Tidak ada data RFID", "Gagal memuat data"]:
            self.log("❌ ERROR: Pilih UID yang valid.")
            return
            
        uid = raw_val.split(" - ")[0].strip().upper()
        if not uid:
            self.log("❌ ERROR: UID Kartu tidak boleh kosong.")
            return
            
        self.log(f"Mencari data untuk UID: {uid}...")
        self.search_btn.configure(state="disabled")
        # Run network request in a thread so GUI doesn't freeze
        threading.Thread(target=self._search_card_thread, args=(uid,), daemon=True).start()

    def _search_card_thread(self, uid):
        try:
            url_rfid = f"{SUPABASE_URL}/rest/v1/rfid_cards?uid=eq.{uid}&select=user_id,users(id,name,balance)"
            res = requests.get(url_rfid, headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            
            if not data:
                self.log(f"❌ ERROR: Kartu dengan UID '{uid}' tidak terdaftar!")
                self._reset_info()
            else:
                card_data = data[0]
                user_data = card_data.get('users')
                
                if not user_data:
                    self.log(f"❌ ERROR: Kartu terdaftar tapi tidak terhubung ke User (Data Korup)!")
                    self._reset_info()
                else:
                    self.current_user_id = user_data['id']
                    self.current_name = user_data.get('name', 'Unknown')
                    self.current_balance = user_data.get('balance', 0)
                    
                    self.name_label.configure(text=f"Nama Pemilik: {self.current_name}")
                    self.balance_label.configure(text=f"Saldo Saat Ini: Rp {self.current_balance:,}")
                    self.log(f"✅ Data ditemukan untuk {self.current_name}.")
                    
                    # Set focus to amount entry
                    self.amount_entry.focus_set()
                    
        except Exception as e:
            self.log(f"❌ Terjadi kesalahan jaringan: {e}")
            self._reset_info()
        finally:
            self.search_btn.configure(state="normal")

    def _reset_info(self):
        self.current_user_id = None
        self.current_name = ""
        self.current_balance = 0
        self.name_label.configure(text="Nama Pemilik: -")
        self.balance_label.configure(text="Saldo Saat Ini: Rp 0")

    def process_topup(self):
        if not self.current_user_id:
            self.log("❌ ERROR: Cari data kartu terlebih dahulu!")
            return
            
        amount_str = self.amount_entry.get().strip()
        if not amount_str.isdigit():
            self.log("❌ ERROR: Nominal harus berupa angka!")
            return
            
        amount = int(amount_str)
        if amount <= 0:
            self.log("❌ ERROR: Nominal harus lebih besar dari 0!")
            return

        self.log(f"Memproses top-up Rp {amount:,} untuk {self.current_name}...")
        self.topup_btn.configure(state="disabled")
        threading.Thread(target=self._process_topup_thread, args=(amount,), daemon=True).start()

    def _process_topup_thread(self, amount):
        try:
            new_balance = self.current_balance + amount
            
            # 1. Update Saldo
            url_user = f"{SUPABASE_URL}/rest/v1/users?id=eq.{self.current_user_id}"
            patch_data = {"balance": new_balance}
            res_patch = requests.patch(url_user, headers=HEADERS, json=patch_data)
            res_patch.raise_for_status()
            
            # 2. Catat Riwayat Transaksi
            url_trans = f"{SUPABASE_URL}/rest/v1/transactions"
            post_data = {
                "user_id": self.current_user_id,
                "amount": amount,
                "transaction_type": "TOPUP"
            }
            res_post = requests.post(url_trans, headers=HEADERS, json=post_data)
            
            if res_post.status_code in [200, 201]:
                self.log(f"✅ BERHASIL! Saldo {self.current_name} sekarang: Rp {new_balance:,}")
                
                # Reset UI for next topup
                self._reset_info()
                self.amount_entry.delete(0, 'end')
                # Optional: self.uid_entry.set("") # Biarkan tetap pada pilihan sebelumnya agar admin bisa ngecek ulang jika mau
                self.uid_entry.focus_set()
                self.log("Siap untuk kartu selanjutnya.")
            else:
                self.log(f"⚠️ PERINGATAN: Saldo bertambah, tapi gagal mencatat riwayat. Code: {res_post.status_code}")
                
        except Exception as e:
            self.log(f"❌ Terjadi kesalahan saat transaksi: {e}")
        finally:
            self.topup_btn.configure(state="normal")


if __name__ == "__main__":
    app = App()
    app.mainloop()
