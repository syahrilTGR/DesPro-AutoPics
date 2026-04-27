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
-   Buat virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # (Mac/Linux)
    ```
-   Instal dependensi:
    ```bash
    pip install opencv-python numpy requests torch firebase-admin
    ```
-   Letakkan file kredensial Firebase Anda di `python/key.json`.
-   Jalankan engine:
    ```bash
    python python/y.py
    ```

---

## ⚙️ Konfigurasi ROI (Slot Parkir)
Anda dapat mengatur koordinat slot parkir langsung melalui file `slots_esp32.json`. Sistem akan secara otomatis melakukan monitoring pada area yang telah didefinisikan tersebut.

---

## 📝 Catatan
Proyek ini dikembangkan untuk keperluan akademis dalam perancangan sistem parkir modern berbasis IoT dan Computer Vision.
