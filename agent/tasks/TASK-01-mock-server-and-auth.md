# 📋 TASK 01: Desain Schema, Auth API Key, dan Mock Server (Tanpa GPU)
**SDLC Phase:** Fase 1  
**Status:** ✅ COMPLETED  
**Dependencies:** None  
**Lokasi Dokumen:** `agent/tasks/TASK-01-mock-server-and-auth.md`  

---

## 1. Tujuan Task
Membangun pondasi REST API menggunakan **FastAPI** yang berjalan mandiri di `server.py`, dilengkapi autentikasi `X-API-Key`, skema request/response Pydantic, dan mode `--dry-run` (MockSynthesizer) agar dapat diuji secara penuh tanpa memerlukan model PyTorch / GPU.

---

## 2. Rincian Langkah Kerja (Execution Steps)

1. **Definisikan Konfigurasi API di `core/settings.py`:**
   - Tambahkan dataclass `ApiConfig`:
     - `host: str = "127.0.0.1"`
     - `port: int = 8000`
     - `api_key: str = "dev-local-secret-key"`
     - `default_profile: str = "low_resource"`
     - `output_dir: str = "outputs/api"`
   - Pasang ke dataclass `Settings` utama.
   - Izinkan override via environment variable `TTS_API_KEY`.

2. **Buat Pydantic Schemas (`core/api_schemas.py` atau `api/schemas.py`):**
   - `SynthesizeRequest`:
     - `text: str` (min_length=1, max_length=5000)
     - `voice: str = "sample_voice"`
     - `profile: Optional[str] = None` (enum: "low_resource", "fast")
     - `temperature: float = 0.25`
     - `tempo: float = 1.0`
     - `pitch: float = 0.0`
   - `VoicesResponse`: list of string `voices`.
   - `HealthResponse`: `status: str`, `model_loaded: bool`, `device: str`, `default_profile: str`.
   - `ErrorResponse`: `error: str`, `detail: Optional[str] = None`.

3. **Buat Module Autentikasi (`api/auth.py` atau fungsi dependency di `server.py`):**
   - Menggunakan `APIKeyHeader(name="X-API-Key", auto_error=False)`.
   - Jika key tidak cocok atau kosong, lemparkan `HTTPException(status_code=401, detail="Invalid or missing API Key")`.

4. **Buat Entry Point `server.py`:**
   - Argumen CLI: `python server.py [--dry-run] [--port 8000] [--host 127.0.0.1]`.
   - Jika `--dry-run` aktif: gunakan `core.synth_mock.MockSynthesizer` (menghasilkan audio dummy sinusoidal/silence WAV).
   - Buat endpoint:
     - `GET /health` (Public, no auth) -> return status server & model mock.
     - `GET /api/v1/voices` (Auth required) -> list file `.wav` di folder `prompt_audio/`.
     - `POST /api/v1/tts/synthesize` (Auth required) -> return mock audio/wav stream.

---

## 3. Batasan Ketat (Do NOT Do in This Task)
- ❌ **JANGAN** menyambungkan ke model PyTorch Chatterbox asli di task ini (fokus pada arsitektur & mock dulu).
- ❌ **JANGAN** membuat endpoint batch multi-segmen di task ini (itu tugas Task 04).
- ❌ **JANGAN** memodifikasi `app.py` atau unit test lama di `tests/`.

---

## 4. Wajib Unit Test (Definition of Done)
Sebelum task ini dianggap selesai, buat file test baru: **`tests/test_api_mock.py`** dan pastikan lulus:

- [ ] `test_health_endpoint`: `GET /health` mengembalikan status 200 dan JSON health.
- [ ] `test_auth_missing_key`: `GET /api/v1/voices` tanpa header mengembalikan status 401.
- [ ] `test_auth_invalid_key`: `GET /api/v1/voices` dengan header salah mengembalikan status 401.
- [ ] `test_voices_valid`: `GET /api/v1/voices` dengan key valid mengembalikan status 200 dan daftar suara.
- [ ] `test_synthesize_mock_wav`: `POST /api/v1/tts/synthesize` dengan body valid mengembalikan status 200, `Content-Type: audio/wav`, dan data binary WAV valid.
- [ ] `test_synthesize_empty_text`: `POST /api/v1/tts/synthesize` dengan teks kosong mengembalikan status 422.

---

## 5. Perintah Verifikasi
```bash
pytest tests/test_api_mock.py -v
```
*Syarat lulus: Semua test di file ini wajib PASS 100%.*
