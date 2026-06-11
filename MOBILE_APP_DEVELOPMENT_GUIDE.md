# 📱 Panduan Pengembangan Aplikasi Mobile - Proyek AutoPics

Dokumen ini disusun khusus sebagai acuan integrasi untuk **Tim Mobile App Developer** dalam proyek **AutoPics (Automated Parking System)**. Aplikasi mobile berinteraksi dengan **ESP32 Gate Controller** dan **Python Vision Engine** melalui **Supabase (PostgreSQL & REST API)**.

---

## 1. Arsitektur Komunikasi (Supabase API)

Seluruh sinkronisasi data dilakukan menggunakan ekosistem **Supabase** (PostgREST API). Tim mobile app diwajibkan menggunakan **Supabase SDK** (tersedia untuk Flutter, React Native, iOS, dan Android). 
Gunakan fitur **Supabase Realtime** (WebSockets) untuk fitur live monitoring seperti pembaruan jumlah slot parkir kosong.

---

## 2. Skema Relasional Database (PostgreSQL)

Pastikan aplikasi Anda melakukan *query* sesuai dengan tabel-tabel di bawah ini:

### A. Tabel `users`
Menyimpan informasi pengguna dan nominal saldo.
*   `id` *(UUID)*: Primary Key pengguna.
*   `name` *(String)*: Nama pengguna.
*   `balance` *(Numeric)*: Saldo saat ini dalam Rupiah (contoh: `50000`).

### B. Tabel `rfid_cards`
Satu `user` dapat memiliki banyak kartu RFID (One-to-Many).
*   `uid` *(String, Primary Key)*: ID Hexadecimal kartu RFID (Tanpa spasi, contoh: `19019211`).
*   `user_id` *(UUID)*: Relasi ke tabel `users`.
*   `vehicle_type` *(String)*: Jenis kendaraan (`'Mobil'` atau `'Motor'`).

### C. Tabel `parking_slots`
Diperbarui secara berkala oleh *Vision Engine Python* menggunakan deteksi kamera.
*   `slot_id` *(String)*: ID slot parkir (contoh: `slot_1`, `slot_2`).
*   `status` *(String)*: Status okupansi. Nilainya: `'EMPTY'` (Kosong) atau `'FULL'` (Terisi).
*   `last_updated` *(Timestamp)*: Waktu deteksi terakhir.

### D. Tabel `parking_history`
Diperbarui oleh ESP32 saat pengguna melakukan *Tap-In* dan *Tap-Out* di gerbang fisik.
*   `id` *(UUID)*: Primary key histori parkir.
*   `rfid_uid` *(String)*: Relasi ke kartu yang ditap.
*   `time_in` *(Timestamp)*: Waktu masuk (dibuat saat gerbang masuk).
*   `time_out` *(Timestamp)*: Waktu keluar (dibuat saat gerbang keluar).
*   `duration_minutes` *(Numeric)*: Total menit parkir.
*   `total_fee` *(Numeric)*: Biaya yang dipotong dari saldo.
*   `status` *(String)*: Kondisi saat ini (`'PARKED'` jika masih di dalam, `'COMPLETED'` jika sudah keluar).

---

## 3. Panduan Implementasi Logika Fitur Utama

### Fitur A: Live Slot & Peta Parkir Interaktif
1.  Gunakan **Supabase Realtime** untuk *subscribe* ke tabel `parking_slots`.
2.  Hitung jumlah baris yang memiliki `status == 'EMPTY'` untuk menampilkan **Total Slot Kosong** di dashboard aplikasi Anda.
3.  Untuk halaman **Peta Parkir Visual**, gambarlah tata letak kotak-kotak slot parkir di layar Anda. Warnai:
    *   **Hijau** jika `status == 'EMPTY'`.
    *   **Merah** jika `status == 'FULL'`.

### Fitur B: Live Timer & Estimasi Biaya
Jika pengguna memiliki data terbaru di tabel `parking_history` dengan `status == 'PARKED'`:
1.  Ambil nilai `time_in` (format ISO8601).
2.  Buat timer berkala di HP (tiap 1 menit):
    $$\text{Durasi Menit} = \frac{\text{Waktu Sekarang (Timestamp HP)} - \text{time\_in (Timestamp)}}{60}$$
3.  **Estimasi Biaya:** Tarif yang diterapkan di gerbang saat ini adalah **Rp 5.000,- per menit/jam (tergantung demo)**. Rumus estimasi biaya di aplikasi:
    $$\text{Estimasi Biaya} = \text{Durasi Menit} \times \text{Tarif Parkir}$$

### Fitur C: Riwayat & Saldo User
*   Gunakan SDK Supabase untuk menge-fetch tabel `users` untuk menampilkan `balance`.
*   Tampilkan daftar histori dari tabel `parking_history` dimana statusnya `'COMPLETED'` dan urutkan berdasarkan `time_out` (Descending).

---

## 4. Tips & Best Practices untuk Mobile App Dev
*   **Waktu ISO8601:** Konversi seluruh tanggal di tabel Supabase ke waktu lokal perangkat saat menampilkannya ke antarmuka pengguna (`time_in` dan `time_out` direkam dalam UTC).
*   **Keamanan Database (RLS):** Untuk pengembangan awal, Row Level Security (RLS) di Supabase mungkin dimatikan. Namun, di versi rilis (*Production*), pastikan aplikasi mobile menggunakan *Access Token (JWT)* dari Supabase Authentication sebelum bisa melakukan *Query*.
*   **Registrasi Kartu Manual:** Saat ini pendaftaran kartu RFID ke dalam database dilakukan langsung oleh Admin (menggunakan skrip Python). Integrasi klaim RFID via aplikasi mobile ditunda untuk versi mendatang.

---
*Dokumentasi ini adalah panduan resmi integrasi sistem AutoPics versi terbaru.*
