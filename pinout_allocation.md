# Alokasi Pin Proyek AutoPics (ESP32)

Dokumen ini berisi daftar alokasi pin GPIO untuk sensor dan aktuator sesuai dengan konfigurasi `diagram.json`.

## 1. Sensor Ultrasonik (HC-SR04)

| Sensor | Fungsi | Pin ESP32 (GPIO) | Keterangan |
| :--- | :--- | :--- | :--- |
| **HC-SR04 1** | Input Motor | **32** (TRIG) / **33** (ECHO) | Deteksi Motor masuk (Safe Pins) |
| **HC-SR04 2** | Input Mobil | **4** (TRIG) / **5** (ECHO) | Deteksi Mobil masuk |
| **HC-SR04 3** | Pintu Keluar | **16** (TRIG) / **17** (ECHO) | Deteksi Kendaraan keluar |

## 2. Servo Motor (Palang Pintu)

| Aktuator | Fungsi | Pin ESP32 (GPIO) | Keterangan |
| :--- | :--- | :--- | :--- |
| **Servo 1** | Palang Motor | **23** | Mengontrol pintu masuk motor |
| **Servo 2** | Palang Mobil | **18** | Mengontrol pintu masuk mobil |
| **Servo 3** | Palang Keluar | **19** | Mengontrol pintu keluar gabungan |

## 3. Catatan Daya (Power)
*   **VCC/VIN**: Terhubung ke pin **5V** ESP32 (lewat Rail Merah Breadboard).
*   **GND**: Terhubung ke pin **GND** ESP32 (lewat Rail Biru/Hitam Breadboard).

---
*Dibuat berdasarkan sinkronisasi diagram.json dan skema logika sistem.*
