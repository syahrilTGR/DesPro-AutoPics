#!/usr/bin/env python3
"""
AutoPics Unified Simulator
Simulator gabungan untuk testing mandiri tanpa hardware
"""

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
from supabase_client import SB_URL, SB_KEY, HEADERS, DUMMY_USERS, ALL_SLOTS, CAR_SLOTS, MOTOR_SLOTS
from simulate_gate import simulate_entry, simulate_exit
from simulate_vision import update_slot, fill_all, show_status

def ensure_dummy_users_exist():
    """Buat dummy user + kartu RFID jika belum ada."""
    for u in DUMMY_USERS:
        resp = requests.get(f"{SB_URL}/rest/v1/rfid_cards?uid=eq.{u['uid']}&select=uid", headers=HEADERS)
        if resp.status_code == 200 and len(resp.json()) > 0:
            continue

        user_resp = requests.post(f"{SB_URL}/rest/v1/users", json={"name": u["name"], "balance": u["balance"]}, headers=HEADERS)
        if user_resp.status_code in [200, 201]:
            user_id = user_resp.json()[0]["id"]
            rfid_resp = requests.post(f"{SB_URL}/rest/v1/rfid_cards", json={
                "uid": u["uid"],
                "user_id": user_id,
                "card_name": u["name"],
                "vehicle_type": u["vehicle"]
            }, headers=HEADERS)
            if rfid_resp.status_code in [200, 201]:
                print(f"  ✅ Dummy user: {u['name']} (UID: {u['uid']})")

def init_all_slots():
    """Pastikan semua slot ada di parking_slots."""
    resp = requests.get(f"{SB_URL}/rest/v1/parking_slots?select=slot_id", headers=HEADERS)
    if resp.status_code == 200:
        existing = {s["slot_id"] for s in resp.json()}
        missing = [s for s in ALL_SLOTS if s not in existing]
        if missing:
            payload = [{"slot_id": s, "status": "EMPTY"} for s in missing]
            requests.post(f"{SB_URL}/rest/v1/parking_slots", json=payload, headers=HEADERS)
            print(f"  ✅ Ditemukan {len(missing)} slot baru, diinisialisasi EMPTY")

def show_current_status():
    """Tampilkan ringkasan status parkir."""
    slots_resp = requests.get(f"{SB_URL}/rest/v1/parking_slots?select=slot_id,status", headers=HEADERS)
    if slots_resp.status_code == 200:
        slots = slots_resp.json()
        full_car   = sum(1 for s in slots if s["status"] == "FULL" and s["slot_id"] in CAR_SLOTS)
        empty_car  = sum(1 for s in slots if s["status"] == "EMPTY" and s["slot_id"] in CAR_SLOTS)
        full_motor = sum(1 for s in slots if s["status"] == "FULL" and s["slot_id"] in MOTOR_SLOTS)
        empty_motor= sum(1 for s in slots if s["status"] == "EMPTY" and s["slot_id"] in MOTOR_SLOTS)
        print(f"\n{'='*40}")
        print(f" 📊 STATUS PARKIR")
        print(f"{'='*40}")
        print(f" 🚗 Mobil  : {empty_car} kosong / {full_car} terisi (slot 1-7)")
        print(f" 🏍️  Motor  : {empty_motor} kosong / {full_motor} terisi (slot 8-14)")

def show_registered_users():
    """Tampilkan daftar user terdaftar."""
    print(f"\n{'='*40}")
    print(" 👥 DAFTAR USER TERDAFTAR")
    print(f"{'='*40}")
    for u in DUMMY_USERS:
        resp = requests.get(f"{SB_URL}/rest/v1/rfid_cards?uid=eq.{u['uid']}&select=uid", headers=HEADERS)
        status = "✅" if resp.status_code == 200 and resp.json() else "❌ belum ada"
        print(f" {u['uid']} | {u['name']:20} | {u['vehicle']:6} | {status}")

def quick_test():
    """Demo cepat: masukkan mobil lalu keluarkan."""
    print("\n🚀 QUICK TEST: Entry + Exit untuk UID TEST0002")
    print("  1. Simulating entry...")
    simulate_entry("TEST0002")
    print("  2. Simulating exit...")
    simulate_exit("TEST0002")

def menu():
    while True:
        show_current_status()
        print(f"\n{'='*40}")
        print(" AutoPics SIMULATOR")
        print(f"{'='*40}")
        print(" [1] Simulate Vehicle Entry (RFID)")
        print(" [2] Simulate Vehicle Exit (RFID)")
        print(" [3] Set Slot Status (Manual)")
        print(" [4] Random Fill Slots")
        print(" [5] Fill All Slots (FULL/EMPTY)")
        print(" [6] Show All Slot Status")
        print(" [7] Show Registered Users")
        print(" [8] Quick Test (Entry → Exit)")
        print(" [9] Re-init Dummy Users")
        print(" [0] Exit")

        try:
            pilihan = input("\nPilih menu: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if pilihan == "1":
            uid = input("UID kartu (atau Enter untuk dummy): ").strip() or "TEST0002"
            simulate_entry(uid.upper())
        elif pilihan == "2":
            uid = input("UID kartu (atau Enter untuk dummy): ").strip() or "TEST0002"
            simulate_exit(uid.upper())
        elif pilihan == "3":
            slot = input("Slot ID (1-14): ").strip()
            status = input("Status (FULL/EMPTY): ").strip().upper()
            update_slot(slot, status)
        elif pilihan == "4":
            try:
                n = int(input("Berapa slot random (default 5): ").strip() or "5")
            except:
                n = 5
            from simulate_vision import random_fill
            random_fill(n)
        elif pilihan == "5":
            st = input("Status (FULL/EMPTY): ").strip().upper()
            fill_all(st)
        elif pilihan == "6":
            show_status()
        elif pilihan == "7":
            show_registered_users()
        elif pilihan == "8":
            quick_test()
        elif pilihan == "9":
            ensure_dummy_users_exist()
        elif pilihan == "0":
            break

def run_auto_test():
    """Jalankan test otomatis tanpa menu interaktif."""
    print("🔧 AutoPics Simulator - Auto Test Mode")
    ensure_dummy_users_exist()
    init_all_slots()
    print("\n[1] Fill All EMPTY...")
    fill_all("EMPTY")
    print("[2] Quick Test Entry/Exit TEST0002...")
    quick_test()
    print("[3] Set slot 1 FULL, slot 8 FULL...")
    update_slot("1", "FULL")
    update_slot("8", "FULL")
    print("[4] Show final status...")
    show_status()
    print("\n✅ Auto test selesai!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        run_auto_test()
    else:
        print("🔧 AutoPics Simulator - Inisialisasi...")
        ensure_dummy_users_exist()
        init_all_slots()
        menu()
        print("👋 Sampai jumpa!")