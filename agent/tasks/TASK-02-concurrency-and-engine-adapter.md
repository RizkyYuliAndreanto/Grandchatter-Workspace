# 📋 TASK 02: Engine Integration, Text Normalizer, dan Concurrency Lock
**SDLC Phase:** Fase 2  
**Status:** ✅ COMPLETED  
**Dependencies:** `TASK-01-mock-server-and-auth.md`  
**Lokasi Dokumen:** `agent/tasks/TASK-02-concurrency-and-engine-adapter.md`  

---

## 1. Tujuan Task
Menghubungkan `server.py` ke engine sintesis sebenarnya (`core.synthesizer.Synthesizer`), mengaktifkan pembersihan naskah bahasa Indonesia (`core.normalizer`), dan memasang proteksi antrean `asyncio.Lock()` untuk mencegah benturan komputasi dan crash CUDA OOM pada GPU lokal.

---

## 2. Rincian Langkah Kerja (Execution Steps)

1. **Buat Adapter Engine (`api/engine.py`):**
   - Kelas pembungkus singleton/manager untuk memuat model:
     - Jika flag `--dry-run`: inisialisasi `MockSynthesizer`.
     - Jika tanpa `--dry-run`: inisialisasi `core.synthesizer.Synthesizer(settings)`.
   - Simpan status kesiapan model (`is_ready: bool`).

2. **Pasang Normalizer Pipeline:**
   - Sebelum teks dikirim ke model, teks WAJIB melewati `core.normalizer.normalize(text)`.
   - Teks seperti `"Rp 50.000"` berubah jadi `"lima puluh ribu rupiah"`, jam `"14:30"` berubah jadi `"empat belas tiga puluh"`.

3. **Pasang Concurrency Lock (`asyncio.Lock`):**
   - Pasang lock asinkron pada fungsi inferensi API:
     ```python
     inference_lock = asyncio.Lock()
     
     async def synthesize_safe(chunk, conditioning, settings):
         async with inference_lock:
             # Menjalankan inferensi PyTorch di threadpool agar tidak memblok event loop
             return await asyncio.to_thread(synth.synthesize, chunk, conditioning, settings)
     ```
   - Request yang datang bersamaan akan mengantre secara tertib (FIFO), bukan menabrak VRAM secara paralel.

4. **Koneksikan ke Endpoint `POST /api/v1/tts/synthesize`:**
   - Ambil sampel suara dari `prompt_audio/{voice}.wav`.
   - Jalankan `prepare_voice` (conditioning cache).
   - Jalankan sintesis dan kembalikan binary stream WAV.

---

## 3. Batasan Ketat (Do NOT Do in This Task)
- ❌ **JANGAN** membuat endpoint batch multi-segmen di task ini (fokus pada 1 segmen dan concurrency lock).
- ❌ **JANGAN** menghapus atau mengubah `MockSynthesizer` yang dibutuhkan pengujian tanpa GPU.
- ❌ **JANGAN** memodifikasi logika inti di `core/normalizer.py` atau `core/synthesizer.py` jika tidak benar-benar diperlukan.

---

## 4. Wajib Unit Test (Definition of Done)
Sebelum task ini dianggap selesai, tambahkan pengujian di **`tests/test_api_concurrency.py`** dan pastikan lulus:

- [ ] `test_normalizer_integrated`: Kirim request sintesis berisi angka `"123"` dan pastikan audio di-generate dari teks yang telah dinormalisasi (*"seratus dua puluh tiga"*).
- [ ] `test_concurrent_requests_handled`: Kirim 5 request HTTP secara bersamaan (menggunakan `asyncio.gather` atau multi-thread di TestClient), pastikan kelimanya selesai dengan status 200 tanpa race condition atau error 500.
- [ ] `test_voice_not_found`: Kirim request dengan nama voice yang tidak ada di `prompt_audio/`, pastikan server merespons `404 Not Found` atau `400 Bad Request` dengan pesan error yang jelas (bukan 500 crash).

---

## 5. Perintah Verifikasi
```bash
pytest tests/test_api_mock.py tests/test_api_concurrency.py -v
```
*Syarat lulus: Semua test wajib PASS 100%.*
