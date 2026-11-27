# 📄 PRD (Product Requirement Document)
**Fitur:** Local REST API Server (Indonesian TTS & Voice Cloning)  
**Status:** DRAFT / LOCKED FOR MVP  
**Lokasi Dokumen:** `agent/PRD.md`  

---

## 1. Latar Belakang & Masalah
Saat ini, proyek *Grandchatter Workspace* dioperasikan melalui antarmuka web Gradio (`app.py`). Untuk kebutuhan produksi konten skala besar seperti **Video Short 60 detik (berisi ~30 baris naskah/segmen)** atau narasi dokumenter, proses input manual melalui GUI sangat memakan waktu. 

Diperlukan interface terprogram (REST API) yang aman, cepat, dan hemat sumber daya agar aplikasi eksternal (video maker, bot, pipeline otomatis) dapat menembak server TTS secara langsung tanpa membuka web browser.

---

## 2. Tujuan & Sasaran (Objectives)
1. **Headless Execution:** Menyediakan server REST API lokal berbasis **FastAPI** yang berjalan terpisah dari Gradio GUI.
2. **Audio Factory Role:** Server hanya bertugas menerima naskah, menormalisasi angka/ejaan bahasa Indonesia, mensintesis audio, dan mengembalikan file audio (WAV). Urusan penyusunan timeline dan sinkronisasi video ditangani sepenuhnya oleh aplikasi eksternal.
3. **Fleksibilitas Perangkat (Dual Hardware Profile):**
   - **Mode Low Resource (Device Kentang):** Optimal dan aman untuk CPU atau GPU dengan VRAM kecil (≤ 4GB).
   - **Mode Fast (Device Dewa):** Throughput maksimal memanfaatkan GPU dengan VRAM lega (≥ 6GB/8GB+).
4. **Proteksi & Keamanan:** Mengamankan endpoint dari akses ilegal dengan autentikasi berbasis **API Key** (`X-API-Key`).

---

## 3. Cakupan (Scope)

### ✅ In-Scope (Wajib Dikerjakan)
- Server API mandiri (`server.py`) berbasis FastAPI.
- Autentikasi API Key via header request (`X-API-Key`).
- Konfigurasi profil performa (`low_resource` vs `fast`) yang dapat dipilih per-request atau via default server.
- Endpoint single segment (`/api/v1/tts/synthesize`) untuk respon real-time baris per baris.
- Endpoint batch multi-segment (`/api/v1/tts/batch`) untuk menerima 30+ script sekaligus dalam 1 request.
- Endpoint daftar preset suara (`/api/v1/voices`) dari folder `prompt_audio/`.
- Endpoint health check (`/health`) untuk memantau status kesiapan model PyTorch.
- Unit & integration tests khusus API (`tests/test_api.py`) dengan dukungan `--dry-run` (MockSynthesizer).

### ❌ Out-of-Scope (Dilarang Dikerjakan)
- Mengubah logika video/audio stitching di aplikasi eksternal.
- Membuat sistem manajemen database user/OAuth yang kompleks.
- Mengubah model deep learning inti atau melakukan fine-tuning ulang.
- Mengubah alur atau merusak Gradio UI di `app.py`.
- Menambahkan fitur Speech-to-Text (STT) atau voice conversion audio-to-audio.

---

## 4. User Persona & Skenario Penggunaan

### Skenario 1: Video Short 60 Detik (~30 Script)
Aplikasi video generator eksternal telah memotong video menjadi 30 segmen/scene. Aplikasi mengirimkan seluruh 30 naskah ke endpoint batch TTS. TTS server memproses antrean audio, lalu mengembalikan daftar file WAV. Aplikasi eksternal kemudian memasang audio tersebut ke timeline video.

### Skenario 2: Narasi Dokumenter Panjang (30 Menit)
Aplikasi eksternal mengirim naskah panjang per paragraf/bab ke endpoint TTS menggunakan mode hemat sumber daya (low resource) agar laptop tetap stabil dan tidak mengalami overheating atau crash memori.
