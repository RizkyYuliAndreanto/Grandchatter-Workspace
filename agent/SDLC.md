# 🔄 SDLC (Software Development Life Cycle)
**Fitur:** Local REST API Server (Indonesian TTS & Voice Cloning)  
**Status:** ROADMAP / PHASES  
**Lokasi Dokumen:** `agent/SDLC.md`  

---

## Roadmap Pelaksanaan (5 Fase Bertahap)

Untuk memastikan implementasi berjalan rapi, bebas bug, dan tidak merusak sistem yang sudah ada, eksekusi dibagi menjadi 5 fase berurutan:

```
┌─────────────────────────────────────────────────────────────┐
│ Fase 1: Desain Kontrak & Mock Server (Zero GPU Dependency) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Fase 2: Engine Integration & Concurrency Lock               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Fase 3: Implementasi Dual Profile (Kentang vs Dewa)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Fase 4: Testing & Hardening (Unit + Integration Tests)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Fase 5: Dokumentasi & Client Integration Examples           │
└─────────────────────────────────────────────────────────────┘
```

---

### 🔹 Fase 1: Desain Kontrak & Mock Server (Zero GPU Dependency)
*Tujuan: Memastikan arsitektur API, routing, autentikasi, dan schema Pydantic berjalan sempurna tanpa perlu load model PyTorch.*
- [ ] Definisikan Pydantic schemas (Request, Response, Error models).
- [ ] Implementasikan dependency autentikasi `X-API-Key`.
- [ ] Buat entry point server `server.py` dengan flag `--dry-run` (menggunakan `MockSynthesizer`).
- [ ] Verifikasi bahwa endpoint dapat di-hit secara lokal dan mengembalikan audio dummy via cURL/Postman.

---

### 🔹 Fase 2: Engine Integration & Concurrency Lock
*Tujuan: Menyambungkan FastAPI ke pipeline inferensi asli dengan proteksi VRAM.*
- [ ] Integrasikan `server.py` dengan `core.synthesizer.Synthesizer` dan `core.batch.run_batch`.
- [ ] Pasang `asyncio.Lock()` pada level inferensi untuk memastikan proses sintesis dieksekusi secara serial (FIFO queue), mencegah tabrakan memory GPU (CUDA OOM).
- [ ] Integrasikan `core.normalizer` agar setiap teks yang masuk otomatis dibersihkan dan dinormalisasi (angka, mata uang, waktu).

---

### 🔹 Fase 3: Implementasi Dual Profile (Kentang vs Dewa)
*Tujuan: Menyesuaikan beban kerja sintesis berdasarkan profil perangkat keras yang dipilih.*
- [ ] Implementasikan logika profil `low_resource`:
  - Batas chunker diperkecil (100–150 karakter).
  - Explicit VRAM/RAM cleanup: `torch.cuda.empty_cache()` dan `gc.collect()` setelah request selesai.
- [ ] Implementasikan logika profil `fast`:
  - Batas chunker normal (200–250 karakter).
  - Mengaktifkan `fp16` dan TF32 untuk memaksimalkan throughput GPU.
- [ ] Mekanisme Auto-Fallback: Jika profil `fast` dipilih di mesin tanpa GPU (CPU-only), server secara otomatis beralih ke `low_resource` tanpa melempar error.

---

### 🔹 Fase 4: Testing & Hardening
*Tujuan: Menjamin keandalan dan stabilitas kode sebelum dipakai di produksi.*
- [ ] Buat suite pengujian baru `tests/test_api.py` menggunakan `starlette.testclient.TestClient`.
- [ ] Uji skenario:
  - Request valid menghasilkan audio WAV yang valid.
  - Request tanpa API Key / key salah menghasilkan `401 Unauthorized`.
  - Request dengan teks kosong menghasilkan `422 Unprocessable Entity`.
  - Request batch 30 segmen berhasil diproses seluruhnya.
- [ ] Jalankan regresi penuh: Pastikan seluruh **57 unit test lama tetap 100% HIJAU**.

---

### 🔹 Fase 5: Dokumentasi & Client Integration Examples
*Tujuan: Mempermudah aplikasi eksternal melakukan integrasi.*
- [ ] Sediakan contoh kode pemanggil di berbagai bahasa:
  - Python (`requests` / `httpx`)
  - Node.js / TypeScript (`fetch` / `axios`)
  - cURL commands
- [ ] Tulis panduan menjalankan server lokal (`python server.py`).
