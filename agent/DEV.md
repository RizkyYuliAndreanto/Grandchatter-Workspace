# 🛠️ DEV SPEC & ARSITEKTUR TEKNIS
**Fitur:** Local REST API Server (Indonesian TTS & Voice Cloning)  
**Status:** SPECIFICATION  
**Lokasi Dokumen:** `agent/DEV.md`  

---

## 1. Arsitektur Komponen & Stack

```
[Aplikasi Eksternal]
        │
        ▼ (HTTP JSON + Header X-API-Key)
[server.py (FastAPI)]
        │
        ├──► [Auth Middleware / Dependency] (Validasi X-API-Key)
        │
        ├──► [Request Validator (Pydantic)] (Validasi format teks, parameter FX)
        │
        ├──► [Concurrency Manager (asyncio.Lock)] (Mencegah CUDA OOM)
        │
        ├──► [core.normalizer] (Normalisasi angka/jam/rupiah Bahasa Indonesia)
        │
        ├──► [core.chunker] (Dynamic chunk length: 100-150 low / 200-250 fast)
        │
        └──► [core.synthesizer / MockSynthesizer] (Eksekusi inferensi audio)
                │
                └──► Return WAV Binary / JSON Batch Results
```

- **Framework:** FastAPI (`fastapi>=0.100.0`), ASGI Server Uvicorn (`uvicorn>=0.20.0`).
- **Data Validation:** Pydantic V2 (`pydantic>=2.0`).
- **Core Engine:** Menggunakan modul `core/` yang sudah ada (`synthesizer.py`, `batch.py`, `normalizer.py`, `audio_fx.py`).

---

## 2. Profil Perangkat (Hardware Profile)

### Profile A: `low_resource` ("Device Kentang")
- **Target:** CPU-only atau GPU dengan VRAM kecil (≤ 4GB, misal GTX 1650, RTX 3050 Laptop).
- **Karakteristik:**
  - Chunker dipangkas lebih pendek: batas maksimal 100–150 karakter per chunk.
  - Setelah inferensi chunk selesai: eksekusi `torch.cuda.empty_cache()` dan `gc.collect()`.
  - Serial lock ketat: antrean diproses 1 per 1 tanpa tumpang tindih.

### Profile B: `fast` ("Device Dewa")
- **Target:** GPU dengan VRAM lega (≥ 6GB/8GB+, misal RTX 3060, 4070, 4090).
- **Karakteristik:**
  - Chunker ukuran standar: batas 200–250 karakter per chunk.
  - Presisi: `fp16` aktif jika CUDA, TF32 (`torch.backends.cuda.matmul.allow_tf32 = True`).
  - Cache conditioning suara disimpan hangat di VRAM, throughput maksimal.

---

## 3. Spesifikasi Endpoint

### 3.1 `POST /api/v1/tts/synthesize`
Sintesis 1 baris/segmen naskah secara instan (real-time).

- **Headers:**
  - `X-API-Key: <secret_key>` (Wajib)
  - `Content-Type: application/json`
- **Request Body (JSON):**
  ```json
  {
    "text": "Selamat datang di fakta menarik hari ini.",
    "voice": "sample_voice",
    "profile": "fast",
    "temperature": 0.25,
    "tempo": 1.0,
    "pitch": 0.0
  }
  ```
- **Response:**
  - Status `200 OK`
  - Header: `Content-Type: audio/wav`, `X-Audio-Duration: 2.3`
  - Body: Binary audio stream (WAV).

---

### 3.2 `POST /api/v1/tts/batch`
Sintesis naskah multi-segmen (contoh: 30 script video short) dalam 1 request.

- **Headers:**
  - `X-API-Key: <secret_key>` (Wajib)
  - `Content-Type: application/json`
- **Request Body (JSON):**
  ```json
  {
    "voice": "sample_voice",
    "profile": "low_resource",
    "tempo": 1.0,
    "pitch": 0.0,
    "segments": [
      { "id": "scene_01", "text": "Tahukah Anda fakta pertama ini?" },
      { "id": "scene_02", "text": "Hewan ini mampu bertahan hidup tanpa makan berminggu-minggu." },
      { "id": "scene_03", "text": "Harganya bisa mencapai Rp 50.000.000 per ekor." }
    ]
  }
  ```
- **Response:**
  - Status `200 OK`
  - Body (JSON):
    ```json
    {
      "status": "success",
      "profile_used": "low_resource",
      "total_segments": 3,
      "results": [
        {
          "id": "scene_01",
          "audio_url": "/api/v1/audio/download/run_abc123/scene_01.wav",
          "duration_s": 2.3
        },
        {
          "id": "scene_02",
          "audio_url": "/api/v1/audio/download/run_abc123/scene_02.wav",
          "duration_s": 3.8
        },
        {
          "id": "scene_03",
          "audio_url": "/api/v1/audio/download/run_abc123/scene_03.wav",
          "duration_s": 3.1
        }
      ]
    }
    ```

---

### 3.3 `GET /api/v1/audio/download/{run_id}/{file_name}`
Mengunduh file audio hasil generate batch.

- **Headers:** `X-API-Key: <secret_key>`
- **Response:** Binary WAV audio file.

---

### 3.4 `GET /api/v1/voices`
Mendapatkan daftar preset suara yang tersedia di folder `prompt_audio/`.

- **Headers:** `X-API-Key: <secret_key>`
- **Response (JSON):**
  ```json
  {
    "voices": ["sample_voice", "narator_short", "suara_dokumenter"]
  }
  ```

---

### 3.5 `GET /health`
Pemeriksaan kesehatan server & model (tidak memerlukan API Key).

- **Response (JSON):**
  ```json
  {
    "status": "healthy",
    "model_loaded": true,
    "device": "cuda",
    "default_profile": "fast"
  }
  ```

---

## 4. Keamanan & Konfigurasi (`config.yaml`)
Penambahan section `api` pada konfigurasi:
```yaml
api:
  host: "127.0.0.1"
  port: 8000
  api_key: "dev-local-secret-key"
  default_profile: "low_resource"  # atau "fast"
  output_dir: "outputs/api"
```
Nilai `api_key` juga dapat dioverride melalui environment variable `TTS_API_KEY`.
