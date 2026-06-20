# Spesifikasi Proyek: AutoPics (Automated Parking System)

Sistem parkir miniatur otomatis yang mengintegrasikan kontrol mekanik (Gate Controller ESP32) dengan pemrosesan citra berbasis GPU (Vision Engine Python) untuk manajemen slot parkir secara real-time.

---

## 1. Arsitektur Sistem

### A. Main Controller (ESP32)
*   **Fungsi**: Mengontrol akses masuk/keluar kendaraan melalui sistem gerbang hibrida (Ultrasonik + Tapping RFID).
*   **Input**: 3x Sensor Ultrasonik (HC-SR04), 3x Modul RFID (MFRC522) dengan konfigurasi SPI paralel.
*   **Output**: 3x Servo Motor (Palang Pintu).
*   **Logic**: Validasi akun, status, dan saldo secara realtime via REST API Supabase, kontrol gate non-blocking.

### B. Vision Input (USB Webcam / IP Camera)
*   **Tugas**: Menyediakan video area parkir secara real-time ke komputer server melalui OpenCV capture.

### C. Vision Engine (Python + YOLOv8 + ByteTrack)
*   **Tugas**: Menjalankan `python/TestByte.py`, melakukan deteksi kendaraan dengan YOLOv8 + ByteTrack, mengecek centroid kendaraan terhadap polygon ROI pada `python/parking_slots.json`, lalu mengunggah status slot ke Supabase secara real-time.

### D. User Interface (Mobile App)
*   **Fitur**:
    *   **Real-time Counter**: Membaca data jumlah slot kosong untuk mobil dan motor secara live dari Supabase.
    *   **Visual Map**: Layout denah area parkir interaktif (Warna Hijau: Kosong, Merah: Terisi) berdasarkan status tiap slot.
    *   **Billing Center**: Pengecekan saldo, riwayat transaksi (terintegrasi di tabel `transactions`), serta pengisian saldo (Top-up via aplikasi Kasir/Admin Desktop).
    *   **Registrasi Kartu Tanpa NFC HP**: Melakukan klaim kartu RFID baru melalui metode *Last Tap Claim* berbasis timestamp per gerbang fisik.

---

## 2. Struktur Data Supabase (PostgreSQL) - AKTIF & SINKRON

Struktur di bawah ini adalah data kontrak aktif yang digunakan oleh **ESP32 Gate Controller** (`src/main.cpp`) dan **Python Vision Engine** (`python/TestByte.py`):

```json
{
  "users": {
    "A1B2C3D4": {
      "balance": 50000,
      "status": "active",
      "parked_at": 1715222400,
      "owner_id": "firebase_auth_uid_user_hp"
    }
  },
  "parkir": {
    "slots": {
      "mobil": {
        "A1": {
          "terisi": false,
          "updated_at": "2026-05-09 11:30:00"
        }
      },
      "motor": {
        "B1": {
          "terisi": true,
          "updated_at": "2026-05-09 11:31:15"
        }
      }
    },
    "ringkasan": {
      "mobil": {
        "total": 4,
        "terisi": 1,
        "kosong": 3,
        "persen_terisi": 25.0,
        "updated_at": "2026-05-09 11:31:15"
      },
      "motor": {
        "total": 6,
        "terisi": 3,
        "kosong": 3,
        "persen_terisi": 50.0,
        "updated_at": "2026-05-09 11:31:15"
      }
    }
  },
  "unregistered_taps": {
    "MOTOR_IN": {
      "uid": "D1E2F3A4",
      "timestamp": 1715222520
    },
    "MOBIL_IN": {
      "uid": "F5G6H7I8",
      "timestamp": 1715222535
    },
    "EXIT_ALL": {
      "uid": "C9B8A7D6",
      "timestamp": 1715222550
    }
  }
}
```

### Penjelasan Detil Tipe Data & Lokasi:

1. **Informasi Pengguna (`/users/{UID_KARTU}`):**
   * `{UID_KARTU}`: Nama node menggunakan ID kartu RFID fisik (Hex, Uppercase, contoh: `"A1B2C3D4"`).
   * `balance` *(int)*: Nilai saldo pengguna (Rupiah).
   * `status` *(string)*: Status parkir kendaraan (`"active"` / `"parked"` / `"left"`).
   * `parked_at` *(int)*: Unix epoch timestamp (dalam detik) ketika tap masuk gerbang sukses. Digunakan untuk kalkulasi biaya keluar.

2. **Status Slot Parkir Visi Komputer (`parking_slots` table):**
   * Diperbarui secara berkala oleh program Python (`python/TestByte.py`).
   * `slot_id` *(string)*: ID slot numerik (`"1"` s/d `"14"`).
   * `status` *(string)*: `"FULL"` jika kendaraan terdeteksi terparkir di slot tersebut, `"EMPTY"` jika kosong.
   * `last_updated` *(timestamp)*: Waktu update terakhir dari Vision Engine.

3. **Ringkasan Parkir (`/parkir/ringkasan/{tipe_kendaraan}`):**
   * Diperbarui oleh Python. Dipantau secara live oleh aplikasi mobile dan **ESP32** (via Firebase Stream `/parkir/ringkasan`).
   * `kosong` *(int)*: Jumlah slot parkir kosong yang tersedia saat ini. Digunakan oleh ESP32 untuk menolak masuk jika gerbang penuh (`kosong <= 0`).

4. **Klaim Registrasi Kartu Baru (`/unregistered_taps/{NAMA_GERBANG}`):**
   * Diisi oleh ESP32 ketika mendeteksi ada tapping kartu yang belum terdaftar di database.
   * `uid` *(string)*: Kode UID kartu RFID yang baru saja di-*tap*.
   * `timestamp` *(int)*: Waktu pengetukan kartu fisik di gerbang. Aplikasi HP menggunakannya untuk validasi klaim kartu baru (maksimal selisih waktu 1 menit).

---

## 3. Alur Kerja Integrasi Sistem (Hybrid Workflow)

1.  **Vision Loop**: Webcam / IP Camera $\rightarrow$ OpenCV Capture $\rightarrow$ Python `TestByte.py` $\rightarrow$ YOLOv8 + ByteTrack $\rightarrow$ Polygon ROI Check $\rightarrow$ Update Supabase `parking_slots`.
2.  **Entry Gate**: Kendaraan terdeteksi ultrasonik $\rightarrow$ Tap RFID $\rightarrow$ ESP32 membaca sisa slot kosong dari Supabase `parking_slots` dan validasi saldo lewat tabel `users` / `rfid_cards` $\rightarrow$ Jika OK, servo membuka palang lalu mencatat sesi baru di `parking_history` dengan status `"PARKED"`.
3.  **Exit Gate**: Kendaraan terdeteksi $\rightarrow$ Tap RFID $\rightarrow$ ESP32 mengambil sesi aktif dari `parking_history` $\rightarrow$ Menghitung durasi parkir dan biaya $\rightarrow$ Potong saldo user $\rightarrow$ Update `parking_history` menjadi `"COMPLETED"` lalu servo membuka palang.
4.  **Mobile Monitoring**: Aplikasi mobile membaca `parking_slots` secara real-time $\rightarrow$ menampilkan 7 slot mobil (`1`-`7`) dan 7 slot motor (`8`-`14`) beserta status `FULL/EMPTY`.

---
*Dokumen teknis acuan pengembangan sistem AutoPics terbaru dan telah disinkronisasikan secara penuh.*
