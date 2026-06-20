#!/usr/bin/env python3
"""
Shared Supabase config untuk semua simulator.
"""

SB_URL  = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SB_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

HEADERS = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation"
}

# Slot valid: 1-7 mobil, 8-14 motor
CAR_SLOTS    = [str(i) for i in range(1, 8)]    # ["1", ..., "7"]
MOTOR_SLOTS  = [str(i) for i in range(8, 15)]   # ["8", ..., "14"]
ALL_SLOTS    = CAR_SLOTS + MOTOR_SLOTS

# User dummy untuk testing gate tanpa seed_test_data.py
DUMMY_USERS = [
    {"name": "Tester Motor",  "balance": 50000, "uid": "TEST0001", "vehicle": "Motor"},
    {"name": "Tester Mobil",  "balance": 50000, "uid": "TEST0002", "vehicle": "Mobil"},
    {"name": "Awang",         "balance": 50000, "uid": "A9369711", "vehicle": "Motor"},
    {"name": "Syahril",       "balance": 50000, "uid": "19019211", "vehicle": "Mobil"},
    {"name": "Refi",          "balance": 50000, "uid": "09D97D11", "vehicle": "Motor"},
    {"name": "Noval",         "balance": 50000, "uid": "29900307", "vehicle": "Mobil"},
]
