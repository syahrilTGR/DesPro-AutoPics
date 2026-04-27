# Laporan Deskripsi Proyek: AutoPics (Automated Parking System)
**Sistem Inteligensi Parkir Terintegrasi IoT, Computer Vision, dan Ekosistem Mobile**

## 1. Pendahuluan
AutoPics merupakan sistem manajemen parkir pintar (Smart Parking) yang dirancang untuk mengatasi inefisiensi pada sistem parkir konvensional. Dengan mengintegrasikan teknologi *Internet of Things (IoT)* dan *Computer Vision*, sistem ini mampu mengotomatisasi seluruh proses parkir—mulai dari deteksi ketersediaan lokasi, otentikasi identitas, hingga sistem pembayaran digital yang terintegrasi. Proyek ini diimplementasikan dalam bentuk miniatur fungsional sebagai representasi sistem parkir modern berbasis data.

## 2. Arsitektur dan Komponen Sistem
Sistem AutoPics dibangun di atas lima pilar teknologi yang saling berinteraksi secara *real-time*:

### 2.1 Main Controller (ESP32)
Unit ini bertindak sebagai otak mekanis di gerbang parkir. ESP32 mengontrol:
*   **Sensor Ultrasonik (HC-SR04)**: Diletakkan di setiap pintu masuk (Motor/Mobil) dan keluar untuk mendeteksi keberadaan objek kendaraan.
*   **Modul RFID (RC522)**: Sebagai alat otentikasi kartu identitas pengguna yang terhubung ke akun digital.
*   **Micro Servo Motor**: Sebagai aktuator untuk menggerakkan palang pintu fisik berdasarkan validasi data.

### 2.2 Visual Monitoring (ESP32-CAM)
Berbeda dengan sistem konvensional yang membutuhkan sensor di setiap slot, AutoPics menggunakan **ESP32-CAM** yang diletakkan di posisi strategis. Perangkat ini secara nirkabel menyiarkan (*stream*) visual seluruh area parkir ke unit pemrosesan server.

### 2.3 Vision Engine (Python & OpenCV)
Unit pemrosesan citra ini berjalan pada server/PC. Menggunakan library OpenCV, perangkat lunak ini menerapkan metode **Region of Interest (ROI)**:
*   Sistem melakukan *labeling* pada koordinat spesifik yang mewakili tiap slot parkir.
*   Algoritma mendeteksi perubahan intensitas objek dalam kotak ROI untuk menentukan status okupansi slot.
*   Hasil analisis dikirimkan secara instan ke database untuk memperbarui status slot tanpa intervensi manusia.

### 2.4 Cloud Backend (Firebase Realtime Database)
Sebagai pusat sinkronisasi, Firebase menangani data terkait:
*   Status real-time setiap slot parkir.
*   Informasi akun pengguna (nama, ID kartu RFID, saldo).
*   Catatan waktu masuk (*timestamp*) untuk perhitungan biaya parkir otomatis.

### 2.5 Mobile Application
Antarmuka pengguna berbasis aplikasi mobile menyediakan akses informasi kapan saja:
*   **Dashboard Statistik**: Menampilkan angka sisa slot mobil dan motor yang tersedia.
*   **Peta Parkir Interaktif**: Representasi visual denah parkir di mana slot kosong ditandai dengan warna hijau dan slot terisi ditandai dengan warna merah.
*   **Pusat Pembayaran**: Memungkinkan pengguna melakukan pengecekan saldo dan riwayat transaksi parkir.

## 3. Mekanisme Operasional: Metode Hybrid Tapping
AutoPics menerapkan skema **Hybrid Tapping** (Dual Tapping) untuk memastikan integritas data dan keamanan:

1.  **Tahap Masuk**: Kendaraan mendekati gerbang $\rightarrow$ Sensor mendeteksi objek $\rightarrow$ Pengguna melakukan tapping kartu RFID $\rightarrow$ Sistem mengecek saldo minimal dan ketersediaan slot di Firebase $\rightarrow$ Gerbang terbuka & waktu masuk tersimpan.
2.  **Tahap Monitoring**: Selama kendaraan berada di dalam, Vision Engine terus memantau posisi slot melalui kamera dan memperbarui peta di aplikasi.
3.  **Tahap Keluar**: Kendaraan mendekati pintu keluar $\rightarrow$ Pengguna tapping RFID kembali $\rightarrow$ Sistem menghitung durasi parkir $\rightarrow$ Saldo dikurangi secara otomatis $\rightarrow$ Gerbang terbuka.

## 4. Keunggulan Sistem
*   **Skalabilitas Ekonomi**: Penggunaan sistem visual (ROI) menghilangkan biaya instalasi sensor fisik di setiap slot parkir.
*   **Optimalisasi Waktu**: Pengguna dapat melihat sisa slot dari kejauhan melalui aplikasi, mengurangi waktu pencarian tempat parkir.
*   **Ekosistem Cashless**: Integrasi pembayaran otomatis meningkatkan kenyamanan dan meminimalisir kesalahan manusia pada gerbang manual.

---
*Laporan ini disusun untuk mendokumentasikan perancangan sistem AutoPics secara menyeluruh bagi keperluan akademis maupun teknis.*
