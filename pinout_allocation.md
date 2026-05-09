# Alokasi Pin Proyek AutoPics (ESP32 Gate Controller)

Dokumen ini berisi daftar alokasi pin GPIO terbaru untuk semua sensor (Ultrasonik & RFID) serta aktuator (Servo Motor) yang digunakan pada perangkat ESP32 Gate Controller sesuai dengan file kode aktif `src/main.cpp`.

---

## 1. Sensor RFID RC522 (Sistem SPI Paralel)
Ketiga sensor RFID dihubungkan secara paralel menggunakan jalur bus SPI standar ESP32 dengan pin Reset (RST) bersama, namun memiliki pin SS (SDA) yang unik untuk memisahkan pembacaan data.

| Sensor RFID | Pin Fungsi SPI | Pin ESP32 (GPIO) | Keterangan |
| :--- | :--- | :--- | :--- |
| **Bersama** | **SCK** | **18** | Jalur Bus Clock SPI bersama |
| **Bersama** | **MISO** | **19** | Jalur Bus MISO SPI bersama |
| **Bersama** | **MOSI** | **23** | Jalur Bus MOSI SPI bersama |
| **Bersama** | **RST** | **4** | Pin Reset bersama |
| **RFID MOTOR_IN** | **SS (SDA)** | **21** | Slave Select RFID Pintu Masuk Motor |
| **RFID MOBIL_IN** | **SS (SDA)** | **22** | Slave Select RFID Pintu Masuk Mobil |
| **RFID EXIT_ALL** | **SS (SDA)** | **25** | Slave Select RFID Pintu Keluar |

---

## 2. Sensor Ultrasonik (HC-SR04)
Digunakan untuk mendeteksi keberadaan kendaraan di depan gerbang sebelum melakukan tapping RFID.

| Sensor | Gerbang | Pin TRIG (GPIO) | Pin ECHO (GPIO) | Keterangan |
| :--- | :--- | :--- | :--- | :--- |
| **Ultrasonik 1** | MOTOR_IN | **32** | **33** | Deteksi Motor masuk |
| **Ultrasonik 2** | MOBIL_IN | **27** | **26** | Deteksi Mobil masuk |
| **Ultrasonik 3** | EXIT_ALL | **16** | **17** | Deteksi Kendaraan keluar |

---

## 3. Servo Motor (Palang Pintu)
Mengontrol gerakan membuka dan menutup palang pintu gerbang parkir.

| Aktuator | Fungsi | Pin ESP32 (GPIO) | Keterangan |
| :--- | :--- | :--- | :--- |
| **Servo 1** | Palang Motor Masuk | **13** | Mengontrol palang masuk motor |
| **Servo 2** | Palang Mobil Masuk | **12** | Mengontrol palang masuk mobil |
| **Servo 3** | Palang Keluar | **14** | Mengontrol palang pintu keluar |

---

## 4. Catatan Catu Daya (Powering)
*   **VCC Modul RFID**: Wajib dihubungkan ke tegangan **3.3V** ESP32 (Toleransi tegangan modul RC522 maksimal adalah 3.3V, jangan hubungkan ke 5V agar modul tidak rusak).
*   **VCC Modul Ultrasonik & Servo**: Dihubungkan ke tegangan **5V** ESP32 / Adaptor eksternal 5V (rekomendasi eksternal untuk kestabilan torsi Servo).
*   **GND**: Semua ground modul wajib terhubung bersama (*Common Ground*) ke pin **GND** ESP32.

---
*Dibuat otomatis berdasarkan sinkronisasi logika firmware `src/main.cpp` yang aktif.*
