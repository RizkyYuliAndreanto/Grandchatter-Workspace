# 🚀 PANDUAN MENJALANKAN PROJECT (RUN GUIDE)
**Grandchatter Workspace — Indonesian TTS & Voice Cloning Studio**  
**Dokumentasi:** Cara Menjalankan Project (Lokal & Kaggle | GUI Gradio & REST API Server)  
**Lokasi Dokumen:** `docs/PANDUAN_MENJALANKAN_PROJECT.md`

---

## 📌 Ringkasan 2 Mode Eksekusi

Project ini memiliki 2 pintu masuk independen yang dapat dijalankan secara terpisah:

1. **Mode GUI Gradio (`app.py`)**: Digunakan untuk riset, mendengarkan sampel, mengatur slider tempo/pitch secara visual, dan meng-clone sampel suara baru.
2. **Mode REST API Server (`server.py`)**: Digunakan sebagai backend headless tanpa antarmuka browser, siap di-hit oleh aplikasi eksternal (video generator, bot, automation pipeline).

```
                            ┌────────────────────────────────────────┐
                            │      Grandchatter Core TTS Engine      │
                            │ (Normalizer, Chunker, FX, Synthesizer) │
                            └───────────────────┬────────────────────┘
                                                │
                       ┌────────────────────────┴────────────────────────┐
                       ▼                                                 ▼
          [app.py — Gradio UI]                              [server.py — FastAPI REST API]
     • Testing manual naskah & suara                   • Headless service untuk aplikasi luar
     • Slider parameter (tempo, pitch, gap)            • Otomatisasi Video Short 60s & Dokumenter
     • Upload sampel voice cloning baru                • Autentikasi API Key (X-API-Key)
     • Web browser di port 7860                        • HTTP JSON & WAV stream di port 8000
```

---

## 1. Prasyarat Sistem & Persiapan

### A. Kebutuhan Sistem
- **Sistem Operasi:** Windows 10/11, Linux (Ubuntu/Debian), atau macOS.
- **Python:** Versi 3.10 atau lebih baru (disarankan Python 3.10).
- **Perangkat Keras (Hardware):**
  - **Mode CPU / Device Kentang:** Minimal RAM 8GB–16GB (bisa jalan tanpa GPU dedicated).
  - **Mode GPU / Device Dewa:** NVIDIA GPU (minimal 4GB VRAM untuk FP16, direkomendasikan 6GB–12GB VRAM).

### B. Setup Pertama Kali (Instalasi Virtual Environment)

Buka terminal (PowerShell di Windows atau Bash di Linux/Mac) di folder project:

```powershell
# 1. Buat virtual environment
python -m venv .venv

# 2. Aktifkan virtual environment
# Di Windows PowerShell:
.venv\Scripts\Activate.ps1
# Di Linux / Mac:
source .venv/bin/activate

# 3. Upgrade pip dan install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

> **Catatan PyTorch:** Kaggle sudah menyediakan PyTorch bawaan GPU. Di komputer lokal Anda, jika ingin menggunakan akselerasi GPU NVIDIA (CUDA), pastikan PyTorch dengan CUDA terpasang (`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`). Jika laptop hanya memiliki CPU, PyTorch CPU standar sudah cukup.

### C. File Konfigurasi (`config.yaml`)
Salin file template konfigurasi:
```powershell
cp config.example.yaml config.yaml
```
Buka `config.yaml` dan sesuaikan pengaturan hardware Anda:
```yaml
model:
  device: ""             # Kosongkan untuk auto-detect (CUDA > MPS > CPU). Isi "cpu" untuk paksa mode hemat.
  fp16: false            # Set true jika GPU memiliki VRAM 4GB-8GB untuk menghemat memori.

api:
  host: "127.0.0.1"      # Host lokal
  port: 8000             # Port server API
  api_key: "dev-local-secret-key"  # Kunci rahasia untuk di-hit aplikasi luar
  default_profile: "low_resource"  # "low_resource" (kentang) atau "fast" (dewa)
  output_dir: "outputs/api"        # Folder penyimpanan audio batch
```

---

## 2. Cara Menjalankan Mode REST API Server (`server.py`)

Gunakan mode ini ketika Anda ingin **menghubungkan aplikasi eksternal pembuat video short atau pipeline otomatis** ke server TTS.

### A. Menjalankan di Komputer Lokal (Mode Normal dengan Model)
```powershell
python server.py --host 127.0.0.1 --port 8000
```
- Server akan memuat model Chatterbox TTS dan fine-tune bahasa Indonesia.
- API siap menerima request di: `http://127.0.0.1:8000`.
- Dokumentasi interaktif Swagger otomatis tersedia di browser: `http://127.0.0.1:8000/docs`.

### B. Menjalankan Mode Cepat / Testing Tanpa GPU (`--dry-run`)
Jika Anda sedang mengembangkan kode di aplikasi eksternal dan ingin menguji alur request/response HTTP tanpa perlu memuat model PyTorch yang berat:
```powershell
python server.py --dry-run --port 8000
```
- Server akan menyala instan dalam 1 detik menggunakan `MockSynthesizer`.
- Seluruh endpoint (`/synthesize`, `/batch`, `/voices`, `/health`) berfungsi normal dan mengembalikan audio sintetis dummy yang valid.

### C. Menjalankan di Port / Host Kustom
```powershell
python server.py --host 0.0.0.0 --port 5000
```

---

## 3. Cara Menjalankan Mode GUI Gradio (`app.py`)

Gunakan mode ini ketika Anda ingin melakukan pengujian audio secara visual, mencoba naskah baru dengan slider interaktif, atau **meng-upload file audio orang baru untuk di-clone suaranya**.

### A. Menjalankan di Laptop Lokal
```powershell
python app.py
```
- Buka browser di alamat: `http://127.0.0.1:7860`.
- Masukkan username `user` dan password yang ada di `config.yaml`.
- Pilih sampel suara di `prompt_audio/` atau upload sampel suara WAV baru (durasi 5–10 detik bersih).
- Ketik naskah → Klik tombol **Generate Speech**.

### B. Menjalankan GUI Cepat Tanpa Model (`--dry-ui`)
Untuk menguji layout antarmuka web tanpa memuat model ke GPU/CPU:
```powershell
python app.py --dry-ui
```

### C. Menjalankan di GPU Kaggle (Cloud Gratis 30 Jam/Minggu)
Jika laptop lokal Anda tidak kuat untuk naskah panjang (dokumenter 10–30 menit):
1. Buka [Kaggle](https://www.kaggle.com) → Buat Notebook baru.
2. Di menu kanan notebook: **Accelerator = GPU P100 / T4** · **Internet = ON**.
3. Buka file [launcher.ipynb](launcher.ipynb) di repo ini:
   - **Run Cell 1:** Clone repo & install library.
   - **Run Cell 2:** Buat password tunnel Anda.
   - **Run Cell 3:** Jalankan server Gradio dengan tunnel Cloudflare/Gradio Share.
4. Buka URL publik `*.gradio.live` atau `*.trycloudflare.com` yang muncul di output dari laptop atau HP Anda.

---

## 4. Cara Menjalankan Pengujian (Testing & Verifikasi)

Repositori ini dilengkapi dengan **80 Unit Test** yang mencakup integritas pipeline teks, DSP audio, antrean concurrency, profiling hardware, dan endpoint API.

Semua test dirancang agar dapat berjalan hijau **100% tanpa memerlukan GPU**.

```powershell
# Jalankan seluruh 80 unit test
pytest -v

# Jalankan pengujian khusus REST API server saja
pytest tests/test_api_mock.py tests/test_api_concurrency.py tests/test_api_profiles.py tests/test_api_batch.py -v

# Jalankan pengujian core engine saja
pytest tests/test_normalizer.py tests/test_chunker.py tests/test_batch.py tests/test_audio_fx.py -v
```

---

## 5. Tips Performa & Troubleshooting Lokal

| Gejala / Kondisi | Solusi Praktis |
|---|---|
| **Laptop terasa panas / kipas kencang saat render naskah** | Gunakan profil `"low_resource"` di request API, atau atur `device: "cpu"` di `config.yaml`. Di profil ini, potongan naskah diperpendek (120 karakter) dan memori dibersihkan setiap selesai 1 chunk. |
| **GPU VRAM kecil (GTX 1650 / RTX 3050 4GB)** | Aktifkan `fp16: true` pada `config.yaml` untuk menghemat separuh pemakaian memori VRAM. |
| **Muncul pesan "Voice not found"** | Pastikan file suara referensi Anda diletakkan di dalam folder `prompt_audio/` dengan ekstensi `.wav` atau `.mp3` (contoh: `prompt_audio/narator.wav`). |
| **Port 8000 atau 7860 sudah terpakai** | Jalankan dengan argumen port lain, misalnya `python server.py --port 8080`. |
