# 📘 Buku Panduan Operasional AutoPics
**Automated Parking System — Sistem Inteligensi Parkir Terintegrasi IoT & Computer Vision**

> Versi Dokumen: 1.0  
> Terakhir Diperbarui: 13 Juni 2026  
> Penulis: Tim Pengembang AutoPics

---

## Daftar Isi

1. [Pendahuluan](#bab-1-pendahuluan)
2. [Arsitektur Sistem](#bab-2-arsitektur-sistem)
3. [Perakitan Hardware & Wiring](#bab-3-perakitan-hardware--wiring)
4. [Instalasi & Konfigurasi Software](#bab-4-instalasi--konfigurasi-software)
5. [SOP Operasional Harian](#bab-5-sop-operasional-harian)
6. [Struktur Database & API](#bab-6-struktur-database--api)
7. [Panduan Pengujian Komponen](#bab-7-panduan-pengujian-komponen)
8. [Troubleshooting & FAQ](#bab-8-troubleshooting--faq)
9. [Referensi Teknis (Lampiran)](#bab-9-referensi-teknis-lampiran)

---

# BAB 1: Pendahuluan

## 1.1 Latar Belakang

AutoPics (*Automated Parking System*) adalah solusi manajemen parkir pintar yang dirancang untuk mengatasi inefisiensi pada sistem parkir konvensional. Sistem ini menggabungkan teknologi **Internet of Things (IoT)** dan **Computer Vision** untuk mengotomatisasi seluruh proses parkir — mulai dari deteksi ketersediaan lokasi, otentikasi identitas pengguna, hingga perhitungan biaya parkir secara otomatis.

Keunggulan utama AutoPics dibanding sistem konvensional:
- **Tanpa sensor fisik di setiap slot** — cukup 1 kamera untuk mengawasi seluruh area parkir.
- **Pembayaran otomatis** — saldo dipotong saat kendaraan keluar tanpa intervensi petugas.
- **Monitoring real-time** — status slot dapat dipantau kapan saja melalui dashboard.

## 1.2 Ruang Lingkup Buku Panduan

Buku ini ditujukan untuk **operator** yang bertanggung jawab menjalankan dan memelihara sistem AutoPics sehari-hari. Setelah membaca panduan ini, operator diharapkan mampu:

- Menyalakan dan mematikan sistem dengan benar
- Melakukan kalibrasi slot parkir pada Vision Engine
- Memahami alur kendaraan masuk dan keluar
- Mengatasi masalah umum yang terjadi di lapangan
- Melakukan pengujian komponen jika diperlukan

## 1.3 Konvensi yang Digunakan

| Simbol | Arti |
|--------|------|
| ⚠️ | Peringatan penting — harap diperhatikan |
| ✅ | Langkah berhasil / status OK |
| ❌ | Error / langkah gagal |
| 💡 | Tips / saran tambahan |
| 🔧 | Tindakan teknis yang perlu dilakukan |
| `teks seperti ini` | Perintah yang perlu diketik di terminal/komputer |

## 1.4 Daftar Komponen Sistem

### Hardware

| No | Komponen | Jumlah | Fungsi |
|----|----------|--------|--------|
| 1 | ESP32 DevKit C V4 | 1 unit | Otak pengontrol gerbang (Gate Controller) |
| 2 | ESP32-CAM (AI-Thinker) | 1 unit | Kamera pengawas area parkir |
| 3 | Sensor Ultrasonik HC-SR04 | 3 unit | Deteksi kendaraan di depan gerbang |
| 4 | Modul RFID MFRC522 | 3 unit | Pembaca kartu identitas pengguna |
| 5 | Micro Servo Motor | 3 unit | Penggerak palang pintu gerbang |
| 6 | Kartu RFID / Tag NFC | 4+ buah | Kartu identitas pengguna |
| 7 | Breadboard & Kabel Jumper | Secukupnya | Koneksi antar komponen |
| 8 | Adaptor 5V / USB Power | 2 unit | Catu daya untuk kedua ESP32 |

### Software

| No | Software | Versi | Fungsi |
|----|----------|-------|--------|
| 1 | PlatformIO (VS Code) | Terbaru | Upload firmware ke ESP32 |
| 2 | Python | 3.10+ | Menjalankan Vision Engine |
| 3 | OpenCV | Terbaru | Library pengolahan citra |
| 4 | PyTorch (opsional) | Terbaru | Akselerasi GPU untuk deteksi |
| 5 | Supabase | Cloud | Database backend (PostgreSQL) |

---

# BAB 2: Arsitektur Sistem

> [!WARNING]
> **Vision Engine - Status Belum Stabil**
> Vision Engine saat ini masih menggunakan metode ROI Thresholding yang sangat sensitif terhadap perubahan cahaya. Sistem sedang dalam proses migrasi ke YOLOv8 + ByteTrack untuk deteksi yang lebih robust. Detail lengkap di: [REVISI_VISION_ENGINE_PLAN.md](file:///Volumes/Data%20Shared/Project/despro%20AutoPics/REVISI_VISION_ENGINE_PLAN.md).

## 2.1 Lima Pilar Teknologi

Sistem AutoPics dibangun di atas lima komponen utama yang bekerja secara terintegrasi:

### Pilar 1 — Main Controller (ESP32 Gate Controller)

ESP32 bertindak sebagai **otak mekanis** di gerbang parkir. Perangkat ini mengontrol:
- **3 sensor ultrasonik**: mendeteksi keberadaan kendaraan di depan gerbang masuk motor, masuk mobil, dan keluar.
- **3 modul RFID**: membaca kartu identitas pengguna di setiap gerbang.
- **3 servo motor**: membuka/menutup palang pintu berdasarkan validasi.

ESP32 terhubung ke internet via WiFi dan berkomunikasi langsung dengan database Supabase untuk:
- Memverifikasi kartu RFID dan saldo pengguna
- Mencatat waktu masuk dan keluar kendaraan
- Mengecek ketersediaan slot parkir

### Pilar 2 — Visual Streamer (ESP32-CAM)

ESP32-CAM adalah modul kamera nirkabel yang diletakkan di **posisi strategis atas** untuk mengawasi seluruh area parkir. Perangkat ini:
- Menyiarkan gambar area parkir melalui HTTP server lokal (port 80)
- Mendukung 3 resolusi: rendah (320×240), sedang (640×480), tinggi (800×600)
- Mengirim sinyal UDP Beacon secara otomatis agar Vision Engine dapat menemukan IP-nya

### Pilar 3 — Vision Engine (Python + OpenCV)

Vision Engine adalah program Python yang berjalan di **komputer/PC server**. Program ini:
- Menerima streaming gambar dari ESP32-CAM
- Menganalisis setiap slot parkir menggunakan metode **Region of Interest (ROI)**
- Mendeteksi apakah slot terisi atau kosong berdasarkan perubahan visual
- Mengirimkan hasil deteksi ke database Supabase secara real-time

### Pilar 4 — Cloud Backend (Supabase)

Supabase adalah pusat sinkronisasi data berbasis PostgreSQL yang menangani:
- Status real-time setiap slot parkir (terisi/kosong)
- Informasi akun pengguna (nama, kartu RFID, saldo)
- Catatan riwayat parkir (waktu masuk, keluar, durasi, biaya)
- Transaksi top-up saldo

### Pilar 5 — Mobile Application *(dalam pengembangan)*

Aplikasi mobile yang akan menyediakan:
- Dashboard statistik slot kosong/terisi
- Peta parkir interaktif (slot hijau = kosong, merah = terisi)
- Pusat pembayaran dan riwayat transaksi

> 💡 **Catatan**: Aplikasi mobile sedang dalam proses migrasi backend dan belum tersedia pada versi ini.

## 2.2 Konsep Sistem Hybrid

AutoPics menerapkan arsitektur **Hybrid** yang membagi tugas secara cerdas:

| Aspek | Ditangani Oleh | Cara Kerja |
|-------|----------------|------------|
| **Keamanan & Akses** | RFID (ESP32 Gate) | Otentikasi kartu, validasi saldo, catat waktu masuk/keluar |
| **Deteksi Slot** | Kamera (Vision Engine) | Analisis visual ROI untuk menentukan slot terisi/kosong |
| **Sinkronisasi Data** | Supabase Cloud | Menjembatani semua komponen secara real-time |

**Mengapa Hybrid?**
- ESP32 Gate **hanya mengetahui** siapa yang masuk/keluar dan kapan, tetapi **tidak tahu** di slot mana kendaraan diparkir.
- Vision Engine **hanya mengetahui** slot mana yang terisi/kosong, tetapi **tidak tahu** siapa pemilik kendaraannya.
- Supabase **menyatukan kedua informasi** tersebut menjadi gambaran lengkap.

## 2.3 Alur Data Real-Time

Berikut alur data saat sistem berjalan:

1. **Vision Loop** (berjalan terus-menerus):
   - ESP32-CAM → kirim gambar → Python Vision Engine → analisis ROI → update status slot di Supabase

2. **Alur Masuk** (saat kendaraan datang):
   - Sensor ultrasonik deteksi kendaraan → pengguna tap RFID → ESP32 cek saldo & slot kosong di Supabase → gerbang buka → catat waktu masuk

3. **Alur Keluar** (saat kendaraan pergi):
   - Sensor ultrasonik deteksi kendaraan → pengguna tap RFID → ESP32 hitung durasi & biaya → potong saldo → gerbang buka

---

# BAB 3: Perakitan Hardware & Wiring

## 3.1 Sensor RFID RC522 (3 Unit — SPI Paralel)

Ketiga sensor RFID dihubungkan secara **paralel** menggunakan jalur bus SPI yang sama, dengan pin SS (SDA) berbeda untuk memisahkan pembacaan data.

### Jalur Bersama (Shared Bus)

| Fungsi SPI | Pin ESP32 (GPIO) | Keterangan |
|------------|------------------|------------|
| SCK | **18** | Clock SPI bersama |
| MISO | **19** | Master In Slave Out bersama |
| MOSI | **23** | Master Out Slave In bersama |
| RST | **4** | Reset bersama untuk ketiga modul |

### Pin SS (Slave Select) — Unik per Modul

| Sensor RFID | Lokasi Gerbang | Pin SS (GPIO) |
|-------------|----------------|---------------|
| RFID 1 | Pintu Masuk Motor | **21** |
| RFID 2 | Pintu Masuk Mobil | **22** |
| RFID 3 | Pintu Keluar | **25** |

> ⚠️ **Penting**: VCC modul RFID RC522 **wajib** dihubungkan ke tegangan **3.3V**. Jangan hubungkan ke 5V karena akan merusak modul!

## 3.2 Sensor Ultrasonik HC-SR04 (3 Unit)

| Sensor | Lokasi Gerbang | Pin TRIG (GPIO) | Pin ECHO (GPIO) |
|--------|----------------|-----------------|-----------------|
| Ultrasonik 1 | Pintu Masuk Motor | **32** | **33** |
| Ultrasonik 2 | Pintu Masuk Mobil | **27** | **26** |
| Ultrasonik 3 | Pintu Keluar | **16** | **17** |

> 💡 Sensor ultrasonik memerlukan tegangan **5V** untuk VCC.

## 3.3 Servo Motor (3 Unit — Palang Pintu)

| Servo | Fungsi | Pin PWM (GPIO) |
|-------|--------|----------------|
| Servo 1 | Palang Masuk Motor | **13** |
| Servo 2 | Palang Masuk Mobil | **12** |
| Servo 3 | Palang Keluar | **14** |

> 💡 Servo motor memerlukan tegangan **5V**. Disarankan menggunakan **adaptor eksternal 5V** terpisah agar torsi servo stabil dan tidak mengganggu chip WiFi ESP32.

## 3.4 Catatan Catu Daya

| Komponen | Tegangan | Sumber |
|----------|----------|--------|
| Modul RFID RC522 | **3.3V** | Pin 3.3V ESP32 |
| Sensor Ultrasonik | **5V** | Pin 5V ESP32 atau adaptor eksternal |
| Servo Motor | **5V** | **Adaptor eksternal 5V** (rekomendasi) |
| ESP32 DevKit | 5V via USB | Kabel USB / adaptor |
| ESP32-CAM | 5V via USB | Kabel USB / adaptor |

> ⚠️ **Wajib**: Semua ground (GND) dari seluruh modul harus terhubung bersama ke pin **GND** ESP32 (*Common Ground*). Jika tidak, komunikasi data akan gagal.

## 3.5 ESP32-CAM (Kamera)

ESP32-CAM menggunakan board **AI-Thinker** dengan pin bawaan:

| Pin | Fungsi | Keterangan |
|-----|--------|------------|
| GPIO 33 | LED Merah Indikator | Active Low (LOW = nyala, HIGH = mati) |
| GPIO 4 | LED Flash / Senter Depan | Active High, dikontrol via PWM |

> 💡 ESP32-CAM tidak memerlukan komponen eksternal tambahan. Cukup sambungkan catu daya 5V dan antena WiFi (sudah terintegrasi di board).

---

# BAB 4: Instalasi & Konfigurasi Software

## 4.1 Persiapan Awal

Sebelum memulai, pastikan software berikut sudah terinstal di komputer:

1. **Visual Studio Code** — Editor kode (unduh di https://code.visualstudio.com)
2. **PlatformIO Extension** — Plugin untuk VS Code yang digunakan untuk upload firmware ke ESP32
3. **Python 3.10 atau lebih baru** — Untuk menjalankan Vision Engine
4. **Driver USB Serial** — Biasanya terinstal otomatis, tetapi jika ESP32 tidak terdeteksi, instal driver CH340 atau CP2102 sesuai board

## 4.2 Upload Firmware ESP32 Gate Controller

Firmware Gate Controller adalah program yang berjalan di ESP32 untuk mengontrol gerbang (RFID, sensor, servo).

### Langkah-langkah:

1. Hubungkan ESP32 DevKit ke komputer via kabel USB
2. Buka folder proyek AutoPics di VS Code
3. Buka terminal dan jalankan perintah upload:

   **Perintah standar:**
   ```
   pio run -e esp32dev -t upload
   ```

   **Untuk macOS (jika perintah standar tidak ditemukan):**
   ```
   ~/.platformio/penv/bin/pio run -e esp32dev -t upload
   ```

   **Untuk Windows PowerShell:**
   ```
   & "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e esp32dev -t upload
   ```

4. Tunggu proses upload selesai (ditandai dengan pesan `SUCCESS`)

### Konfigurasi WiFi (Pertama Kali):

Saat pertama kali dinyalakan, ESP32 Gate akan membuat jaringan WiFi sendiri bernama **`AutoPics_Gate_AP`**:
1. Hubungkan HP/laptop ke WiFi `AutoPics_Gate_AP`
2. Browser akan otomatis membuka halaman konfigurasi
3. Pilih jaringan WiFi yang tersedia dan masukkan password
4. ESP32 akan restart dan terhubung ke jaringan tersebut

> 💡 **Cara Reset WiFi**: Jika ingin mengganti jaringan WiFi, tekan **tombol BOOT** di ESP32 selama **3 detik**, atau ketik perintah `reswi` di Serial Monitor.

## 4.3 Upload Firmware ESP32-CAM

1. Hubungkan ESP32-CAM ke komputer via kabel USB (atau USB-to-TTL adapter)
2. Jalankan perintah upload:

   **Perintah standar:**
   ```
   pio run -e esp32cam -t upload
   ```

   **Untuk macOS:**
   ```
   ~/.platformio/penv/bin/pio run -e esp32cam -t upload
   ```

   **Untuk Windows PowerShell:**
   ```
   & "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -e esp32cam -t upload
   ```

3. Tunggu proses upload selesai

### Konfigurasi WiFi ESP32-CAM:

Sama seperti Gate Controller, ESP32-CAM akan membuat WiFi bernama **`AutoPics_Cam_AP`** saat pertama kali dinyalakan. Ikuti langkah yang sama untuk menghubungkannya ke jaringan WiFi.

> ⚠️ **Penting**: ESP32 Gate dan ESP32-CAM **harus terhubung ke jaringan WiFi yang sama** agar Vision Engine dapat berkomunikasi dengan kamera.

## 4.4 Instalasi Python Vision Engine

> [!WARNING]
> **Status Vision Engine**
> Python Vision Engine versi saat ini (`y.py`) masih berstatus eksperimental (menggunakan metode *Thresholding* yang sensitif terhadap cahaya). Program ini dalam proses perombakan menjadi sistem tracking objek.

### Langkah 1: Buat Virtual Environment

Buka terminal di folder proyek AutoPics, lalu jalankan:

```bash
# Buat virtual environment (hanya sekali)
python -m venv venv

# Aktifkan virtual environment
# macOS / Linux:
source venv/bin/activate
# Windows Command Prompt:
venv\Scripts\activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### Langkah 2: Instal Dependensi

```bash
pip install -r requirements.txt
```

Jika ingin menggunakan **akselerasi GPU** (opsional, untuk performa lebih cepat):
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

### Langkah 3: Jalankan Vision Engine

```bash
python python/y.py
```

Program akan otomatis:
1. Mencari IP ESP32-CAM via **UDP Beacon** (metode utama)
2. Mencoba resolusi hostname via **mDNS** (cadangan)
3. Menggunakan **IP terakhir** yang tersimpan di `last_ip.txt` (fallback)

Jika berhasil terhubung, akan muncul jendela video menampilkan area parkir.

## 4.5 Setup Database Supabase

### Langkah 1: Buat Project Supabase

1. Buka https://supabase.com dan buat akun
2. Klik **New Project** dan pilih region terdekat
3. Catat **Project URL** dan **anon key** yang diberikan

### Langkah 2: Buat Tabel Database

1. Buka menu **SQL Editor** di dashboard Supabase
2. Copy-paste seluruh isi file `supabase_schema.sql` ke editor
3. Klik **Run** untuk membuat 5 tabel yang dibutuhkan

### Langkah 3: Isi Data Awal (Seeding)

Jalankan script seeder untuk membuat 4 pengguna demo beserta kartu RFID-nya:

```bash
python seed_test_data.py
```

Data yang dibuat:

| Nama | UID Kartu RFID | Saldo Awal | Tipe Kendaraan |
|------|----------------|------------|----------------|
| Awang | A9369711 | Rp 50.000 | Motor |
| Syahril | 19019211 | Rp 50.000 | Mobil |
| Refi | 09D97D11 | Rp 50.000 | Motor |
| Noval | 29900307 | Rp 50.000 | Mobil |

### Langkah 4: Update Konfigurasi di Source Code

Jika Anda menggunakan project Supabase sendiri, perbarui URL dan Key di dua file berikut:

**File `src/main.cpp` (baris 14-15):**
```cpp
#define SUPABASE_URL "https://XXXX.supabase.co"
#define SUPABASE_ANON_KEY "eyJhbGci..."
```

**File `python/y.py` (baris 86-87):**
```python
SUPABASE_URL = "https://XXXX.supabase.co"
SUPABASE_KEY = "eyJhbGci..."
```

> ⚠️ Setelah mengganti URL/Key di `main.cpp`, firmware ESP32 Gate harus di-upload ulang.

---

# BAB 5: SOP Operasional Harian

## 5.1 Prosedur Startup Sistem (Menyalakan)

Ikuti urutan berikut setiap kali memulai operasional:

| Langkah | Tindakan | Indikator Berhasil |
|---------|----------|-------------------|
| 1 | Nyalakan **adaptor 5V** (catu daya bersama untuk ESP32 Gate dan ESP32-CAM) | Kedua board menyala bersamaan |
| 2 | Tunggu ESP32-CAM terhubung WiFi | LED merah berkedip → kemudian mati (WiFi terhubung) |
| 3 | Tunggu **10–15 detik** hingga kedua ESP32 terhubung WiFi | — |
| 4 | Buka terminal di komputer server | — |
| 5 | Aktifkan virtual environment Python | Muncul `(venv)` di depan prompt terminal |
| 6 | Jalankan `python python/y.py` | Muncul jendela video area parkir |
| 7 | Pastikan kamera menampilkan seluruh area parkir | Gambar terlihat jelas dan tidak lag |

> 💡 Jika LED merah ESP32-CAM terus berkedip, artinya WiFi belum terhubung. Periksa jaringan WiFi atau lakukan konfigurasi ulang WiFi (lihat BAB 4.3).

## 5.2 Prosedur Kalibrasi Slot Parkir

> [!WARNING]
> **Catatan Penting:** Prosedur kalibrasi manual ini adalah kelemahan utama dari Vision Engine versi saat ini dan menjadikannya **belum stabil** untuk operasional jangka panjang. Prosedur ini akan dihapus setelah sistem bermigrasi ke metode YOLOv8 Object Tracking.

Kalibrasi **wajib dilakukan** setiap kali:
- Sistem pertama kali dijalankan
- Posisi kamera berubah
- Kondisi pencahayaan berubah drastis (pagi → malam)
- Hasil deteksi tidak akurat

### Langkah 1: Pastikan Semua Slot Kosong

Sebelum kalibrasi, **semua slot parkir harus dalam keadaan kosong** (tidak ada kendaraan yang terparkir).

### Langkah 2: Gambar Area Slot (Jika Belum Ada)

Jika slot belum didefinisikan:

1. Tekan tombol **`G`** (mode Gambar) pada keyboard
2. **Klik dan drag** mouse untuk menggambar kotak di area slot parkir
3. Setelah melepas mouse, akan muncul pilihan:
   - Tekan **`1`** untuk tipe **Mobil**
   - Tekan **`2`** untuk tipe **Motor**
   - Tekan **`Esc`** untuk membatalkan
4. Ulangi untuk semua slot yang perlu didefinisikan
5. Tekan **`N`** untuk kembali ke mode Normal

### Langkah 3: Kalibrasi Referensi

1. Pastikan semua slot **benar-benar kosong**
2. Tekan tombol **`C`** (Kalibrasi)
3. Tunggu hingga muncul pesan `✅ Kalibrasi selesai (X slot)`

### Langkah 4: Simpan Konfigurasi

Tekan **`S`** untuk menyimpan konfigurasi slot dan referensi kalibrasi ke file. Konfigurasi ini akan dimuat otomatis saat program dijalankan kembali.

### Langkah 5: Verifikasi

1. Letakkan kendaraan miniatur di salah satu slot
2. Tunggu beberapa detik
3. Kotak slot harus berubah dari **hijau (KOSONG)** menjadi **merah (TERISI)**
4. Angkat kendaraan, slot harus kembali hijau

## 5.3 Menghapus Slot yang Salah

1. Tekan **`H`** (mode Hapus)
2. Klik pada kotak slot yang ingin dihapus
3. Slot akan langsung terhapus dari tampilan dan database
4. Tekan **`N`** untuk kembali ke mode Normal

## 5.4 Alur Kendaraan Masuk

Berikut yang terjadi saat kendaraan masuk ke area parkir:

```
Kendaraan mendekat
       ↓
Sensor ultrasonik mendeteksi objek (< 15 cm)
       ↓
Pengguna menempelkan kartu RFID
       ↓
ESP32 memverifikasi ke Supabase:
  ├─ Apakah kartu terdaftar? ──── Jika TIDAK → ❌ Ditolak
  ├─ Apakah saldo ≥ Rp 5.000? ── Jika TIDAK → ❌ Ditolak  
  ├─ Apakah sudah parkir? ─────── Jika YA    → ❌ Ditolak (anti-passback)
  └─ Apakah ada slot kosong? ──── Jika TIDAK → ❌ Ditolak
       ↓ (Semua OK)
✅ Gerbang terbuka (servo 90°)
✅ Status pengguna berubah menjadi "PARKED"
✅ Waktu masuk dicatat
       ↓
Kendaraan melewati gerbang
       ↓
Gerbang menutup otomatis (1,5 detik setelah kendaraan lewat)
```

> ⚠️ Jika kendaraan tidak kunjung lewat setelah gerbang terbuka, gerbang akan menutup otomatis setelah **5 detik** (timeout).

## 5.5 Alur Kendaraan Keluar

```
Kendaraan mendekati pintu keluar
       ↓
Sensor ultrasonik mendeteksi objek
       ↓
Pengguna menempelkan kartu RFID
       ↓
ESP32 memverifikasi ke Supabase:
  ├─ Apakah status pengguna "PARKED"? ── Jika TIDAK → ❌ Ditolak
  └─ Apakah saldo cukup untuk bayar? ─── Jika TIDAK → ❌ Ditolak
       ↓ (OK)
Kalkulasi biaya parkir (lihat tabel tarif di bawah)
       ↓
✅ Saldo dipotong otomatis
✅ Gerbang keluar terbuka
✅ Status pengguna berubah menjadi "COMPLETED"
✅ Durasi dan biaya dicatat di riwayat parkir
```

### Tabel Tarif Parkir

| Tipe Kendaraan | Tarif Dasar (1 Jam Pertama) | Tarif Tambahan (Per Menit Setelah 1 Jam) |
|----------------|----------------------------|------------------------------------------|
| **Motor** | Rp 2.000 | Rp 30 / menit |
| **Mobil** | Rp 5.000 | Rp 80 / menit |

**Contoh perhitungan:**
- Motor parkir 45 menit → Biaya: **Rp 2.000** (masih dalam 1 jam pertama)
- Mobil parkir 1 jam 30 menit (90 menit) → Biaya: Rp 5.000 + (30 × Rp 80) = **Rp 7.400**

> 💡 **Durasi minimum**: Sistem akan menghitung minimal **1 menit** meskipun kendaraan keluar dalam hitungan detik.

## 5.6 Prosedur Shutdown (Mematikan)

| Langkah | Tindakan |
|---------|----------|
| 1 | Pada jendela Vision Engine, tekan **`Q`** untuk menutup program |
| 2 | Cabut catu daya **ESP32 Gate** |
| 3 | Cabut catu daya **ESP32-CAM** |

> 💡 Konfigurasi slot dan kalibrasi yang sudah disimpan (tekan `S`) tidak akan hilang saat sistem dimatikan. Data tersebut tersimpan di file `slots_esp32.json` dan `reference_esp32.npz`.

## 5.7 Mengatur Pencahayaan Kamera (Flash/Senter)

ESP32-CAM dilengkapi LED senter depan yang dapat diatur untuk kondisi pencahayaan rendah:

1. Tekan **`F`** pada jendela Vision Engine untuk berganti level senter
2. Level senter berputar secara siklis:

| Level | Kecerahan (PWM) | Keterangan |
|-------|-----------------|------------|
| 0 | 0 (mati) | Default, cahaya mati |
| 1 | 10 (redup) | Pencahayaan minimal |
| 2 | 50 (sedang) | Pencahayaan standar |
| 3 | 255 (maksimal) | Cahaya penuh |

## 5.8 Mengubah Resolusi Kamera

Jika koneksi lambat atau gambar kurang detail, resolusi kamera dapat diubah:

| Tombol | Resolusi | Ukuran | Keterangan |
|--------|----------|--------|------------|
| **3** | Rendah | 320 × 240 | Untuk koneksi lambat |
| **4** | Sedang | 640 × 480 | **Default** (rekomendasi) |
| **5** | Tinggi | 800 × 600 | Detail tinggi, butuh bandwidth lebih |

---

# BAB 6: Struktur Database & API

## 6.1 Tabel Database Supabase

Sistem menggunakan 5 tabel di database PostgreSQL (Supabase):

### Tabel 1: `users` — Data Pengguna

| Kolom | Tipe Data | Keterangan |
|-------|-----------|------------|
| `id` | UUID (Primary Key) | ID unik pengguna, digenerate otomatis |
| `name` | VARCHAR(255) | Nama lengkap pengguna |
| `balance` | NUMERIC | Saldo pengguna dalam Rupiah |
| `created_at` | TIMESTAMP | Waktu pendaftaran |

### Tabel 2: `rfid_cards` — Kartu RFID Terdaftar

| Kolom | Tipe Data | Keterangan |
|-------|-----------|------------|
| `uid` | VARCHAR(50) (Primary Key) | Kode UID kartu RFID (contoh: `A9369711`) |
| `user_id` | UUID (Foreign Key → users) | Pemilik kartu |
| `card_name` | VARCHAR(100) | Label kartu (contoh: "Kartu Awang") |
| `vehicle_type` | VARCHAR(20) | Tipe kendaraan: `Mobil` atau `Motor` |
| `created_at` | TIMESTAMP | Waktu pendaftaran kartu |

### Tabel 3: `parking_history` — Riwayat Parkir

| Kolom | Tipe Data | Keterangan |
|-------|-----------|------------|
| `id` | UUID (Primary Key) | ID transaksi unik |
| `rfid_uid` | VARCHAR(50) (FK → rfid_cards) | UID kartu yang digunakan |
| `time_in` | TIMESTAMP | Waktu masuk gerbang |
| `time_out` | TIMESTAMP | Waktu keluar gerbang (NULL jika masih parkir) |
| `duration_minutes` | NUMERIC | Durasi parkir dalam menit |
| `total_fee` | NUMERIC | Total biaya parkir dalam Rupiah |
| `status` | VARCHAR(20) | `PARKED` (sedang parkir) atau `COMPLETED` (sudah keluar) |

### Tabel 4: `transactions` — Buku Besar Transaksi (Top-Up, dll)

| Kolom | Tipe Data | Keterangan |
|-------|-----------|------------|
| `id` | UUID (Primary Key) | ID transaksi unik |
| `user_id` | UUID (FK → users) | Pengguna yang terkait transaksi |
| `amount` | NUMERIC | Jumlah nominal dalam Rupiah |
| `transaction_type`| VARCHAR(20) | Jenis transaksi (contoh: `TOPUP`) |
| `created_at` | TIMESTAMP | Waktu transaksi |

### Tabel 5: `parking_slots` — Status Slot Parkir

| Kolom | Tipe Data | Keterangan |
|-------|-----------|------------|
| `slot_id` | VARCHAR(20) (Primary Key) | ID slot (contoh: `A1`, `B3`) |
| `status` | VARCHAR(20) | `EMPTY` (kosong) atau `FULL` (terisi) |
| `last_updated` | TIMESTAMP | Waktu terakhir status diperbarui |

## 6.2 Hubungan Antar Tabel

```
users (1) ──────── (N) rfid_cards
                        │
                        │ (1)
                        │
                        (N) parking_history

users (1) ──────── (N) transactions

parking_slots (berdiri sendiri, diupdate oleh Vision Engine)
```

- Satu **pengguna** bisa memiliki **banyak kartu RFID**
- Satu **kartu RFID** bisa memiliki **banyak riwayat parkir**
- Satu **pengguna** bisa memiliki **banyak catatan transaksi (mis. top-up)**
- Tabel **parking_slots** tidak terhubung langsung ke tabel lain — dikelola sepenuhnya oleh Vision Engine

## 6.3 Contoh Alur Data API

### Saat Kendaraan Masuk:

1. **GET** `/rest/v1/rfid_cards?uid=eq.A9369711&select=user_id,vehicle_type,users(balance)`  
   → Mengecek apakah kartu terdaftar dan berapa saldonya

2. **GET** `/rest/v1/parking_history?rfid_uid=eq.A9369711&status=eq.PARKED`  
   → Mengecek apakah kendaraan ini sudah sedang parkir (anti-passback)

3. **GET** `/rest/v1/parking_slots?status=eq.EMPTY&select=slot_id`  
   → Menghitung berapa slot yang masih kosong

4. **POST** `/rest/v1/parking_history`  
   → Mencatat data masuk: UID, status "PARKED", waktu masuk

### Saat Kendaraan Keluar:

1. **GET** `/rest/v1/parking_history?rfid_uid=eq.A9369711&status=eq.PARKED`  
   → Mengambil data sesi parkir aktif (waktu masuk, saldo)

2. **PATCH** `/rest/v1/users?id=eq.{user_id}`  
   → Mengurangi saldo pengguna setelah kalkulasi biaya

3. **PATCH** `/rest/v1/parking_history?id=eq.{history_id}`  
   → Memperbarui riwayat: waktu keluar, durasi, biaya, status "COMPLETED"

---

# BAB 7: Panduan Pengujian Komponen

## 7.1 Uji Coba Sensor RFID (3 Modul Sekaligus)

Gunakan firmware test khusus untuk memverifikasi bahwa ketiga sensor RFID bekerja dengan benar:

1. Upload firmware test RFID:
   ```
   pio run -e test_rfid -t upload
   ```

2. Buka Serial Monitor:
   ```
   pio device monitor
   ```
   Atau untuk macOS dengan port spesifik:
   ```
   ~/.platformio/penv/bin/pio device monitor -p /dev/cu.usbserial-0001 -b 115200
   ```

3. Tempelkan kartu RFID ke masing-masing sensor secara bergantian

4. **Hasil yang diharapkan**:
   ```
   🎯 [RFID MOTOR_IN] Terbaca! | 💳 UID: A9369711
   🎯 [RFID MOBIL_IN] Terbaca! | 💳 UID: 19019211
   🎯 [RFID EXIT_ALL] Terbaca! | 💳 UID: 09D97D11
   ```

> ⚠️ Jika salah satu sensor menampilkan `Firmware Version: 0x00` saat inisialisasi, periksa kembali koneksi kabel SPI dan pastikan pin SS sudah benar.

## 7.2 Uji Coba Sensor Ultrasonik (3 Sensor)

1. Upload firmware test ultrasonik:
   ```
   pio run -e test_ultrasonic -t upload
   ```

2. Buka Serial Monitor

3. Letakkan dan jauhkan objek dari depan masing-masing sensor

4. **Hasil yang diharapkan**:
   ```
   =========================================
   📡 MOTOR_IN (Ultrasonik 1): 25 cm
   📡 MOBIL_IN (Ultrasonik 2): 8 cm
   📡 EXIT_ALL (Ultrasonik 3): 2 cm  [ 🚨 OBJEK TERDETEKSI! <= 2 CM ]
   ```

> 💡 Threshold deteksi pada firmware test adalah **2 cm**. Pada firmware utama (Gate Controller), threshold yang digunakan adalah **15 cm**.

## 7.3 Verifikasi Koneksi Database

Jalankan script untuk mengecek data terakhir di Supabase:

```bash
python check_db.py
```

**Hasil yang diharapkan**:
```
--- RIWAYAT PARKIR TERBARU ---
{
  "id": "...",
  "rfid_uid": "19019211",
  "time_in": "2026-06-13T...",
  ...
}

--- SALDO USER (UID 19019211) ---
Nama: Syahril | Saldo Saat Ini: Rp 50000
```

## 7.4 Reset Database ke Kondisi Awal

Jika data sudah berantakan atau ingin memulai dari awal saat demo:

```bash
python reset_db.py
```

Script ini akan:
1. Menghapus seluruh riwayat parkir (`parking_history`)
2. Mereset saldo semua pengguna ke **Rp 50.000**

> ⚠️ **Hati-hati**: Script ini menghapus semua data riwayat parkir secara permanen!

## 7.5 Monitor Serial ESP32 (Live Debugging)

Untuk melihat log aktivitas ESP32 secara real-time:

**ESP32 Gate Controller:**
```
pio device monitor
```
Atau dengan port spesifik (macOS):
```
~/.platformio/penv/bin/pio device monitor -p /dev/cu.usbserial-0001 -b 115200
```

**ESP32-CAM:**
```
~/.platformio/penv/bin/pio device monitor -p /dev/cu.usbserial-A5069RR4 -b 115200
```

**Contoh output log ESP32 Gate saat beroperasi normal:**
```
🔍 Heap: 180224 B | Slot Kosong: 12 | Jarak(MTR,MBL,EXT): 25,30,999 cm
📡 Kartu di MOTOR_IN! UID: A9369711
🔄 Mencatat histori masuk ke Supabase...
✅ Entrance Sukses. UID: A9369711, Saldo: Rp 50000
🚀 MOTOR_IN: OPEN
🔒 MOTOR_IN: CLOSE (Lewat)
```

---

# BAB 8: Troubleshooting & FAQ

## 8.1 Tabel Masalah Umum & Solusi

### Masalah Hardware

| No | Masalah | Kemungkinan Penyebab | Solusi |
|----|---------|---------------------|--------|
| 1 | **Kartu RFID tidak terbaca** di salah satu sensor | Koneksi kabel SPI longgar, atau bus SPI collision | Periksa sambungan kabel. Pastikan semua pin SS di-set HIGH sebelum inisialisasi. Coba test dengan firmware `test_rfid`. |
| 2 | **Sensor ultrasonik selalu menunjukkan 999 cm** | Kabel TRIG/ECHO tertukar atau sensor rusak | Periksa pin TRIG dan ECHO. Coba test dengan firmware `test_ultrasonic`. |
| 3 | **Servo tidak bergerak** | Tegangan tidak cukup, atau servo rusak | Pastikan servo mendapat tegangan 5V dari adaptor eksternal, bukan dari ESP32 langsung. |
| 4 | **Servo bergetar/bergerak tidak stabil** | Voltage dip saat servo dan WiFi aktif bersamaan | Gunakan **adaptor 5V eksternal** terpisah untuk servo. Pastikan ground terhubung bersama. |
| 5 | **ESP32 restart terus-menerus** | Memori habis (heap overflow) atau arus tidak cukup | Cek Free Heap di Serial Monitor. Gunakan adaptor power yang cukup kuat (minimal 1A). |

### Masalah Koneksi & Jaringan

| No | Masalah | Kemungkinan Penyebab | Solusi |
|----|---------|---------------------|--------|
| 6 | **ESP32 tidak bisa konek WiFi** | Password salah, jaringan berubah, atau di luar jangkauan | Tekan tombol BOOT 3 detik (atau kirim `reswi` via serial) untuk reset WiFi, lalu konfigurasi ulang. |
| 7 | **Vision Engine tidak menemukan kamera** | ESP32-CAM belum konek WiFi, atau IP berubah | Pastikan LED merah ESP32-CAM mati (artinya WiFi sudah konek). Restart Vision Engine agar auto-discovery berjalan ulang. |
| 8 | **Kamera lag / gambar patah-patah** | FPS terlalu tinggi atau bandwidth terbatas | Gunakan resolusi rendah (tekan `3`). Pastikan router WiFi tidak overload. |
| 9 | **Upload firmware gagal di macOS** (`termios.error`) | Driver serial USB tidak mendukung baud rate tinggi | Sudah ditangani: upload speed dikunci di `115200` pada `platformio.ini`. Jika masih gagal, coba cabut-pasang kabel USB. |

### Masalah Software & Database

| No | Masalah | Kemungkinan Penyebab | Solusi |
|----|---------|---------------------|--------|
| 10 | **Gerbang tidak buka padahal kartu valid** | Slot penuh, saldo kurang, atau status masih "PARKED" | Cek Serial Monitor untuk melihat pesan error detail. Gunakan `check_db.py` untuk verifikasi data. |
| 11 | **Deteksi slot tidak akurat** (selalu terisi/kosong) | Kalibrasi sudah usang, cahaya berubah drastis | Lakukan kalibrasi ulang: pastikan semua slot kosong → tekan `C`. |
| 12 | **Supabase error / koneksi timeout** | Koneksi internet terputus | Periksa koneksi internet ESP32 dan komputer server. Cek log di Serial Monitor. |
| 13 | **ESP32 hang saat banyak kendaraan masuk/keluar** | Dual-core deadlock di network stack | Sudah ditangani di firmware: task HTTP terpisah di Core 0 dengan Mutex. Jika masih terjadi, restart ESP32. |

## 8.2 Pertanyaan yang Sering Diajukan (FAQ)

**Q: Berapa banyak slot parkir yang bisa diawasi oleh satu kamera?**  
A: Secara teoritis, satu kamera dapat mengawasi puluhan slot selama posisi kamera memadai dan resolusi cukup. Pada konfigurasi saat ini, sistem mengawasi **7 slot mobil** dan **9 slot motor** (total 16 slot).

**Q: Apakah sistem bisa bekerja tanpa internet?**  
A: **Tidak untuk saat ini.** ESP32 Gate memerlukan koneksi ke Supabase untuk verifikasi kartu dan saldo. Vision Engine juga memerlukan koneksi untuk mengirim status slot. Namun, komunikasi antara Vision Engine dan ESP32-CAM berjalan secara **lokal** (LAN).

**Q: Apa yang terjadi jika listrik padam saat kendaraan sedang parkir?**  
A: Data terakhir sudah tersimpan di Supabase (cloud). Saat sistem dinyalakan kembali, kendaraan yang masih berstatus "PARKED" dapat keluar dengan tap RFID seperti biasa.

**Q: Bagaimana cara mendaftarkan kartu RFID baru?**  
A: Saat ini, pendaftaran dilakukan melalui script `seed_test_data.py` atau langsung melalui dashboard Supabase. Fitur registrasi via mobile app sedang dalam pengembangan.

**Q: Apakah satu pengguna bisa punya lebih dari satu kartu?**  
A: Ya. Tabel `rfid_cards` memungkinkan banyak kartu terhubung ke satu akun pengguna.

**Q: Bagaimana cara menambah saldo pengguna?**  
A: Saat ini dapat dilakukan langsung melalui dashboard Supabase dengan mengubah kolom `balance` di tabel `users`. Fitur top-up via aplikasi mobile akan tersedia di versi mendatang.

---

# BAB 9: Referensi Teknis (Lampiran)

## 9.1 Keyboard Shortcut Vision Engine

Daftar lengkap tombol yang dapat digunakan pada jendela Vision Engine:

| Tombol | Fungsi | Keterangan |
|--------|--------|------------|
| `G` | Mode Gambar | Aktifkan mode menggambar slot baru (drag mouse) |
| `H` | Mode Hapus | Aktifkan mode menghapus slot (klik slot) |
| `N` | Mode Normal | Kembali ke mode pengawasan normal |
| `C` | Kalibrasi | Ambil referensi semua slot (pastikan slot kosong!) |
| `S` | Simpan | Simpan konfigurasi slot dan referensi kalibrasi |
| `Q` | Keluar | Tutup program Vision Engine |
| `F` | Senter | Ganti level senter kamera (0→1→2→3→0...) |
| `3` | Resolusi Rendah | Ganti ke 320×240 |
| `4` | Resolusi Sedang | Ganti ke 640×480 (default) |
| `5` | Resolusi Tinggi | Ganti ke 800×600 |
| `1` | Tipe Mobil | Saat menggambar slot, tandai sebagai slot mobil |
| `2` | Tipe Motor | Saat menggambar slot, tandai sebagai slot motor |
| `Esc` | Batal | Batalkan pemilihan tipe slot |

## 9.2 Perintah Serial ESP32

| Perintah | Fungsi |
|----------|--------|
| `reswi` | Reset konfigurasi WiFi dan restart ESP32 |
| (Tombol BOOT 3 detik) | Sama seperti `reswi` — reset WiFi via tombol fisik |

## 9.3 Konfigurasi Slot Parkir Saat Ini

Data tersimpan di file `slots_esp32.json`. Konfigurasi aktif:

| Slot ID | Tipe | Koordinat (x1,y1) → (x2,y2) |
|---------|------|------------------------------|
| A1 | Mobil | (553, 271) → (631, 397) |
| A2 | Mobil | (456, 275) → (545, 396) |
| A3 | Mobil | (362, 275) → (443, 397) |
| A4 | Mobil | (270, 273) → (347, 395) |
| A5 | Mobil | (179, 270) → (255, 390) |
| A6 | Mobil | (93, 271) → (158, 388) |
| A7 | Mobil | (0, 268) → (77, 380) |
| A8 | Motor | (373, 48) → (398, 112) |
| A9 | Motor | (402, 48) → (435, 111) |
| B1 | Motor | (437, 50) → (467, 110) |
| B2 | Motor | (469, 51) → (498, 111) |
| B3 | Motor | (498, 53) → (526, 112) |
| B4 | Motor | (527, 51) → (557, 113) |
| B5 | Motor | (561, 55) → (589, 113) |
| B6 | Motor | (593, 57) → (618, 115) |

**Total: 7 slot mobil + 8 slot motor = 15 slot**

## 9.4 Daftar File Penting

| File | Fungsi |
|------|--------|
| `src/main.cpp` | Firmware utama ESP32 Gate Controller |
| `src/main-espcam.cpp` | Firmware ESP32-CAM |
| `python/y.py` | Vision Engine (program deteksi slot) |
| `platformio.ini` | Konfigurasi build PlatformIO |
| `slots_esp32.json` | Koordinat slot parkir (dihasilkan oleh Vision Engine) |
| `reference_esp32.npz` | Data referensi kalibrasi (snapshot slot kosong) |
| `last_ip.txt` | IP terakhir ESP32-CAM yang berhasil terkoneksi |
| `supabase_schema.sql` | Schema database Supabase |
| `seed_test_data.py` | Script untuk mengisi data awal (4 user demo) |
| `reset_db.py` | Script untuk reset riwayat parkir dan saldo |
| `check_db.py` | Script untuk cek data terbaru di Supabase |
| `requirements.txt` | Daftar dependensi Python |

## 9.5 Dependensi & Library

### Python (Vision Engine)

| Library | Fungsi |
|---------|--------|
| `opencv-python` | Pengolahan citra dan tampilan video |
| `numpy` | Operasi array dan matematika |
| `requests` | HTTP client untuk komunikasi REST API |
| `torch` | Akselerasi GPU untuk deteksi (opsional) |
| `torchvision` | Utilitas vision untuk PyTorch (opsional) |

### ESP32 Gate Controller (Arduino/PlatformIO)

| Library | Fungsi |
|---------|--------|
| `ESP32Servo` | Kontrol servo motor |
| `WiFiManager` | Konfigurasi WiFi via captive portal |
| `ArduinoJson` | Parsing dan serialisasi JSON |
| `MFRC522` | Driver modul RFID RC522 |

### ESP32-CAM

| Library | Fungsi |
|---------|--------|
| `esp32cam` | Driver kamera OV2640 |
| `WiFiManager` | Konfigurasi WiFi via captive portal |

## 9.6 Parameter Sistem yang Dapat Disesuaikan

| Parameter | Lokasi | Nilai Default | Keterangan |
|-----------|--------|---------------|------------|
| `DISTANCE_THRESHOLD` | `main.cpp` | 15 cm | Jarak deteksi sensor ultrasonik |
| `GATE_HOLD_TIME` | `main.cpp` | 5000 ms (5 detik) | Waktu maksimal gerbang terbuka tanpa kendaraan lewat |
| `POLL_INTERVAL` | `main.cpp` | 5000 ms (5 detik) | Interval polling slot kosong ke Supabase |
| `THRESHOLD_SCORE` | `y.py` | 0.50 | Ambang batas skor deteksi (slot terisi jika skor > 0.50) |
| `SMOOTH_FRAMES` | `y.py` | 15 frame | Jumlah frame untuk smoothing deteksi |
| `FLIP_HORIZONTAL` | `y.py` | True | Mirror gambar kamera secara horizontal |
| `ROI_SIZE` | `y.py` | 64 × 64 px | Ukuran normalisasi ROI per slot |
| Saldo minimum masuk | `main.cpp` | Rp 5.000 | Saldo minimal untuk bisa masuk gerbang |
| Tarif motor (base) | `main.cpp` | Rp 2.000 | Tarif 1 jam pertama motor |
| Tarif motor (lanjut) | `main.cpp` | Rp 30/menit | Tarif per menit setelah 1 jam (motor) |
| Tarif mobil (base) | `main.cpp` | Rp 5.000 | Tarif 1 jam pertama mobil |
| Tarif mobil (lanjut) | `main.cpp` | Rp 80/menit | Tarif per menit setelah 1 jam (mobil) |

---

> 📘 **Akhir Dokumen**  
> Buku Panduan Operasional AutoPics v1.0  
> Untuk pertanyaan atau bantuan teknis, hubungi tim pengembang AutoPics.
