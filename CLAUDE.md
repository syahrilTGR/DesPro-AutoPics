# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

**ESP32 firmware (PlatformIO)**
> All commands below require PlatformIO CLI. Verify with `pio --version`.

| Target | macOS | Linux | Windows (cmd) | Windows (PowerShell) |
|---|---|---|---|---|
| Gate controller | `~/.platformio/penv/bin/pio run -e esp32dev -t upload` | `~/.platformio/penv/bin/pio run -e esp32dev -t upload` | `%USERPROFILE%\.platformio\penv\Scripts\pio.exe run -e esp32dev -t upload` | `& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e esp32dev -t upload` |
| Camera controller | `~/.platformio/penv/bin/pio run -e esp32cam -t upload` | `~/.platformio/penv/bin/pio run -e esp32cam -t upload` | `%USERPROFILE%\.platformio\penv\Scripts\pio.exe run -e esp32cam -t upload` | `& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e esp32cam -t upload` |
| RFID test | `~/.platformio/penv/bin/pio run -e test_rfid -t upload` | `~/.platformio/penv/bin/pio run -e test_rfid -t upload` | `%USERPROFILE%\.platformio\penv\Scripts\pio.exe run -e test_rfid -t upload` | `& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e test_rfid -t upload` |
| Ultrasonic test | `~/.platformio/penv/bin/pio run -e test_ultrasonic -t upload` | `~/.platformio/penv/bin/pio run -e test_ultrasonic -t upload` | `%USERPROFILE%\.platformio\penv\Scripts\pio.exe run -e test_ultrasonic -t upload` | `& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e test_ultrasonic -t upload` |
| Serial monitor | `~/.platformio/penv/bin/pio device monitor` | `~/.platformio/penv/bin/pio device monitor` | `%USERPROFILE%\.platformio\penv\Scripts\pio.exe device monitor` | `& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" device monitor` |

**Python vision engine**
- **Create virtualenv** (once)
  ```bash
  # macOS / Linux
  python -m venv venv
  source venv/bin/activate
  # Windows Command Prompt
  python -m venv venv
  venv\Scripts\activate
  # Windows PowerShell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Install dependencies**
  `pip install -r requirements.txt`
- **Run detection loop**
  `python python/TestByte.py`
- **Run simulator** (gate entry/exit)
  `python simulator/simulate_gate.py entry TEST0002`
  `python simulator/simulate_gate.py exit TEST0002`
- **Run full simulation**
  `python simulator/simulate_all.py --auto`

**Supabase utilities**
- **Check DB schema** – script `check_db.py`
- **Reset DB** – script `reset_db.py`
- **Seed test data** – script `seed_test_data.py`

**Android app (Kotlin)**
- **Build debug APK**
  `cd autopics && ./gradlew assembleDebug`
- **Run unit tests**
  `cd autopics && ./gradlew testDebugUnitTest`
- **Run UI tests**
  `cd autopics && ./gradlew connectedDebugAndroidTest`
- **Clean build**
  `cd autopics && ./gradlew clean`
- **Run a single test** (replace `MyTest` with the class name)
  `cd autopics && ./gradlew testDebugUnitTest --tests com.example.autopics.MyTest`

## High-Level Architecture

```
+-------------------+          +-------------------+          +-------------------+
|   ESP32 Gate      |  <--->   |   Supabase Cloud  |  <--->   |   Android App     |
|  (Arduino C++)   |          | (PostgreSQL)      |          | (Kotlin/Compose) |
+-------------------+          +-------------------+          +-------------------+
        ^                                 ^                              ^
        |                                 |                              |
        |                                 |                              |
        v                                 v                              v
+-------------------+          +-------------------+          +-------------------+
|   Vision Engine   |  <--->   |   Python Backend  |  <--->   |   Simulator       |
|  (Python + YOLO) |          | (Supabase client) |          | (Python scripts) |
+-------------------+          +-------------------+          +-------------------+
```

* **ESP32 Gate Controller** – C++ code under `src/`. Handles RFID reads, ultrasonic sensors, and servo control. Communicates with Supabase via HTTPS (REST) to validate users, check balance, and record entry/exit in `parking_history`. Uses FreeRTOS mutexes to avoid network stack collisions between Core 0 (WiFi polling) and Core 1 (RFID + ultrasonic).

* **Supabase Backend** – PostgreSQL schema includes tables:
  - `users` (id, name, email, password hash, balance)
  - `rfid_cards` (uid, user_id, vehicle_type)
  - `parking_history` (rfid_uid, slot_id, time_in, time_out, status, total_fee)
  - `parking_slots` (slot_id, status, last_updated)
  - `transactions` (user_id, amount, transaction_type)
  - `unregistered_taps` (temporary store for new RFID cards - planned, not yet implemented in ESP32)

* **Vision Engine** – Python script `python/TestByte.py` captures video, runs YOLOv8 + ByteTrack, maps detected vehicle centroids to slot polygons defined in `python/parking_slots.json`, and updates the `parking_slots` table in real-time. Drop to `Y_http_backup.py` if HTTPS sync fails.

* **Android App** – Jetpack Compose UI under `autopics/app/src/main/java/com/example/autopics/`. Key screens:
  - `LoginScreen.kt` / `RegisterScreen.kt` – Supabase native auth, PBKDF2 password hashing (`PasswordHash.kt`).
  - `MainScreen.kt` – Dashboard showing empty/full slot counts, user balance, and navigation to other screens.
  - `ParkingHistoryScreen.kt` – Shows user-specific parking records (fix: query `rfid_cards` first, then `parking_history`; current code queries `users.rfid_uid` which does not exist).
  - `TopUpScreen.kt` – Balance top-up using the `transactions` table.
  - UI components live in `ui/components/` (e.g., `SlotCard.kt`, `RFIDRegistrationCard.kt`).

* **Simulator** – Python utilities under `simulator/` to mock gate entry/exit events and vision detections for end-to-end testing.

## Important Project Files

| Path | Purpose |
|------|---------|
| `platformio.ini` | PlatformIO build configuration for ESP32 firmware. |
| `src/main.cpp` | **Gate controller firmware** — RFID, ultrasonic, servo, Supabase REST. |
| `src/main-espcam.cpp` | Camera controller firmware (AI detection). |
| `python/TestByte.py` | **Primary vision loop** — YOLOv8 + ByteTrack + slot mapping (GPU). |
| `python/y.py` | Legacy vision loop — deprecated. |
| `python/parking_slots.json` | Slot polygon ROI coordinates for detection mapping. |
| `python/bytetrack.yaml` | ByteTrack tracker configuration. |
| `python/bos.pt` | YOLOv8 trained model (CUDA). |
| `simulator/simulate_gate.py` | CLI for gate entry/exit events. |
| `simulator/simulate_all.py` | Full end-to-end simulation (auto mode). |
| `simulator/supabase_client.py` | Shared Supabase client for simulator scripts. |
| `check_db.py` | Check Supabase DB schema. |
| `reset_db.py` | Reset Supabase database. |
| `seed_test_data.py` | Seed test users & RFID cards. |
| `PANDUAN_OPERASIONAL.md` | **Complete operational manual** (36KB) — hardware wiring, SOP, troubleshooting. |
| `PROJECT_SPECIFICATION.md` | Full system spec, data model, and workflow description. |
| `README.md` (root) | High-level project overview. |
| `MOBILE_APP_DEVELOPMENT_GUIDE.md` | Android Studio setup and common commands (app not yet in repo). |
| `TEST_PLAN.md` | Manual test steps for Android integration testing. |
| `DESKRIPSI_PROYEK_LENGKAP.md` | Full project description (Indonesian). |
| `DEMO_PANDUAN.md` | Demo walkthrough guide. |
| `ANDROID_UPDATE_NOTES.md` | Android app update notes. |

## Development Notes

- **ESP32 macOS upload fix** – `platformio.ini` locks `upload_speed = 115200` and uses `setInsecure()` SSL bypass to avoid termios and handshake failures.
- **Supabase auth** – Environment variables `SUPABASE_URL` and `SUPABASE_ANON_KEY` are read in `SupabaseHelper.kt`. Keep them out of source control.
- **Password hashing** – Salt "autopics_salt" should be moved to a secure env var before production.
- **Vision engine** – Ensure CUDA is available for YOLOv8; otherwise fallback to CPU (may be slow). The project ships a CUDA model `bos.pt` in `python/`.
- **Testing workflow** – After firmware flash, run `python simulator/simulate_gate.py entry <RFID>` to create a parking session, then verify app UI reflects slot status and balance changes.
- **Known issue** – `ParkingHistoryScreen.kt` queries `users.rfid_uid`; correct flow:
  1. Query `rfid_cards` where `user_id = ownerId` → obtain `uid`.
  2. Query `parking_history` where `rfid_uid = uid`.
  Update the Kotlin data class and query accordingly.
- **Critical bug fix** – `main.cpp.bak_preventGateOpen` references `rfid` as a pointer (`MFRC522* rfid`) instead of reference (`MFRC522 rfid`) in Gate struct. This causes RFID sensors to malfunction. Use `src/main.cpp` which correctly assigns RFID modules by reference for MOTOR_IN (rfidMot), MOBIL_IN (rfidMob), and EXIT_ALL (rfidExit).

---
