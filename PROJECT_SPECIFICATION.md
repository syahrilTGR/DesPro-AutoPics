# Spesifikasi Proyek: AutoPics (Automated Parking System)

Sistem parkir miniatur otomatis yang mengintegrasikan kontrol mekanik (Gate Control) dengan pemrosesan citra (Computer Vision) untuk manajemen slot parkir secara real-time.

## 1. Arsitektur Sistem

### A. Main Controller (ESP32)
*   **Fungsi**: Mengontrol akses masuk dan keluar kendaraan serta otentikasi.
*   **Input**: 3x Ultrasonik (HC-SR04), 1x RFID Reader (RC522).
*   **Output**: 3x Servo Motor (Palang Pintu).
*   **Logic**: Validasi akun & saldo via Firebase, kontrol gate non-blocking.

### B. Visual Streamer (ESP32-CAM)
*   **Tugas**: Mengambil stream video area parkir dan mengirim ke server via Wi-Fi.

### C. Vision Engine (Python + OpenCV)
*   **Tugas**: Pemrosesan ROI (Region of Interest) untuk mendeteksi objek di koordinat slot yang telah ditentukan (Labeling). Mengomunikasikan status slot ke Firebase.

### D. User Interface (Mobile App)
*   **Fitur**:
    *   **Real-time Counter**: Menampilkan angka sisa slot mobil/motor.
    *   **Visual Map**: Layout parkir dengan indikator warna (Hijau: Kosong, Merah: Isi) berdasarkan data koordinat ROI.
    *   **Billing Center**: Cek saldo, top-up, dan riwayat transaksi.

---

## 2. Struktur Data Firebase (RTDB)

```json
{
  "parking_system": {
    "status": {
      "is_full_motor": false,
      "is_full_car": false,
      "remaining_motor": 2,
      "remaining_car": 2
    },
    "slots": {
      "m1": {"status": "empty", "type": "motor"},
      "m2": {"status": "occupied", "type": "motor"},
      "c1": {"status": "empty", "type": "car"},
      "c2": {"status": "empty", "type": "car"}
    }
  },
  "users": {
    "UID_RFID_SAMPLE": {
      "name": "User Name",
      "balance": 50000,
      "parked_at": "2024-04-24 10:00:00",
      "status": "parked"
    }
  }
}
```

---

## 3. Alur Kerja (Hybrid Workflow)

1.  **Vision Loop**: ESP32-CAM $\rightarrow$ Python (ROI Logic) $\rightarrow$ Update Firebase `slots`.
2.  **Entry Gate**: Kendaraan terdeteksi $\rightarrow$ Tap RFID $\rightarrow$ ESP32 cek Firebase (Sisa Slot? & Saldo?) $\rightarrow$ Buka Palang & Update `parked_at`.
3.  **Exit Gate**: Tap RFID $\rightarrow$ ESP32 hitung durasi dari `parked_at` $\rightarrow$ Potong Saldo $\rightarrow$ Buka Palang Keluar.
4.  **App Sync**: User melihat denah visual (Map) dan sisa slot di aplikasi mobile.

---
*Dokumen teknis acuan pengembangan AutoPics.*
