# Catatan Pembaruan Android — Refaktor Multi-Kendaraan

Dokumen ini adalah panduan singkat untuk menyesuaikan kode Android setelah perubahan skema database "1 Kartu Multi Kendaraan".

## Perubahan Skema yang Relevan

| Sebelum | Sesudah |
|---|---|
| `rfid_cards.vehicle_type` | ❌ Kolom sudah dihapus |
| *(tidak ada)* | ✅ `parking_history.vehicle_type` (VARCHAR) |

---

## Checklist Perubahan di Kode Android

### 1. Data Class `RFIDCard`
Cari file yang memiliki data class / model untuk kartu RFID.

```kotlin
// SEBELUM:
data class RFIDCard(
    val uid: String,
    val userId: String,
    val cardName: String,
    val vehicleType: String,   // ← HAPUS baris ini
    val createdAt: String
)

// SESUDAH:
data class RFIDCard(
    val uid: String,
    val userId: String,
    val cardName: String,
    val createdAt: String
)
```

### 2. Data Class `ParkingHistory`
Cari file model untuk histori parkir.

```kotlin
// SEBELUM (vehicle_type belum ada):
data class ParkingHistory(
    val id: String,
    val rfidUid: String,
    val timeIn: String,
    val timeOut: String?,
    val durationMinutes: Int?,
    val totalFee: Int?,
    val status: String
)

// SESUDAH (tambahkan vehicleType):
data class ParkingHistory(
    val id: String,
    val rfidUid: String,
    val vehicleType: String,   // ← TAMBAH baris ini
    val timeIn: String,
    val timeOut: String?,
    val durationMinutes: Int?,
    val totalFee: Int?,
    val status: String
)
```

### 3. Tampilan di `ParkingHistoryScreen.kt`
Setelah `vehicleType` tersedia di data class `ParkingHistory`, tampilkan informasinya di layar histori:

```kotlin
// Contoh: Tampilkan ikon kendaraan di kartu histori
val vehicleIcon = if (history.vehicleType == "Motor") "🏍️" else "🚗"
Text(text = "$vehicleIcon ${history.vehicleType}")
```

### 4. Cek Serialization / JSON Parsing
Jika proyek menggunakan `kotlinx.serialization` atau `Gson`, pastikan `@SerialName("vehicle_type")` ada di properti baru `vehicleType` di `ParkingHistory`.

```kotlin
@SerialName("vehicle_type")
val vehicleType: String = "Mobil",  // Gunakan default agar tidak null
```

---

## 5. Flow Registrasi Kartu Baru (Opsi A + Validasi)

Karena user sekarang memegang kartu fisik dengan UID (label pada kartu), namun belum terdaftar di aplikasi, tambahkan fitur ini di `RegisterScreen.kt` (atau layar pendaftaran):

1. **Input Field Baru**: Tambahkan field untuk memasukkan UID kartu yang tertera pada label.
2. **Validasi UID**:
   - Sebelum mendaftarkan akun, lakukan *query* ke tabel `rfid_cards` untuk memeriksa apakah UID tersebut sudah digunakan oleh `user_id` lain.
   - Jika `user_id` pada kartu tersebut `!= null`, maka tolak registrasi (kartu sudah dimiliki orang lain).
   - Jika belum ada di tabel, pendaftaran diizinkan, dan setelah akun terbuat, sisipkan (insert) record baru ke `rfid_cards` dengan UID tersebut yang ditautkan ke `user_id` baru.

Contoh logika validasi (Kotlin):
```kotlin
// Cek ketersediaan kartu
val existingCards = SupabaseHelper.client.postgrest["rfid_cards"]
    .select { filter { eq("uid", inputtedUid) } }
    .decodeList<RFIDCard>()

if (existingCards.isNotEmpty()) {
    errorMessage = "Kartu dengan UID ini sudah terdaftar oleh pengguna lain!"
    return@Button
}

// Lanjut proses registrasi (insert user ke tabel users)
// ...

// Tautkan kartu ke user baru
val rfidPayload = mapOf(
    "uid" to inputtedUid,
    "user_id" to newlyCreatedUserId,
    "card_name" to "Kartu $userName"
)
SupabaseHelper.client.postgrest["rfid_cards"].insert(rfidPayload)
```

> [!NOTE]
> Perubahan di atas tidak mengubah alur login, topup, atau navigasi utama. Hanya model data, tampilan histori, dan proses registrasi yang perlu disesuaikan.
