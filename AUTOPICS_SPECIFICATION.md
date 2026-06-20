# AUTOPICS (AUTOMATED PARKING SYSTEM)

## 📱 APPLICATION PREVIEW
Aplikasi Android AutoPics bertindak sebagai antarmuka pengguna (dashboard) utama untuk manajemen area parkir:
- **Live Counter & Visual Map**: Denah interaktif area parkir yang menampilkan slot secara real-time (Hijau = Kosong, Merah = Terisi). Menampilkan sisa kuota parkir mobil dan motor.
- **Billing Center**: Memungkinkan pengguna untuk mengecek saldo akun dan melihat riwayat transaksi (masuk/keluar gerbang).
- **RFID Card Management**: Pengguna dapat mendaftarkan (bind) kartu RFID ke akun mereka secara langsung melalui aplikasi dengan memasukkan ID yang telah dicetak/tertera pada kartu fisik.

---

## ⚙️ SYSTEM DIAGRAM

**[ INPUT ]** 
- Sensor Ultrasonik (HC-SR04)
- Modul RFID (MFRC522)
- USB Webcam / IP Camera

**[ CONTROLLER & ENGINE ]**
- ESP32 Microcontroller (Gate Controller, Core 0 & Core 1 dengan FreeRTOS)
- PC / Server (Vision Engine - Python)

*(Keduanya tersinkronisasi dua arah via Internet / Supabase)*

**[ OUTPUT ]**
- Servo Motor (Palang Pintu / Gate Barrier)
- Aplikasi Android (Visualisasi, Notifikasi & Akun)

---

## 📋 SPECIFICATION

| SPECIFICATION | DETAIL |
| :--- | :--- |
| **PROJECT NAME** | AutoPics (Automated Parking System) |
| **RELEASE** | 2026 |
| **TYPE** | IoT & Computer Vision Based Smart Parking System |
| **CONTROLLER** | ESP32 |
| **DISPLAY** | Smartphone Application Dashboard |
| **PROGRAMMING LANGUAGE**| C/C++ (ESP32), Python 3 (Vision Engine), Kotlin (Android App) |
| **DATABASE** | Supabase (PostgreSQL) - via REST API |
| **AI MODEL / TRACKER** | YOLOv8 (Object Detection) & ByteTrack (Multi-Object Tracking) |
| **RTOS** | FreeRTOS (Dual-Core Processing & Mutex Synchronization) |
| **CONNECTIVITY** | WiFi IEEE 802.11 b/g/n (Captive Portal via WiFiManager) & HTTPS REST API |
| **MONITORING** | Real-Time Parking Area Monitoring |
| **SENSORS** | • 3x Ultrasonic Sensor (HC-SR04)<br>• 3x RFID Reader Module (MFRC522)<br>• USB Webcam / IP Camera (Vision Input) |
| **ACTUATORS** | • 3x Servo Motor (Gate Barrier / Palang Pintu) |
| **POWER SUPPLY** | DC Power Supply (Microcontroller) & AC 220V (PC Server) |
| **DATA TRANSMISSION** | Internet / WiFi (Supabase Cloud Sync) |
| **PLATFORM** | Android Smartphone & PostgreSQL Cloud |
| **FEATURES** | • Real-Time Parking Slot Monitoring<br>• Camera-Based Occupancy Detection (YOLOv8 + ByteTrack)<br>• Automatic Gate Control (Hybrid: Ultrasonik + Tapping RFID)<br>• Live Interactive Visual Map (Hijau: Kosong, Merah: Terisi)<br>• Billing Center & Top-up Management<br>• Manual Card Binding (Registrasi Kartu via Input ID)<br>• Dynamic WiFi Config (WiFiManager Captive Portal) |
| **MEASURED PARAMETERS**| • Jarak Kedatangan Kendaraan via Sensor (Baseline Deviation)<br>• Posisi Kendaraan (Centroid) terhadap Polygon ROI (Vision)<br>• UID Tag Kartu RFID |
| **NOTIFICATIONS** | • Alert Kartu Belum Terdaftar (Unregistered Tap)<br>• Alert Saldo Tidak Mencukupi<br>• Peringatan Parkir Penuh (Empty Slot <= 0)<br>• Status Transaksi (Parked / Completed) |
| **VISION ENGINE** | • Deteksi Kendaraan menggunakan YOLOv8<br>• Pelacakan (Tracking) menggunakan ByteTrack<br>• Polygon ROI Status Checker<br>• Background Thread Cloud Batch Update |
| **APPLICATION** | Smart Parking Area Management |
| **ADVANTAGES** | • **Kamera sebagai Mata Cerdas:** Meniadakan kebutuhan sensor fisik di setiap slot.<br>• **Akurasi & Efisiensi Tinggi:** Memanfaatkan AI mutakhir (YOLOv8).<br>• **Sistem Real-Time Tangguh:** Proses HTTP dan kontrol gerbang dipisah via Dual-Core (FreeRTOS) sehingga *non-blocking*.<br>• **Keamanan Data Mutex:** Menggunakan Semaphore/Mutex locking untuk mencegah *crash* jaringan.<br>• **Hemat Biaya Infrastruktur:** Deteksi terpusat di server kamera.<br>• **Tahan Masalah Jaringan:** Memotong overhead SSL Handshake (Bypass SSL) untuk respons seketika. |
| **STATUS** | Prototype |
