#!/usr/bin/env python3
"""
Vision Engine Simulator - AutoPics
Simulasi update status slot parkir tanpa hardware kamera
"""

import sys, os, time, random, requests
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import SB_URL, SB_KEY, HEADERS, ALL_SLOTS, CAR_SLOTS, MOTOR_SLOTS

def update_slot(slot_id: str, status: str) -> bool:
    """Update status satu slot ke Supabase (string slot_id)."""
    if slot_id not in ALL_SLOTS:
        print(f"❌ Slot {slot_id} tidak valid (harus 1-14)")
        return False
    if status not in ("FULL", "EMPTY"):
        print(f"❌ Status harus FULL atau EMPTY")
        return False

    from datetime import datetime
    payload = [{
        "slot_id": slot_id,
        "status": status,
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    }]
    resp = requests.post(f"{SB_URL}/rest/v1/parking_slots", json=payload, headers=HEADERS)
    if resp.status_code in [200, 201]:
        print(f"✅ Slot {slot_id} → {status}")
        return True
    else:
        print(f"❌ Gagal: {resp.text}")
        return False

def random_fill(count=5):
    """Acak update beberapa slot random."""
    for _ in range(count):
        sid = random.choice(ALL_SLOTS)
        st  = random.choice(["FULL", "EMPTY"])
        update_slot(sid, st)
        time.sleep(0.3)

def fill_all(status: str):
    """Set semua slot ke status tertentu."""
    for sid in ALL_SLOTS:
        update_slot(sid, status)
        time.sleep(0.2)

def show_status():
    """Tampilkan status semua slot."""
    resp = requests.get(f"{SB_URL}/rest/v1/parking_slots?select=slot_id,status&order=slot_id.asc", headers=HEADERS)
    if resp.status_code == 200:
        print("\n=== PARKING SLOTS ===")
        for s in resp.json():
            mark = "🔴" if s["status"] == "FULL" else "🟢"
            tipe = "Mobil" if s["slot_id"] in CAR_SLOTS else "Motor"
            print(f"  {mark} Slot {s['slot_id']:>2} ({tipe}) : {s['status']}")
    else:
        print(f"❌ Gagal ambil data: {resp.text}")

def interactive():
    """Mode CLI interaktif."""
    print("Vision Simulator — Interactive Mode")
    print("Perintah: <slot> <FULL|EMPTY> | random | fill <FULL|EMPTY> | show | exit")
    while True:
        try:
            cmd = input("\n> ").strip().split()
            if not cmd: continue
            if cmd[0] == "exit": break
            elif cmd[0] == "show": show_status()
            elif cmd[0] == "random": random_fill(int(cmd[1]) if len(cmd) > 1 else 5)
            elif cmd[0] == "fill" and len(cmd) == 2: fill_all(cmd[1].upper())
            elif len(cmd) == 2 and cmd[0].isdigit(): update_slot(cmd[0], cmd[1].upper())
            else: print("Perintah tidak dikenali")
        except (EOFError, KeyboardInterrupt):
            break
    print("Bye!")

if __name__ == "__main__":
    import requests
    if len(sys.argv) == 3 and sys.argv[1].isdigit():
        update_slot(sys.argv[1], sys.argv[2].upper())
    else:
        interactive()