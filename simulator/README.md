# 🧪 Panduan Simulator AutoPics

Simulator untuk testing komponen secara terpisah tanpa hardware asli. Semua simulator tetap terkoneksi ke **Supabase** yang sama, sehingga hasil testing langsung terlihat di mobile app maupun dashboard Supabase.

---

## 1. Mengapa Simulator?

```
┌─────────────────┐       ┌──────────┐       ┌─────────────────┐
│  simulate_gate   │ ────► │ Supabase │ ◄──── │ simulate_vision  │
│  (RFID + Gate)   │       │ (Shared) │       │  (Slot Status)   │
└─────────────────┘       └────┬─────┘       └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌──────────┐ ┌────────┐ ┌────────┐
              │Mobile App│ │ESP32   │ │Dashboard│
              │(Android) │ │(Real)  │ │Supabase│
              └──────────┘ └────────┘ └────────┘
```

Ketiga tim (hardware, vision, mobile) bisa bekerja mandiri. Yang belum ready, digantikan simulator.

| Tim | Butuh simulator? | Yang disimulasikan |
|-----|-------------------|-------------------|
| **Mobile App** | ✅ | `simulate_gate.py` + `simulate_vision.py` |
| **Hardware ESP32** | ✅ | `simulate_vision.py` (slot berubah) |
| **Vision Engine** | ❌ | Pakai komponen asli (`TestByte.py`) |

---

## 2. Instalasi

```bash
cd "despro AutoPics"
pip install -r simulator/requirements.txt
```

Satu dependency saja: `requests`.

---

## 3. File Simulator

| File | Fungsi |
|------|--------|
| `supabase_client.py` | Config shared (URL, Key, slot lists, dummy users) |
| `simulate_gate.py` | Simulasi tap RFID masuk/keluar |
| `simulate_vision.py` | Simulasi update status slot parkir |
| `simulate_all.py` | Menu interaktif gabungan |
| `requirements.txt` | Dependencies |

---

## 4. Dummy Users (Akun Test)

Simulator otomatis membuat user dummy saat pertama kali dijalankan:

| UID | Nama | Tipe | Saldo |
|-----|------|------|-------|
| TEST0001 | Tester Motor | Motor | Rp 50.000 |
| TEST0002 | Tester Mobil | Mobil | Rp 50.000 |
| A9369711 | Awang | Motor | Rp 50.000 |
| 19019211 | Syahril | Mobil | Rp 50.000 |
| 09D97D11 | Refi | Motor | Rp 50.000 |
| 29900307 | Noval | Mobil | Rp 50.000 |

User dummy dibuat di tabel `users` + `rfid_cards` secara otomatis. Jika sudah ada (dari `seed_test_data.py`), tidak dibuat ulang.

---

## 5. Cara Pakai

### Mode Interaktif (Menu)

```bash
python simulator/simulate_all.py
```

Akan muncul menu:
```
🔧 AutoPics Simulator - Inisialisasi...
  ✅ Dummy user: Tester Motor (UID: TEST0001)
  ✅ Dummy user: Tester Mobil (UID: TEST0002)

========================================
 📊 STATUS PARKIR
========================================
 🚗 Mobil  : 7 kosong / 0 terisi (slot 1-7)
 🏍️  Motor  : 7 kosong / 0 terisi (slot 8-14)

========================================
 AutoPics SIMULATOR
========================================
 [1] Simulate Vehicle Entry (RFID)
 [2] Simulate Vehicle Exit (RFID)
 [3] Set Slot Status (Manual)
 [4] Random Fill Slots
 [5] Fill All Slots (FULL/EMPTY)
 [6] Show All Slot Status
 [7] Show Registered Users
 [8] Quick Test (Entry → Exit)
 [9] Re-init Dummy Users
 [0] Exit
```

### Mode CLI (Satu Perintah)

**Gate Simulator:**
```bash
# Kendaraan masuk
python simulator/simulate_gate.py entry TEST0002

# Kendaraan keluar
python simulator/simulate_gate.py exit TEST0002
```

**Vision Simulator:**
```bash
# Set slot 3 jadi FULL
python simulator/simulate_vision.py 3 FULL

# Set slot 10 jadi EMPTY
python simulator/simulate_vision.py 10 EMPTY

# Mode interaktif
python simulator/simulate_vision.py
```

---

## 6. Alur Testing per Tim

### 📱 Tim Mobile App

**Tujuan:** Test UI tanpa menunggu ESP32 + Vision Engine selesai.

```bash
# 1. Jalankan simulator
python simulator/simulate_all.py

# 2. Pilih [5] Fill All Slots → EMPTY
# 3. Buka app Android → cek slot kosong semua

# 4. Pilih [1] Entry (UID: TEST0002)
# 5. Cek app Android → PersonalParkingCard muncul

# 6. Pilih [3] Set slot 1 → FULL
# 7. Cek app Android → Slot 1 berubah merah

# 8. Pilih [2] Exit (UID: TEST0002)
# 9. Cek app Android → status parkir hilang
```

### 🔧 Tim Hardware ESP32

**Tujuan:** Test gerbang tanpa Vision Engine berjalan.

```bash
# Jalankan vision simulator saja
python simulator/simulate_vision.py

# Di terminal simulator:
> random 5     # Acak 5 slot
> show          # Lihat status
> 1 FULL        # Set slot 1 FULL
> exit
```

### 🎥 Tim Vision Engine

**Tujuan:** Test `TestByte.py` tanpa ESP32 gerbang.

Tidak perlu simulator — pakai `TestByte.py` langsung. Hasil deteksi otomatis update Supabase, terbaca di app Android.

---

## 7. Slot Parkir

| Blok | Tipe | Range ID | Jumlah |
|------|------|----------|--------|
| Blok A | Mobil | "1" – "7" | 7 slot |
| Blok B | Motor | "8" – "14" | 7 slot |

Slot ID dikirim sebagai **string** ke Supabase (VARCHAR).

---

## 8. Tarif Parkir (untuk simulasi exit)

| Tipe | Base (1 jam) | Tambahan |
|------|--------------|----------|
| Motor | Rp 2.000 | Rp 30/menit (setelah 1 jam) |
| Mobil | Rp 5.000 | Rp 80/menit (setelah 1 jam) |

Saldo minimum masuk: **Rp 5.000**.

---

## 9. Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `❌ UID tidak terdaftar` | Pilih menu [9] Re-init Dummy Users |
| `⚠️ Slot penuh` | Pilih menu [5] Fill All Slots → EMPTY |
| Gagal koneksi Supabase | Cek koneksi internet, pastikan Supabase project aktif |
| `requests module not found` | Jalankan `pip install -r simulator/requirements.txt` |

---

> ⚠️ **Catatan Keamanan:**
> Simulator ini hanya untuk **development/testing**. Jangan commit `SUPABASE_KEY` ke repository publik.
