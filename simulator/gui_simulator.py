#!/usr/bin/env python3
"""
AutoPics GUI Simulator
Tampilan parkiran tampak atas — simulasi gate, sensor, tap kartu, dan slot parkir.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import threading
import time
import hashlib
from datetime import datetime, timezone
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from supabase_client import SB_URL, SB_KEY

# ─────────────────────────────────────────
# KONSTANTA & STYLE
# ─────────────────────────────────────────
BG        = "#0D1117"
CARD_BG   = "#161B22"
BORDER    = "#30363D"
GREEN     = "#3FB950"
RED       = "#F85149"
YELLOW    = "#E3B341"
BLUE      = "#58A6FF"
PURPLE    = "#BC8CFF"
TEXT      = "#E6EDF3"
TEXT_DIM  = "#8B949E"
MOTOR_COL = "#F78166"  # Oranye kemerahan untuk area motor
CAR_COL   = "#4DCBFC"  # Biru muda untuk area mobil

FONT_HEAD  = ("Inter", 14, "bold")
FONT_BODY  = ("Inter", 11)
FONT_SMALL = ("Inter", 9)
FONT_MONO  = ("Consolas", 10)

# Slot 1-7 = Mobil, 8-15 = Motor
CAR_SLOTS   = [str(i) for i in range(1, 8)]
MOTOR_SLOTS = [str(i) for i in range(8, 16)]
ALL_SLOTS   = CAR_SLOTS + MOTOR_SLOTS


# ─────────────────────────────────────────
# SUPABASE API HELPERS
# ─────────────────────────────────────────
def sb_headers(token=None):
    h = {
        "apikey": SB_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    h["Authorization"] = f"Bearer {token}" if token else f"Bearer {SB_KEY}"
    return h

def sb_get(endpoint, token=None):
    try:
        r = requests.get(f"{SB_URL}{endpoint}", headers=sb_headers(token), timeout=6)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        return []

def sb_post(endpoint, payload, token=None):
    try:
        r = requests.post(f"{SB_URL}{endpoint}", json=payload, headers=sb_headers(token), timeout=6)
        return r.status_code in [200, 201], r.text
    except Exception as e:
        return False, str(e)

def sb_patch(endpoint, payload, token=None):
    try:
        r = requests.patch(f"{SB_URL}{endpoint}", json=payload, headers=sb_headers(token), timeout=6)
        return r.status_code in [200, 204], r.text
    except Exception as e:
        return False, str(e)

def hash_password(plain: str, salt: str = "autopics_salt") -> str:
    """Hash password menggunakan SHA-256 (plain + salt), konsisten dengan Android app."""
    import hashlib
    input_str = plain + salt
    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()

def login_supabase(email, password):
    """Login ke tabel public.users (Custom Auth)."""
    hashed_pw = hash_password(password)
    try:
        r = requests.get(
            f"{SB_URL}/rest/v1/users?email=eq.{email}&password=eq.{hashed_pw}&select=id",
            headers={"apikey": SB_KEY},
            timeout=8
        )
        if r.status_code == 200 and len(r.json()) > 0:
            user_id = r.json()[0]["id"]
            # Kita tidak pakai token Supabase Auth, biarkan None
            return None, user_id
        return None, None
    except Exception as e:
        print("Login err:", e)
        return None, None


# ─────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────
class AutoPicsSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoPics Simulator — Parking Overhead View")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.geometry("1200x750")

        # State
        self.token      = None
        self.user_id    = None
        self.rfid_cards = []
        self.active_uid = None
        self.balance    = 0
        self.slot_status = {s: "EMPTY" for s in ALL_SLOTS}
        self.vehicles_inside = {}  # uid -> {vehicle_type, hist_id, slot}
        self.log_lines  = []

        self._build_login_screen()

    # ──────────────────────────────────────
    # LOGIN SCREEN
    # ──────────────────────────────────────
    def _build_login_screen(self):
        self._clear()
        frame = tk.Frame(self, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="🅿️  AutoPics Simulator", font=("Inter", 22, "bold"),
                 bg=BG, fg=TEXT).pack(pady=(0, 6))
        tk.Label(frame, text="Login dengan akun Supabase Anda untuk memulai simulasi.",
                 font=FONT_BODY, bg=BG, fg=TEXT_DIM).pack(pady=(0, 24))

        card = tk.Frame(frame, bg=CARD_BG, bd=0, relief="flat",
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(ipadx=30, ipady=24)

        tk.Label(card, text="Email", font=FONT_BODY, bg=CARD_BG, fg=TEXT_DIM).pack(anchor="w", padx=20, pady=(16,2))
        self.entry_email = tk.Entry(card, font=FONT_BODY, bg="#21262D", fg=TEXT,
                                    insertbackground=TEXT, bd=0, relief="flat", width=34)
        self.entry_email.insert(0, "syahril@test.com")
        self.entry_email.pack(padx=20, ipady=6)
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=20)

        tk.Label(card, text="Password", font=FONT_BODY, bg=CARD_BG, fg=TEXT_DIM).pack(anchor="w", padx=20, pady=(12,2))
        self.entry_pw = tk.Entry(card, font=FONT_BODY, bg="#21262D", fg=TEXT,
                                  insertbackground=TEXT, bd=0, relief="flat", width=34, show="●")
        self.entry_pw.pack(padx=20, ipady=6)
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=20)

        self.lbl_err = tk.Label(card, text="", font=FONT_SMALL, bg=CARD_BG, fg=RED)
        self.lbl_err.pack(pady=(8,0))

        btn = tk.Button(card, text="  Masuk  ", font=("Inter", 11, "bold"),
                        bg=GREEN, fg="#0D1117", bd=0, relief="flat", cursor="hand2",
                        activebackground="#2EA043", command=self._do_login)
        btn.pack(pady=16)
        self.bind("<Return>", lambda e: self._do_login())

    def _do_login(self):
        email = self.entry_email.get().strip()
        pw    = self.entry_pw.get()
        self.lbl_err.config(text="⏳ Menghubungkan ke database...")
        self.update()

        def _login_thread():
            token, uid = login_supabase(email, pw)
            if uid:  # Cek uid karena token kita kembalikan None (Custom Auth)
                self.token   = token
                self.user_id = uid
                self.after(0, self._after_login)
            else:
                self.after(0, lambda: self.lbl_err.config(text="❌ Email / password salah."))

        threading.Thread(target=_login_thread, daemon=True).start()

    def _after_login(self):
        """Fetch RFID cards milik user setelah login berhasil."""
        cards = sb_get(f"/rest/v1/rfid_cards?user_id=eq.{self.user_id}&select=uid,card_name,users(balance,name)", self.token)
        if not cards:
            messagebox.showerror("Error", "Tidak ada kartu RFID terdaftar untuk akun ini.")
            return
        self.rfid_cards = cards
        self.active_uid = cards[0]["uid"]
        user_data = cards[0].get("users", {})
        self.balance = int(user_data.get("balance", 0))
        self.user_name = user_data.get("name", "User")
        self._build_main_screen()

    # ──────────────────────────────────────
    # MAIN SCREEN
    # ──────────────────────────────────────
    def _build_main_screen(self):
        self._clear()
        self._fetch_slots_bg()

        # === HEADER ===
        hdr = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        hdr.pack(fill="x", padx=0, pady=0)
        tk.Label(hdr, text="🅿️ AutoPics Simulator", font=("Inter", 13, "bold"),
                 bg=CARD_BG, fg=TEXT).pack(side="left", padx=16, pady=10)

        info_right = tk.Frame(hdr, bg=CARD_BG)
        info_right.pack(side="right", padx=16, pady=8)
        self.lbl_user = tk.Label(info_right, text=f"👤 {self.user_name}", font=FONT_BODY, bg=CARD_BG, fg=TEXT)
        self.lbl_user.pack(side="left", padx=12)
        self.lbl_balance = tk.Label(info_right, text=f"💰 Rp {self.balance:,}", font=("Inter", 11, "bold"),
                                     bg=CARD_BG, fg=GREEN)
        self.lbl_balance.pack(side="left", padx=12)

        # === BODY ===
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # LEFT: Parking Area Canvas
        left = tk.Frame(body, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,4))
        tk.Label(left, text="DENAH AREA PARKIR", font=FONT_SMALL, bg=CARD_BG, fg=TEXT_DIM).pack(pady=(8,0))

        self.canvas = tk.Canvas(left, bg="#0A0F14", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda e: self._draw_parking_area())

        # RIGHT: Panel Control
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_control_panel(right)

    def _build_control_panel(self, parent):
        # ── KARTU RFID ──
        self._section(parent, "🪪 KARTU RFID AKTIF")
        self.cmb_card = ttk.Combobox(parent, state="readonly", font=FONT_BODY,
                                      values=[f"{c['card_name']} ({c['uid']})" for c in self.rfid_cards])
        self.cmb_card.current(0)
        self.cmb_card.pack(fill="x", padx=8, pady=(0, 8))
        self.cmb_card.bind("<<ComboboxSelected>>", self._on_card_change)

        # ── PILIH KENDARAAN ──
        self._section(parent, "🚗 PILIH KENDARAAN")
        self.vehicle_var = tk.StringVar(value="Mobil")
        veh_frame = tk.Frame(parent, bg=BG)
        veh_frame.pack(fill="x", padx=8, pady=(0,8))
        for v, icon in [("Mobil", "🚗"), ("Motor", "🏍️")]:
            tk.Radiobutton(veh_frame, text=f" {icon} {v}", variable=self.vehicle_var,
                           value=v, font=FONT_BODY, bg=BG, fg=TEXT, selectcolor=BG,
                           activebackground=BG, activeforeground=TEXT).pack(side="left", padx=8)

        # ── GATE MASUK ──
        self._section(parent, "🚦 SIMULASI GATE MASUK")
        btn_enter = tk.Button(parent, text="🟢  Tap Kartu — Gate MASUK", font=FONT_BODY,
                               bg="#1F6226", fg=TEXT, bd=0, relief="flat", cursor="hand2",
                               activebackground="#2EA043", command=self._simulate_entry)
        btn_enter.pack(fill="x", padx=8, pady=(0,6))

        # ── PILIH SLOT ──
        self._section(parent, "🅿️  PILIH SLOT UNTUK KENDARAAN")
        self.lbl_slot_info = tk.Label(parent, text="(Tap masuk dulu sebelum pilih slot)",
                                       font=FONT_SMALL, bg=BG, fg=TEXT_DIM)
        self.lbl_slot_info.pack(padx=8, anchor="w")
        self.cmb_slot = ttk.Combobox(parent, state="disabled", font=FONT_BODY)
        self.cmb_slot.pack(fill="x", padx=8, pady=(4, 4))
        btn_park = tk.Button(parent, text="📍  Tempatkan di Slot", font=FONT_BODY,
                              bg="#1A3A6B", fg=TEXT, bd=0, relief="flat", cursor="hand2",
                              activebackground="#1F6FEB", command=self._assign_slot)
        btn_park.pack(fill="x", padx=8, pady=(0, 8))

        # ── GATE KELUAR ──
        self._section(parent, "🚪 SIMULASI GATE KELUAR")
        btn_exit = tk.Button(parent, text="🔴  Tap Kartu — Gate KELUAR", font=FONT_BODY,
                              bg="#4A1111", fg=TEXT, bd=0, relief="flat", cursor="hand2",
                              activebackground="#B91C1C", command=self._simulate_exit)
        btn_exit.pack(fill="x", padx=8, pady=(0, 8))

        # ── REFRESH ──
        btn_ref = tk.Button(parent, text="🔄  Refresh Status Slot", font=FONT_SMALL,
                             bg=CARD_BG, fg=TEXT_DIM, bd=0, relief="flat", cursor="hand2",
                             command=self._fetch_slots_bg)
        btn_ref.pack(fill="x", padx=8, pady=(0, 4))

        # ── LOG ──
        self._section(parent, "📋 LOG AKTIVITAS")
        log_frame = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.log_text = tk.Text(log_frame, font=FONT_MONO, bg=CARD_BG, fg=TEXT,
                                 bd=0, relief="flat", state="disabled", wrap="word",
                                 height=10)
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _section(self, parent, title):
        tk.Label(parent, text=title, font=("Inter", 10, "bold"),
                 bg=BG, fg=TEXT_DIM).pack(anchor="w", padx=8, pady=(10, 2))

    # ──────────────────────────────────────
    # CANVAS: GAMBAR DENAH PARKIR
    # ──────────────────────────────────────
    def _draw_parking_area(self):
        self.canvas.delete("all")
        W = self.canvas.winfo_width()
        H = self.canvas.winfo_height()
        if W < 50 or H < 50:
            return

        # Lebar slot
        slot_w = min(68, (W - 40) // 8)
        slot_h = min(90, (H - 120) // 2)
        pad_x  = 20
        pad_y  = 20

        # ── AREA MOBIL (Baris atas, slot 1-7) ──
        self.canvas.create_text(pad_x, pad_y, text="AREA MOBIL  (Slot 1–7)", anchor="nw",
                                 fill=CAR_COL, font=("Inter", 9, "bold"))
        self.slot_rects = {}
        for i, sid in enumerate(CAR_SLOTS):
            x1 = pad_x + i * (slot_w + 4)
            y1 = pad_y + 18
            x2 = x1 + slot_w
            y2 = y1 + slot_h
            status = self.slot_status.get(sid, "EMPTY")
            fill_c = self._slot_color(sid, status)
            r = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_c, outline=BORDER, width=2)
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2 - 10,
                                     text=f"S{sid}", fill=TEXT, font=("Inter", 10, "bold"))
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2 + 8,
                                     text="FULL" if status == "FULL" else "OK",
                                     fill=TEXT, font=("Inter", 8))
            self.slot_rects[sid] = r
            self.canvas.tag_bind(r, "<Button-1>", lambda e, s=sid: self._click_slot(s))

        # ── AREA MOTOR (Baris bawah, slot 8-15) ──
        row2_y = pad_y + slot_h + 50
        self.canvas.create_text(pad_x, row2_y - 18, text="AREA MOTOR  (Slot 8–15)", anchor="nw",
                                  fill=MOTOR_COL, font=("Inter", 9, "bold"))
        for i, sid in enumerate(MOTOR_SLOTS):
            x1 = pad_x + i * (slot_w + 4)
            y1 = row2_y
            x2 = x1 + slot_w
            y2 = y1 + slot_h
            status = self.slot_status.get(sid, "EMPTY")
            fill_c = self._slot_color(sid, status)
            r = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_c, outline=BORDER, width=2)
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2 - 10,
                                     text=f"S{sid}", fill=TEXT, font=("Inter", 10, "bold"))
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2 + 8,
                                     text="FULL" if status == "FULL" else "OK",
                                     fill=TEXT, font=("Inter", 8))
            self.slot_rects[sid] = r
            self.canvas.tag_bind(r, "<Button-1>", lambda e, s=sid: self._click_slot(s))

        # ── GATE SECTION ──
        gate_y = row2_y + slot_h + 14
        gates = [
            ("MASUK\nMOBIL",  CAR_COL,   W*0.18),
            ("MASUK\nMOTOR",  MOTOR_COL, W*0.5),
            ("KELUAR\nSEMUA", YELLOW,    W*0.82),
        ]
        for label, color, cx in gates:
            gw, gh = 90, 44
            self.canvas.create_rectangle(cx - gw//2, gate_y, cx + gw//2, gate_y + gh,
                                          fill=color, outline="", width=0)
            self.canvas.create_text(cx, gate_y + gh//2, text=label,
                                     fill="#0D1117", font=("Inter", 9, "bold"), justify="center")

        # ── Kendaraan di dalam ──
        for uid, info in self.vehicles_inside.items():
            slot = info.get("slot")
            if slot and slot in self.slot_rects:
                r = self.slot_rects[slot]
                coords = self.canvas.coords(r)
                cx = (coords[0] + coords[2]) // 2
                cy = (coords[1] + coords[3]) // 2
                icon = "🚗" if info["vehicle_type"] == "Mobil" else "🏍️"
                self.canvas.create_text(cx, cy - 16, text=icon, font=("Inter", 18))

    def _slot_color(self, sid, status):
        if status == "FULL":
            return "#3A1010"  # Merah gelap
        base = CAR_COL if sid in CAR_SLOTS else MOTOR_COL
        # Warna hijau sangat gelap untuk slot kosong
        return "#0C2215"

    def _click_slot(self, sid):
        """Klik slot di canvas = shortcut set slot."""
        self.cmb_slot.set(sid)
        self._assign_slot(sid)

    # ──────────────────────────────────────
    # AKSI SIMULASI
    # ──────────────────────────────────────
    def _on_card_change(self, event=None):
        idx = self.cmb_card.current()
        self.active_uid = self.rfid_cards[idx]["uid"]

    def _active_uid(self):
        idx = self.cmb_card.current()
        return self.rfid_cards[idx]["uid"]

    def _simulate_entry(self):
        uid    = self._active_uid()
        vtype  = self.vehicle_var.get()

        # Cek kartu belum sedang parkir
        existing = sb_get(f"/rest/v1/parking_history?rfid_uid=eq.{uid}&status=eq.PARKED", self.token)
        if existing:
            self._log(f"⚠️  UID {uid} sudah aktif parkir. Tap EXIT dulu.")
            return

        # Cek saldo
        card_data = sb_get(f"/rest/v1/rfid_cards?uid=eq.{uid}&select=users(balance)", self.token)
        balance = int(card_data[0]["users"]["balance"]) if card_data else 0
        if balance < 5000:
            self._log(f"❌ Saldo tidak cukup (Rp {balance:,})")
            return

        # POST ke parking_history
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        ok, resp = sb_post("/rest/v1/parking_history", {
            "rfid_uid": uid,
            "status": "PARKED",
            "vehicle_type": vtype,
            "time_in": now_str
        }, self.token)

        if ok:
            hist_id = None
            try:
                import json
                data = json.loads(resp)
                hist_id = data[0]["id"] if data else None
            except:
                pass
            self.vehicles_inside[uid] = {"vehicle_type": vtype, "hist_id": hist_id, "slot": None}
            self._log(f"✅ Masuk: UID {uid} ({vtype}) — Gate {'Mobil' if vtype == 'Mobil' else 'Motor'} BUKA")

            # Aktifkan combo slot
            avail = CAR_SLOTS if vtype == "Mobil" else MOTOR_SLOTS
            empty_slots = [s for s in avail if self.slot_status.get(s) == "EMPTY"]
            self.cmb_slot.config(state="readonly", values=empty_slots)
            if empty_slots:
                self.cmb_slot.current(0)
            self.lbl_slot_info.config(text=f"Pilih slot untuk {vtype} ({uid})")
            self._draw_parking_area()
        else:
            self._log(f"❌ Gagal masuk: {resp}")

    def _assign_slot(self, forced_slot=None):
        uid   = self._active_uid()
        info  = self.vehicles_inside.get(uid)
        if not info:
            self._log("⚠️  Kendaraan ini belum tap masuk.")
            return

        slot = forced_slot or self.cmb_slot.get()
        if not slot:
            self._log("⚠️  Pilih slot dulu.")
            return

        # Update slot status di DB (mock Vision Engine)
        ok, _ = sb_patch(f"/rest/v1/parking_slots?slot_id=eq.{slot}",
                         {"status": "FULL", "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")},
                         self.token)
        if ok:
            info["slot"] = slot
            self.slot_status[slot] = "FULL"
            self._log(f"📍 UID {uid} ({info['vehicle_type']}) → Slot {slot} [FULL]")
            self._draw_parking_area()
        else:
            self._log(f"❌ Gagal update slot {slot}")

    def _simulate_exit(self):
        uid  = self._active_uid()
        info = self.vehicles_inside.get(uid)

        # Ambil sesi aktif dari DB
        hist = sb_get(
            f"/rest/v1/parking_history?rfid_uid=eq.{uid}&status=eq.PARKED"
            f"&select=id,time_in,vehicle_type,rfid_cards(user_id,users(balance))",
            self.token
        )
        if not hist:
            self._log(f"❌ UID {uid} tidak ada sesi parkir aktif.")
            return

        h       = hist[0]
        hist_id = h["id"]
        vtype   = h["vehicle_type"]
        user_id = h["rfid_cards"]["user_id"]
        balance = int(h["rfid_cards"]["users"]["balance"])
        time_in = h["time_in"]

        # Hitung durasi & tarif
        t_in = datetime.fromisoformat(time_in.replace("Z", "+00:00")).replace(tzinfo=None)
        duration_min = max(1, int((datetime.utcnow() - t_in).total_seconds() / 60))
        if vtype == "Motor":
            cost = 2000 + max(0, duration_min - 1) * 30
        else:
            cost = 5000 + max(0, duration_min - 1) * 80

        if balance < cost:
            self._log(f"❌ Saldo tidak cukup! Biaya Rp {cost:,}, Saldo Rp {balance:,}")
            return

        new_balance = balance - cost
        sb_patch(f"/rest/v1/users?id=eq.{user_id}", {"balance": new_balance}, self.token)
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        sb_patch(f"/rest/v1/parking_history?id=eq.{hist_id}", {
            "time_out": now_str,
            "duration_minutes": duration_min,
            "total_fee": cost,
            "status": "COMPLETED"
        }, self.token)

        # Kosongkan slot jika ada
        if info and info.get("slot"):
            slot = info["slot"]
            sb_patch(f"/rest/v1/parking_slots?slot_id=eq.{slot}",
                     {"status": "EMPTY", "last_updated": now_str}, self.token)
            self.slot_status[slot] = "EMPTY"

        # Hapus dari vehicles_inside
        self.vehicles_inside.pop(uid, None)

        # Update balance display
        self.balance = new_balance
        self.lbl_balance.config(text=f"💰 Rp {new_balance:,}")

        self._log(f"✅ Keluar: UID {uid} ({vtype}) | Durasi: {duration_min}m | "
                  f"Biaya: Rp {cost:,} | Sisa: Rp {new_balance:,}")
        self.cmb_slot.config(state="disabled", values=[])
        self.lbl_slot_info.config(text="(Tap masuk dulu sebelum pilih slot)")
        self._draw_parking_area()

    # ──────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────
    def _fetch_slots_bg(self):
        def _fetch():
            data = sb_get("/rest/v1/parking_slots?select=slot_id,status", self.token)
            for row in data:
                self.slot_status[str(row["slot_id"])] = row["status"]
            self.after(0, self._draw_parking_area)
        threading.Thread(target=_fetch, daemon=True).start()

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        if len(self.log_lines) > 200:
            self.log_lines.pop(0)
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()


if __name__ == "__main__":
    app = AutoPicsSimulator()
    app.mainloop()
