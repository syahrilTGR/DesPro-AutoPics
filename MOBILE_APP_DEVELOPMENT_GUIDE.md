# 📱 Panduan Pengembangan Aplikasi Mobile - Proyek AutoPics

Dokumen ini disusun khusus sebagai acuan integrasi untuk **Tim Mobile App Developer** dalam proyek **AutoPics (Automated Parking System)**. Aplikasi mobile berinteraksi secara realtime dengan **ESP32 Gate Controller** dan **Python Vision Engine** melalui **Firebase Realtime Database (RTDB)**.

---

## 1. Arsitektur Komunikasi realtime (Firebase RTDB)

Seluruh sinkronisasi data dilakukan tanpa REST API konvensional, melainkan memanfaatkan fitur **realtime listener / subscription** bawaan Firebase SDK (Android/iOS/Flutter/React Native).

---

## 2. Kontrak Struktur Data JSON

Pastikan database Firebase Anda terstruktur persis seperti skema aktif di bawah ini:

```json
{
  "users": {
    "A1B2C3D4": {
      "balance": 50000,
      "status": "active",
      "parked_at": 1715222400,
      "owner_id": "auth_uid_user_hp"
    }
  },
  "parkir": {
    "slots": {
      "mobil": {
        "A1": {
          "terisi": false,
          "updated_at": "2026-05-09 11:30:00"
        }
      },
      "motor": {
        "B1": {
          "terisi": true,
          "updated_at": "2026-05-09 11:31:15"
        }
      }
    },
    "ringkasan": {
      "mobil": {
        "total": 4,
        "terisi": 1,
        "kosong": 3,
        "persen_terisi": 25.0,
        "updated_at": "2026-05-09 11:31:15"
      },
      "motor": {
        "total": 6,
        "terisi": 3,
        "kosong": 3,
        "persen_terisi": 50.0,
        "updated_at": "2026-05-09 11:31:15"
      }
    }
  },
  "unregistered_taps": {
    "MOTOR_IN": {
      "uid": "D1E2F3A4",
      "timestamp": 1715222520
    },
    "MOBIL_IN": {
      "uid": "F5G6H7I8",
      "timestamp": 1715222535
    },
    "EXIT_ALL": {
      "uid": "C9B8A7D6",
      "timestamp": 1715222550
    }
  }
}
```

### Penjelasan Field & Aturan Tipe Data:

#### A. Node Pengguna (`/users/{UID_KARTU}`)
*   `{UID_KARTU}` *(string, UPPERCASE)*: ID kartu RFID fisik hasil tap (Hexadecimal, tanpa spasi/pemisah, contoh: `"A1B2C3D4"`).
*   `balance` *(integer)*: Jumlah nominal rupiah saldo akun pengguna (contoh: `50000`).
*   `status` *(string)*: Kondisi parkir pengguna. Nilai yang valid:
    *   `"active"`: Kartu aktif dan berada di luar area parkir (siap masuk).
    *   `"parked"`: Pengguna sedang berada di dalam area parkir.
    *   `"left"`: Pengguna baru saja keluar (sama fungsionalnya dengan `"active"`).
*   `parked_at` *(integer, Unix Timestamp)*: Detik Unix sejak Epoch ketika kendaraan masuk (diisi otomatis oleh ESP32). Gunakan ini untuk menghitung durasi parkir di HP secara dinamis.
*   `owner_id` *(string)*: Kode UID dari akun Firebase Authentication milik pengguna HP.

#### B. Peta & Denah Visual (`/parkir/slots/{tipe_kendaraan}/{slot_id}`)
*   `terisi` *(boolean)*: `true` jika mobil/motor terdeteksi parkir di slot tersebut oleh kamera (Vision Engine), `false` jika kosong. Gunakan ini untuk mewarnai peta visual denah parkir di layar HP (Hijau = Kosong, Merah = Terisi).

#### C. Live Slot Counter (`/parkir/ringkasan/{tipe_kendaraan}`)
*   `kosong` *(integer)*: Menampilkan sisa slot kosong yang tersedia untuk ditampilkan di halaman depan dashboard aplikasi secara realtime.

#### D. Registrasi Kartu Tanpa NFC HP (`/unregistered_taps/{NAMA_GERBANG}`)
*   `uid` *(string)*: Berisi UID kartu tak dikenal terakhir yang baru saja di-*tap* di gerbang fisik.
*   `timestamp` *(integer, Unix Timestamp)*: Waktu saat kartu tersebut di-*tap* di gerbang.

---

## 3. Panduan Implementasi Logika Fitur Utama

### Fitur A: Live Slot & Peta Parkir Interaktif
1.  Buat **Realtime Listener** ke path `/parkir/ringkasan/mobil/kosong` dan `/parkir/ringkasan/motor/kosong`. Tampilkan angka ini langsung di dashboard depan.
2.  Buat halaman **"Peta Parkir"** yang melakukan subscription ke `/parkir/slots`. Gambar kotak-kotak slot parkir sesuai tata letak layout miniatur Anda, lalu warnai:
    *   Warna **Hijau** jika `terisi: false`.
    *   Warna **Merah** jika `terisi: true`.

---

### Fitur B: Live Timer & Estimasi Biaya
Jika pengguna memiliki `status == "parked"` di profil mereka:
1.  Ambil nilai `parked_at` (Unix Timestamp).
2.  Buat fungsi timer berkala di HP (tiap 1 menit):
    $$\text{Durasi Detik} = \text{Waktu Sekarang (Timestamp HP)} - \text{parked\_at}$$
3.  Konversi hasil detik tersebut ke format `Jam : Menit`.
4.  **Estimasi Biaya:** Tarif yang diterapkan di gerbang saat ini adalah **Rp 2.000,- per jam** (pembulatan ke atas). Rumus estimasi biaya di aplikasi:
    $$\text{Estimasi Biaya} = \left\lceil \frac{\text{Durasi Detik}}{3600} \right\rceil \times 2000$$

---

### Fitur C: Alur Registrasi Kartu Baru (Last Tap Claim)
Karena tidak semua smartphone memiliki sensor NFC bawaan, kita menggunakan metode klaim tap fisik di gerbang.

#### Alur Logika di Aplikasi Mobile:
1.  Sediakan halaman **"Registrasi Kartu Baru"**.
2.  Minta pengguna berdiri di dekat salah satu gerbang gerbang fisik (pilihannya: `"Pintu Masuk Motor" / "MOTOR_IN"`, `"Pintu Masuk Mobil" / "MOBIL_IN"`, atau `"Pintu Keluar" / "EXIT_ALL"`).
3.  Instruksikan pengguna untuk **menempelkan kartu RFID fisiknya sekali** ke sensor di gerbang tersebut.
4.  Pada aplikasi mobile, sediakan tombol **"Klaim Kartu Saya"** setelah mereka memilih gerbang yang sesuai.
5.  Ketika tombol ditekan, baca data dari `/unregistered_taps/{GERBANG_PILIHAN}`:
    ```javascript
    const tapData = snapshot.val(); // Ambil uid dan timestamp
    const waktuSekarangSeconds = Math.floor(Date.now() / 1000);
    const selisihDetik = waktuSekarangSeconds - tapData.timestamp;

    if (selisihDetik <= 60) { // Toleransi waktu tap maksimal 60 detik (1 menit)
        // KARTU VALID! Lakukan penulisan data baru ke profil user:
        const userUidKartu = tapData.uid;
        
        // Daftarkan ke database
        firebase.database().ref(`/users/${userUidKartu}`).set({
            "balance": 0, // Saldo default awal
            "status": "active",
            "parked_at": 0,
            "owner_id": currentUserAuthUid // Hubungkan ke Auth User HP
        });

        // (Opsional) Hapus data unregistered tap agar tidak diklaim ganda
        firebase.database().ref(`/unregistered_taps/${GERBANG_PILIHAN}`).remove();

        alert("Registrasi Kartu Berhasil! Silakan Top-Up saldo sebelum masuk parkir.");
    } else {
        alert("Waktu pengetukan kartu sudah kadaluwarsa. Silakan tempelkan kembali kartu Anda di gerbang fisik!");
    }
    ```

---

## 4. Tips & Best Practices untuk Mobile App Dev
*   **Format UID:** Selalu pastikan string UID dikonversi ke **UPPERCASE** tanpa karakter spasi atau tanda hubung sebelum dicari/ditulis ke Firebase.
*   **Unix Timestamp:** Selalu gunakan satuan **Detik** (bukan Milidetik) untuk pencatatan waktu agar selaras dengan library `<time.h>` yang digunakan pada modul ESP32. Jika menggunakan JavaScript (`Date.now()`), bagi dengan `1000` terlebih dahulu dan lakukan pembulatan ke bawah (`Math.floor`).
*   **Offline Support:** Aktifkan fitur *disk persistence* Firebase agar aplikasi tetap responsif jika koneksi internet seluler pengguna kurang stabil di area parkir semi-indoor.

---
*Dokumentasi ini adalah panduan resmi integrasi sistem AutoPics versi terbaru.*
