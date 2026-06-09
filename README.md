# 🚗 AutoPics (Automated Parking System)

**Sistem Inteligensi Parkir Terintegrasi IoT, Computer Vision, dan Ekosistem Cloud.**

AutoPics adalah solusi manajemen parkir pintar yang menggabungkan efisiensi hardware **ESP32**, kekuatan deteksi visual **Python (OpenCV)**, dan sinkronisasi real-time **Firebase**. Sistem ini mengotomatisasi pemantauan slot parkir tanpa memerlukan sensor fisik di setiap slot, melainkan menggunakan kamera sebagai mata cerdas.

---

## 🚀 Fitur Unggulan (Optimized)

Sistem ini telah dioptimasi untuk performa maksimal pada perangkat edge:

-   **📡 Smart Discovery**: Python secara otomatis mencari IP ESP32-CAM via UDP Beacon. Jika koneksi terputus, ESP32 akan kembali berteriak (Beacon) secara otomatis setelah 10 detik.
-   **💾 IP Memory Fallback**: Python mengingat IP terakhir yang berhasil terkoneksi (`last_ip.txt`), memastikan koneksi instan meskipun discovery gagal.
-   **⚡ Stable HTTP Streaming**: Menggunakan metode *Keep-Alive* yang jauh lebih stabil daripada TCP Push konvensional, mencegah "buffer bloat" dan lag.
-   **📉 Dynamic FPS Limiter**: Dibatasi pada **5 FPS** secara presisi di sisi client untuk menjaga suhu ESP32 tetap dingin dan menghemat bandwidth tanpa mengorbankan akurasi deteksi.
-   **🔥 Firebase Real-time Sync**: Status slot parkir diupdate secara instan ke cloud dan dapat dipantau langsung via aplikasi mobile.

---

## 🏗️ Arsitektur Sistem

1.  **Main Controller (ESP32)**: Mengontrol gerbang fisik (Servo), sensor ultrasonik, dan pembaca RFID (RC522).
2.  **Visual Monitoring (ESP32-CAM)**: Melakukan streaming visual area parkir secara efisien.
3.  **Vision Engine (Python & OpenCV)**: Unit pemrosesan AI yang melakukan deteksi okupansi slot parkir menggunakan metode **Region of Interest (ROI)**.
4.  **Cloud Backend (Firebase)**: Pusat data untuk status slot, saldo pengguna, dan riwayat parkir.
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
-   *(Opsional)* Anda dapat memasukkan Web API Key Firebase Anda langsung ke dalam baris kode di `python/y.py` agar sistem dapat login secara resmi.
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

### 2. Jaringan & Koneksi NTP (Penting untuk SSL)
*   **Masalah**: ESP32 menggunakan koneksi aman HTTPS (SSL) untuk berkomunikasi dengan Firebase. Agar jabat tangan SSL (*SSL Handshake*) berhasil, waktu internal ESP32 harus sinkron dengan waktu nyata internet. Jika sinkronisasi NTP gagal, koneksi SSL akan ditolak oleh Firebase (Error: `Failed to initialize the SSL layer`).
*   **Solusi**: ESP32 diprogram menggunakan server lokal **`id.pool.ntp.org`** dan memblokir booting secara aman sampai waktu terverifikasi sinkron. Jika Anda mengalami hambatan atau titik-titik `NTP Sync...` yang lama, pastikan untuk **menghubungkan ESP32 ke Hotspot/Tethering HP Anda** (karena provider seluler tidak memblokir port UDP 123 untuk NTP).

### 3. Pemisahan Jalur Data Firebase (Stream vs Query)
*   **Solusi**: Koneksi *Streaming* di latar belakang menggunakan objek data terdedikasi **`streamFbdo`**, sedangkan operasi *Get/Set* (baca saldo & tulis status) menggunakan objek **`fbdo`**. Pemisahan ini mencegah terputusnya pemantauan slot parkir asinkron secara tiba-tiba ketika kartu RFID ditap.

### 4. Optimasi Memori RAM (Heap) & Jarak Threshold
*   **Arus & Memori**: Memori buffer respons Firebase dibatasi sebesar **1KB** (`setResponseSize(1024)`) untuk mencegah fragmentasi RAM di ESP32. Urutan penulisan Firebase diselesaikan *sebelum* servo berputar untuk menjaga chip WiFi dari kejutan penurunan tegangan (*voltage dip*).
*   **Sensor Jarak**: Batas jarak pemicu sensor ultrasonik miniatur diatur pada **$\le$ 3 cm**.

---

## 📝 Catatan
Proyek ini dikembangkan untuk keperluan akademis dalam perancangan sistem parkir modern berbasis IoT dan Computer Vision.

