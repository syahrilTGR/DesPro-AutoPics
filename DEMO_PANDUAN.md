# 🚀 Panduan Demo: Alur Kendaraan Masuk (Gate Controller)

Panduan ini menjelaskan mekanisme alur kendaraan dari saat mendekati gerbang hingga palang terbuka, berdasarkan logika pada firmware `src/main.cpp`.

---

## 1. Komponen yang Terlibat

| Komponen | Fungsi dalam Alur |
| :--- | :--- |
| **Sensor Ultrasonik (HC-SR04)** | Mendeteksi adanya kendaraan (objek) di depan gerbang. |
| **Pembaca RFID (MFRC522)** | Membaca kartu identitas pengguna (UID). |
| **Micro Servo Motor** | Penggerak palang pintu gerbang. |
| **ESP32 DevKit** | Otak pengontrol yang memproses logika dan menghitung slot kosong. |

---

## 2. Alur Mekanisme Kendaraan Masuk

Berikut adalah langkah-langkah yang terjadi secara berurutan:

### **Langkah 1: Deteksi Kendaraan**
- Kendaraan mendekati gerbang.
- Sensor Ultrasonik mendeteksi jarak objek **< 3 cm**.

### **Langkah 2: Tap Kartu RFID**
- Pengguna menempelkan kartu RFID ke modul pembaca (Motor In atau Mobil In).
- ESP32 membaca UID kartu.

### **Langkah 3: Validasi Sistem**
Saat kartu terbaca, ESP32 akan melakukan pengecekan berikut ke database **Supabase**:
1. **Cek Slot Kosong**: Apakah masih ada slot parkir yang tersedia? (Jika penuh, gerbang tidak akan dibuka).
2. **Cek Terdaftar**: Apakah UID kartu ini terdaftar di database?
3. **Cek Saldo**: Apakah saldo pengguna ≥ Rp 5.000?
4. **Cek Anti-Passback**: Apakah kendaraan ini sudah tercatat sedang parkir? (Jika sudah, gerbang tidak akan dibuka).

### **Langkah 4: Gerbang Terbuka (Palang Terangkat)**
Jika semua validasi **BERHASIL**:
- Palang pintu dibuka (Servo 90°).
- Waktu masuk dicatat ke Supabase.
- Status gerbang menjadi `isOpen = true`.

### **Langkah 5: Kendaraan Lewat & Palang Menutup**
- Saat kendaraan lewat (sensor jarak mendeteksi perubahan), `hasEntered = true`.
- **Palang akan menutup otomatis** setelah kendaraan lewat (jika jarak kembali normal selama 1.5 detik).
- *Atau* palang menutup otomatis setelah **5 detik** (Timeout) jika tidak ada kendaraan yang lewat.

---

## 3. Skema Logika di Serial Monitor

Saat demo berlangsung, perhatikan output log berikut di Serial Monitor:

**Jika Berhasil:**
```text
📡 Kartu di MOTOR_IN! UID: A9369711
🔄 Mencatat histori masuk ke Supabase...
✅ Entrance Sukses. UID: A9369711, Saldo: Rp 50000
🚀 MOTOR_IN: OPEN
🔒 MOTOR_IN: CLOSE (Lewat)
```

**Jika Gagal (Contoh: Saldo Kurang):**
```text
📡 Kartu di MOTOR_IN! UID: A9369711
❌ Saldo tidak cukup untuk masuk! UID: A9369711 (Saldo: Rp 0)
```

---

## 4. Parameter Waktu (Penting untuk Demo)

| Parameter | Fungsi | Keterangan |
| :--- | :--- | :--- |
| `GATE_HOLD_TIME` | 5000 ms (5 detik) | Maksimal waktu palang terbuka jika kendaraan tidak kunjung lewat. |
| Auto-Close | 1.5 detik | Palang menutup otomatis 1.5 detik setelah kendaraan terdeteksi lewat. |
| Polling Interval | 5000 ms (5 detik) | Frekuensi ESP32 mengecek jumlah slot kosong ke Supabase. |

---

---

## 5. Alur Mekanisme Kendaraan Keluar

Berikut adalah langkah-langkah yang terjadi secara berurutan:

### **Langkah 1: Deteksi Kendaraan di Gerbang Keluar**
- Kendaraan mendekati gerbang keluar (`EXIT_ALL`).
- Sensor Ultrasonik mendeteksi jarak objek **< 3 cm**.

### **Langkah 2: Tap Kartu RFID**
- Pengguna menempelkan kartu RFID ke modul pembaca gerbang keluar.
- ESP32 membaca UID kartu.

### **Langkah 3: Validasi Sistem (Exit)**
Saat kartu terbaca, ESP32 melakukan pengecekan berikut ke database **Supabase**:
1. **Cek Sesi Aktif**: Apakah kartu UID memiliki sesi parkir dengan status `PARKED`?
2. Jika tidak ada sesi aktif → ❌ **Ditolak** (tidak sedang parkir).

### **Langkah 4: Kalkulasi Biaya & Pembayaran**
- ESP32 menghitung **durasi parkir** (dari timestamp `time_in` hingga sekarang).
- Biaya dihitung berdasarkan tipe kendaraan:
  | Tipe | Tarif Dasar (1 Jam) | Tarif per Menit |
  | :--- | :--- | :--- |
  | **Motor** | Rp 2.000 | Rp 30 |
  | **Mobil** | Rp 5.000 | Rp 80 |
- Saldo pengguna dipotong sesuai biaya.

### **Langkah 5: Update Database & Gerbang Terbuka**
- Waktu keluar dicatat (`time_out`).
- Status parkir diubah menjadi `COMPLETED`.
- Saldo pengguna diperbarui (kurang biaya).
- **Palang pintu dibuka** (Servo 90°).
- Palang menutup otomatis sesuai aturan yang sama dengan pintu masuk.

---

## 6. Serial Monitor — Alur Keluar

**Jika Berhasil:**
```text
📡 Kartu di EXIT_ALL! UID: 19019211
🔄 Memproses pembayaran & histori keluar di Supabase...
✅ Exit Sukses. UID: 19019211, Durasi: 45 mnt, Biaya: Rp 5000, Sisa Saldo: Rp 45000
🚀 EXIT_ALL: OPEN
🔒 EXIT_ALL: CLOSE (Lewat)
```

**Jika Gagal (Tidak Sedang Parkir):**
```text
📡 Kartu di EXIT_ALL! UID: A9369711
❌ Kendataan tidak terdaftar sedang parkir atau kartu salah: A9369711
```

---

## 7. Troubleshooting Demo

### Kendaraan tidak bisa masuk (Gerbang tidak terbuka)

| Gejala | Kemungkinan Penyebab | Solusi |
| :--- | :--- | :--- |
| `❌ Kartu belum terdaftar!` | UID kartu belum ada di tabel `rfid_cards` Supabase | Daftarkan kartu lewat dashboard Supabase atau script `seed_test_data.py` |
| `❌ Saldo tidak cukup` | Saldo < Rp 5.000 | Top-up saldo lewat dashboard Supabase atau aplikasi |
| `❌ Sudah berada di dalam area parkir!` | Kartu masih punya sesi `PARKED` aktif | Exit dulu lewat gerbang keluar sebelum masuk lagi |
| `⚠️ FULL! Tunggu slot kosong` | Semua slot mobil/motor terisi | Ubah status salah satu slot jadi `EMPTY` via Vision Engine atau Supabase |
| RF tidak terbaca | Jarak kartu terlalu jauh / SPI error | Dekatkan kartu ke reader, cek koneksi kabel |

### Kendaraan tidak bisa keluar

| Gejala | Kemungkinan Penyebab | Solusi |
| :--- | :--- | :--- |
| `❌ Tidak terdaftar sedang parkir` | Belum pernah masuk, atau sesi sudah `COMPLETED` | Cek tabel `parking_history` di Supabase |
| Biaya 0 / Saldo tidak berkurang | Tarif belum dihitung | Cek `time_in` di Supabase (minimal durasi 1 menit) |

### Tip Diagn Cepat

1. **Cek log Serial Monitor** — semua kegagalan tercetak dengan label `❌` dan pesan jelas.
2. **Cek tabel Supabase langsung** — pastikan `parking_history` ada record `PARKED` untuk UID yang tap exit.
3. **Cek slot kosong** — lihat `availSlotsMobil` / `availSlotsMotor` di log (update tiap 5 detik).
4. **Reset WiFi** — tekan tombol BOOT 3 detik atau kirim `reswi` di Serial Monitor.

---

> 💡 **Tips Demo**: 
> Pastikan data di Supabase (`parking_slots`) memiliki slot yang `EMPTY` agar gerbang bisa terbuka. Jika slot penuh, ubah status salah satu slot menjadi `EMPTY` melalui dashboard Supabase atau Vision Engine.
