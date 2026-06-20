# 🚗 AutoPics (Automated Parking System)

**Sistem Inteligensi Parkir Terintegrasi IoT, Computer Vision, dan Ekosistem Cloud.**

AutoPics adalah solusi manajemen parkir pintar yang menggabungkan efisiensi hardware **ESP32**, kekuatan deteksi visual **Python (OpenCV)**, dan sinkronisasi real-time **Supabase (PostgreSQL)**. Sistem ini mengotomatisasi pemantauan slot parkir tanpa memerlukan sensor fisik di setiap slot, melainkan menggunakan kamera sebagai mata cerdas.

---

## 🚀 Fitur Unggulan (Optimized)

Sistem ini telah dioptimasi untuk performa maksimal pada perangkat edge:

-   **⚡ YOLOv8 + ByteTrack Real-time Detection**: Deteksi kendaraan secara akurat dengan tracking ID unik untuk setiap kendaraan.
-   **🅿️ Polygon-based ROI Parking Slots**: Slot parkir didefinisikan via polygon (4 titik) di `parking_slots.json`, deteksi centroid otomatis.
-   **🔥 Supabase Cloud Sync**: Status slot parkir diupdate secara instan ke cloud via REST API batch update.
-   **📉 Background Thread Sender**: Batch update supabase non-blocking, hemat bandwidth.

---

## 🏗️ Arsitektur Sistem

1.  **Gate Controller (ESP32)**: Mengontrol gerbang fisik (Servo), sensor ultrasonik, dan pembaca RFID (RC522).
2.  **Vision Engine (Python & YOLOv8)**: Unit pemrosesan AI menggunakan YOLOv8 + ByteTrack untuk deteksi kendaraan, memeriksa occupancy slot parkir secara real-time.
3.  **Cloud Backend (Supabase)**: Pusat data relasional (PostgreSQL) untuk status slot, entitas pengguna, dan pencatatan riwayat parkir.
4.  **Mobile App**: Dashboard interaktif untuk pengguna mencari tempat parkir kosong.

---

## 🛠️ Instalasi & Persiapan

### 1. ESP32 Gate Controller (Physical Firmware)
-   Buka folder proyek di **PlatformIO**.
-   **Upload Command**:
    -   *Standard*: `pio run -e esp32dev -t upload`
    -   *Windows*: `%USERPROFILE%\.platformio\penv\Scripts\pio run -e esp32dev -t upload`
    -   *Mac*: `~/.platformio/penv/bin/pio run -e esp32dev -t upload`

### 3. Python Client (Vision Engine)
-   Pastikan sudah menginstal Python 3.10+.
-   Buat dan aktifkan *Virtual Environment* (venv):
    ```bash
    # Buat venv baru (hanya dilakukan sekali)
    python -m venv venv

    # Aktifkan venv (Lakukan ini setiap kali membuka terminal baru)
    source venv/bin/activate     # Untuk macOS / Linux
    venv\Scripts\activate        # Untuk Windows (Command Prompt)
    .\venv\Scripts\Activate.ps1  # Untuk Windows (PowerShell)
    ```
-   Instal semua dependensi dari file requirements:
    ```bash
    pip install -r requirements.txt
    ```
-   *(Opsional)* Anda dapat memasukkan API Key Supabase Anda langsung ke dalam baris kode di `python/TestByte.py` agar sistem dapat login secara resmi.
-   Jalankan engine:
    ```bash
    python python/TestByte.py
    ```

---

## ⚙️ Konfigurasi ROI (Slot Parkir)
Anda dapat mengatur koordinat slot parkir langsung melalui file `parking_slots.json`. Sistem akan secara otomatis melakukan monitoring pada area yang telah didefinisikan tersebut. Jalankan `parking_roi_config.py` untuk membuat polygon slot secara visual.

---

## 🛠️ Catatan Khusus Pengembang & Pemecahan Masalah

Untuk memastikan kelancaran pengembangan di masa depan, berikut adalah beberapa poin optimasi penting yang telah diterapkan pada sistem:

### 1. Masalah Upload di macOS (Termios Error)
*   **Masalah**: Flashing firmware pada macOS seringkali mengalami kegagalan `termios.error: (22, 'Invalid argument')` karena *driver* serial USB tidak mendukung penggantian kecepatan baud secara dinamis oleh `esptool.py`.
*   **Solusi**: Kecepatan unggah dikunci secara stabil pada **`upload_speed = 115200`** di dalam `platformio.ini` untuk lingkungan `esp32dev`.

### 2. Jaringan & Koneksi HTTPS (Bypass SSL)
*   **Masalah**: ESP32 menggunakan koneksi aman HTTPS (SSL) untuk berkomunikasi dengan Supabase. Koneksi bawaan `HTTPClient` sering memakan RAM hingga 40KB+ dan rentan gagal melakukan jabat tangan (SSL Handshake).
*   **Solusi**: Dirombak menggunakan `WiFiClientSecure` manual dengan instruksi `client.setInsecure()`. Ini memangkas *overhead* validasi sertifikat Let's Encrypt secara total, membuat lalu lintas data menjadi super ringan dan kebal dari penyakit *hang*.

### 3. Pencegahan Tabrakan Internet ESP32 (Deadlock)
*   **Masalah**: ESP32 memiliki dua inti prosesor (Dual-Core). Meminta data ke Supabase di *background* sambil melakukan Tap Kartu secara bersamaan akan membuat *network stack* LwIP bertabrakan.
*   **Solusi**: Kita memisahkan tugas *Polling* slot kosong ke **Core 0**, sedangkan *loop* pembacaan sensor ultrasonik dan RFID di **Core 1**. Sebagai pengaman jalurnya, digunakan sistem penguncian **FreeRTOS Mutex** (`httpMutex`). Kini Core 0 dan Core 1 bergantian secara rapi saat mengirim *request* HTTP.

### 4. Optimasi Memori RAM (Heap) & Jarak Threshold
*   **Arus & Memori**: Komunikasi HTTP dengan Supabase dioptimalkan untuk mencegah fragmentasi RAM di ESP32. Proses HTTP *request* diselesaikan *sebelum* servo berputar untuk menjaga chip WiFi dari kejutan penurunan tegangan (*voltage dip*).
*   **Sensor Jarak**: Deteksi kendaraan menggunakan sistem **Baseline Deviation**, di mana pintu akan merespons jika jarak pembacaan sensor berubah lebih dari 1 cm dari jarak lantai/baseline default (`abs(dist - g.defaultDist) > 1`). Ini jauh lebih adaptif terhadap fluktuasi sensor daripada sekadar batas statis.

---

## 📝 Catatan
Proyek ini dikembangkan untuk keperluan akademis dalam perancangan sistem parkir modern berbasis IoT dan Computer Vision.

