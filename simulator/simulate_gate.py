#!/usr/bin/env python3
"""
Gate Controller Simulator - AutoPics
Simulasi tap RFID masuk/keluar tanpa hardware ESP32
"""

import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import SB_URL, SB_KEY, HEADERS

def get_user_and_card(uid: str):
    """Ambil data user + card info berdasarkan UID."""
    resp = requests.get(f"{SB_URL}/rest/v1/rfid_cards?uid=eq.{uid}&select=user_id,users(id,balance)", headers=HEADERS)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]
    return None

def check_avail_slots(vehicle_type: str) -> int:
    """Cek jumlah slot kosong berdasarkan tipe kendaraan."""
    # 1-7 = Mobil, 8-14 = Motor
    slot_range = "slot_id.gte.1.and.slot_id.lte.7" if vehicle_type == "Mobil" else "slot_id.gte.8.and.slot_id.lte.14"
    resp = requests.get(f"{SB_URL}/rest/v1/parking_slots?{slot_range}&status=eq.EMPTY", headers=HEADERS)
    if resp.status_code == 200:
        return len(resp.json())
    return 0

def simulate_entry(uid: str, vehicle_type: str = "Mobil") -> bool:
    """Simulasi kendaraan masuk via tap RFID.
    
    vehicle_type: 'Motor' atau 'Mobil' — ditentukan dari gate mana kartu ditap.
    """
    card = get_user_and_card(uid)
    if not card:
        print(f"❌ UID {uid} tidak terdaftar")
        return False

    balance = card["users"]["balance"]

    if balance < 5000:
        print(f"❌ Saldo tidak cukup (Rp {balance})")
        return False

    avail = check_avail_slots(vehicle_type)
    if avail <= 0:
        print(f"⚠️ Slot {vehicle_type} penuh")
        return False

    payload = {
        "rfid_uid": uid,
        "status": "PARKED",
        "vehicle_type": vehicle_type,
        "time_in": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    }
    resp = requests.post(f"{SB_URL}/rest/v1/parking_history", json=payload, headers=HEADERS)
    if resp.status_code in [200, 201]:
        print(f"✅ Entry sukses - {uid} ({vehicle_type}) masuk")
        return True
    else:
        print(f"❌ Gagal entry: {resp.text}")
        return False

def simulate_exit(uid: str) -> bool:
    """Simulasi kendaraan keluar via tap RFID."""
    # Ambil sesi aktif
    resp = requests.get(
        f"{SB_URL}/rest/v1/parking_history?rfid_uid=eq.{uid}&status=eq.PARKED&select=id,time_in,vehicle_type,rfid_cards(user_id)",
        headers=HEADERS
    )
    if resp.status_code != 200 or not resp.json():
        print(f"❌ UID {uid} tidak ada sesi parkir aktif")
        return False

    hist = resp.json()[0]
    hist_id = hist["id"]
    user_id = hist["rfid_cards"]["user_id"]
    time_in = hist["time_in"]
    vtype = hist["vehicle_type"]  # Dibaca dari histori, bukan dari rfid_cards

    # Hitung durasi + biaya
    from datetime import datetime
    t_in = datetime.fromisoformat(time_in.replace("Z", "+00:00"))
    duration_min = max(1, int((datetime.utcnow().replace(tzinfo=None) - t_in.replace(tzinfo=None)).total_seconds() / 60))

    if vtype == "Motor":
        cost = 2000 + max(0, duration_min - 1) * 30
    else:
        cost = 5000 + max(0, duration_min - 1) * 80

    # Update user balance
    user_resp = requests.get(f"{SB_URL}/rest/v1/users?id=eq.{user_id}&select=balance", headers=HEADERS)
    if user_resp.status_code == 200 and user_resp.json():
        new_balance = max(0, user_resp.json()[0]["balance"] - cost)
        requests.patch(f"{SB_URL}/rest/v1/users?id=eq.{user_id}", json={"balance": new_balance}, headers=HEADERS)

    # Update history
    exit_payload = {
        "time_out": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "duration_minutes": duration_min,
        "total_fee": cost,
        "status": "COMPLETED"
    }
    requests.patch(f"{SB_URL}/rest/v1/parking_history?id=eq.{hist_id}", json=exit_payload, headers=HEADERS)
    print(f"✅ Exit sukses - Durasi: {duration_min}m, Biaya: Rp {cost}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simulate_gate.py <entry|exit> <UID>")
        print("Example: python simulate_gate.py entry A9369711")
        sys.exit(1)

    action, uid = sys.argv[1].lower(), sys.argv[2].upper()
    # Argumen ke-3 (opsional): jenis gate — 'Motor' atau 'Mobil' (default: Mobil)
    vehicle_type = sys.argv[3].capitalize() if len(sys.argv) >= 4 else "Mobil"
    if action == "entry":
        simulate_entry(uid, vehicle_type)
    elif action == "exit":
        simulate_exit(uid)
    else:
        print("Action must be 'entry' atau 'exit'")