# GEMINI.md

Ini adalah file instruksi lokal (Local Rules) untuk agen Antigravity (Gemini) di dalam proyek AutoPics. File ini bekerja bersamaan dengan Global Rules (`<appDataDir>\GEMINI.md`).

## 1. Referensi Utama Arsitektur & Perintah
Proyek ini membagikan arsitektur dan struktur instruksi dengan Claude. Untuk informasi mengenai:
- Arsitektur sistem (ESP32, Supabase, Python Vision, Android)
- Perintah kompilasi (PlatformIO, Python, Android)
- File-file penting dan isu yang diketahui
**SELALU baca file `CLAUDE.md`** di root folder sebelum melakukan analisis atau eksekusi yang menyangkut arsitektur keseluruhan.

## 2. Aturan Spesifik Gemini
- **Supabase MCP:** Selalu manfaatkan Supabase MCP untuk memeriksa skema database, data aktual (seeding), dan eksekusi SQL. Hindari berasumsi tentang struktur tabel tanpa memeriksa secara langsung.
- **Python Environment:** Pastikan selalu menggunakan `venv` yang telah disepakati (seperti yang tertulis di Global Rules atau `CLAUDE.md`) saat mengeksekusi script Python.
- **Konfirmasi Desain (Brainstorming):** Selalu gunakan skill `/brainstorming` untuk mengeksplorasi perubahan arsitektur atau desain fitur sebelum mengimplementasikannya dalam kode.
