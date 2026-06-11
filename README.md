# 🚗 AutoPics (Automated Parking System)

**Sistem Inteligensi Parkir Terintegrasi IoT, Computer Vision, dan Ekosistem Cloud.**

AutoPics adalah solusi manajemen parkir pintar yang menggabungkan efisiensi hardware **ESP32**, kekuatan deteksi visual **Python (OpenCV)**, dan sinkronisasi real-time **Supabase (PostgreSQL)**. Sistem ini mengotomatisasi pemantauan slot parkir tanpa memerlukan sensor fisik di setiap slot, melainkan menggunakan kamera sebagai mata cerdas.

---

## 🚀 Fitur Unggulan (Optimized)

Sistem ini telah dioptimasi untuk performa maksimal pada perangkat edge:

-   **📡 Smart Discovery**: Python secara otomatis mencari IP ESP32-CAM via UDP Beacon. Jika koneksi terputus, ESP32 akan kembali berteriak (Beacon) secara otomatis setelah 10 detik.
-   **💾 IP Memory Fallback**: Python mengingat IP terakhir yang berhasil terkoneksi (`last_ip.txt`), memastikan koneksi instan meskipun discovery gagal.
-   **⚡ Stable HTTP Streaming**: Menggunakan metode *Keep-Alive* yang jauh lebih stabil daripada TCP Push konvensional, mencegah "buffer bloat" dan lag.
-   **📉 Dynamic FPS Limiter**: Dibatasi pada **5 FPS** secara presisi di sisi client untuk menjaga suhu ESP32 tetap dingin dan menghemat bandwidth tanpa mengorbankan akurasi deteksi.
-   **🔥 Supabase Cloud Sync**: Status slot parkir diupdate secara instan ke cloud via REST API dan dapat dipantau langsung via aplikasi mobile.

---

## 🏗️ Arsitektur Sistem

1.  **Main Controller (ESP32)**: Mengontrol gerbang fisik (Servo), sensor ultrasonik, dan pembaca RFID (RC522).
2.  **Visual Monitoring (ESP32-CAM)**: Melakukan streaming visual area parkir secara efisien.
3.  **Vision Engine (Python & OpenCV)**: Unit pemrosesan AI yang melakukan deteksi okupansi slot parkir menggunakan metode **Region of Interest (ROI)**.
4.  **Cloud Backend (Supabase)**: Pusat data relasional (PostgreSQL) untuk status slot, entitas pengguna, dan pencatatan riwayat parkir.
5.  **Mobile App**: Dashboard interaktif untuk pengguna mencari tempat parkir kosong.

---

## 🛠️ Instalasi & Persiapan

### 1. ESP32-CAM (Vision Firmware)
-   Buka folder proyek di **PlatformIO**.
-   **Upload Command**:
    -   *Standard*: `pio run -e esp32cam -t upload`
    -   *Windows*: `%USERPROFILE%\.platformio\penv\Scripts\pio run -e esp32cam -t upload`
    -   *Mac*: `~/.platformio/penv/bin/pio run -e esp32cam -t upload`

### 2. ESP32 Gate Controller (Physical Firmware)
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
-   *(Opsional)* Anda dapat memasukkan API Key Supabase Anda langsung ke dalam baris kode di `python/y.py` agar sistem dapat login secara resmi.
-   Jalankan engine:
    ```bash
    python python/y.py
    ```

---

## ⚙️ Konfigurasi ROI (Slot Parkir)
Anda dapat mengatur koordinat slot parkir langsung melalui file `slots_esp32.json`. Sistem akan secara otomatis melakukan monitoring pada area yang telah didefinisikan tersebut.

---

## 🛠️ Catatan Khusus Pengembang & Pemecahan Masalah

Untuk memastikan kelancaran pengembangan di masa depan, berikut adalah beberapa poin optimasi penting yang telah diterapkan pada sistem:

### 1. Masalah Upload di macOS (Termios Error)
*   **Masalah**: Flashing firmware pada macOS seringkali mengalami kegagalan `termios.error: (22, 'Invalid argument')` karena *driver* serial USB tidak mendukung penggantian kecepatan baud secara dinamis oleh `esptool.py`.
*   **Solusi**: Kecepatan unggah dikunci secara stabil pada **`upload_speed = 115200`** di dalam `platformio.ini` untuk lingkungan `esp32dev` dan `esp32cam`.

### 2. Jaringan & Koneksi HTTPS (Bypass SSL)
*   **Masalah**: ESP32 menggunakan koneksi aman HTTPS (SSL) untuk berkomunikasi dengan Supabase. Koneksi bawaan `HTTPClient` sering memakan RAM hingga 40KB+ dan rentan gagal melakukan jabat tangan (SSL Handshake).
*   **Solusi**: Dirombak menggunakan `WiFiClientSecure` manual dengan instruksi `client.setInsecure()`. Ini memangkas *overhead* validasi sertifikat Let's Encrypt secara total, membuat lalu lintas data menjadi super ringan dan kebal dari penyakit *hang*.

### 3. Pencegahan Tabrakan Internet ESP32 (Deadlock)
*   **Masalah**: ESP32 memiliki dua inti prosesor (Dual-Core). Meminta data ke Supabase di *background* sambil melakukan Tap Kartu secara bersamaan akan membuat *network stack* LwIP bertabrakan.
*   **Solusi**: Kita memisahkan tugas *Polling* slot kosong ke **Core 0**, sedangkan *loop* pembacaan sensor ultrasonik dan RFID di **Core 1**. Sebagai pengaman jalurnya, digunakan sistem penguncian **FreeRTOS Mutex** (`httpMutex`). Kini Core 0 dan Core 1 bergantian secara rapi saat mengirim *request* HTTP.

### 4. Optimasi Memori RAM (Heap) & Jarak Threshold
*   **Arus & Memori**: Memori buffer respons Firebase dibatasi sebesar **1KB** (`setResponseSize(1024)`) untuk mencegah fragmentasi RAM di ESP32. Urutan penulisan Firebase diselesaikan *sebelum* servo berputar untuk menjaga chip WiFi dari kejutan penurunan tegangan (*voltage dip*).
*   **Sensor Jarak**: Batas jarak pemicu sensor ultrasonik miniatur diatur pada **$\le$ 3 cm**.

---

## 📝 Catatan
Proyek ini dikembangkan untuk keperluan akademis dalam perancangan sistem parkir modern berbasis IoT dan Computer Vision.

