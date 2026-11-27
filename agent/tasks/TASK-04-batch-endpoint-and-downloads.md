# 📋 TASK 04: Batch Multi-Segment Endpoint dan Audio Download
**SDLC Phase:** Fase 4 (Bagian 1)  
**Status:** ✅ COMPLETED  
**Dependencies:** `TASK-03-dual-hardware-profiles.md`  
**Lokasi Dokumen:** `agent/tasks/TASK-04-batch-endpoint-and-downloads.md`  

---

## 1. Tujuan Task
Menyediakan endpoint batch yang mampu menerima array multi-segmen (contoh: **30 baris naskah untuk video short 60 detik**, hingga skala ratusan naskah dokumenter) dalam 1 kali HTTP request, memproses seluruh audio secara terurut, menyimpan file audio per segmen, dan mengembalikan URL download serta durasi untuk masing-masing segmen.

---

## 2. Rincian Langkah Kerja (Execution Steps)

1. **Definisikan Schema Batch (`api/schemas.py`):**
   - `SegmentItem`:
     - `id: str` (identitas unik segmen, misal: `"scene_01"`)
     - `text: str` (naskah segmen)
     - `tempo: Optional[float] = None`
     - `pitch: Optional[float] = None`
   - `BatchRequest`:
     - `voice: str = "sample_voice"`
     - `profile: Optional[str] = None`
     - `tempo: float = 1.0`
     - `pitch: float = 0.0`
     - `segments: List[SegmentItem]` (min_items=1, max_items=1000 — skala ratusan naskah)
   - `SegmentResult`:
     - `id: str`
     - `audio_url: str`
     - `duration_s: float`
     - `status: str` (success / failed)
   - `BatchResponse`:
     - `status: str`
     - `profile_used: str`
     - `total_segments: int`
     - `results: List[SegmentResult]`

2. **Implementasikan Endpoint `POST /api/v1/tts/batch`:**
   - Buat folder run khusus: `outputs/api/batch_{run_id}/`.
   - Iterasi setiap segmen di dalam request:
     - Normalisasi teks segmen.
     - Sintesis audio chunk.
     - Simpan audio segmen ke disk: `outputs/api/batch_{run_id}/{segment.id}.wav`.
     - Hitung durasi audio (detik).
     - Jika mode `low_resource` aktif: bersihkan memory setelah setiap segmen.
   - Return daftar URL download untuk setiap segmen: `/api/v1/audio/download/batch_{run_id}/{segment.id}.wav`.

3. **Implementasikan Endpoint `GET /api/v1/audio/download/{batch_id}/{filename}`:**
   - Validasi file ada di dalam folder `outputs/api/{batch_id}/` (cegah path traversal `../`).
   - Kembalikan file WAV menggunakan `FileResponse(path, media_type="audio/wav")`.

---

## 3. Batasan Ketat (Do NOT Do in This Task)
- ❌ **JANGAN** membuat server crash jika salah satu segmen gagal disintesis; catat `status: "failed"` pada segmen tersebut dan lanjutkan segmen berikutnya (anti-runtuh).
- ❌ **JANGAN** mengizinkan download file di luar direktori `outputs/api/` (wajib sanitasi path terhadap karakter `..` atau `/`).

---

## 4. Wajib Unit Test (Definition of Done)
Sebelum task ini dianggap selesai, tambahkan pengujian di **`tests/test_api_batch.py`** dan pastikan lulus:

- [ ] `test_batch_30_segments`: Kirim request batch berisi 30 segmen teks dummy, pastikan respon 200 OK dan mengembalikan 30 item `results`.
- [ ] `test_batch_audio_downloadable`: Hit URL `audio_url` yang dihasilkan dari salah satu segmen, pastikan file WAV berhasil diunduh dan memiliki header audio yang valid.
- [ ] `test_batch_empty_segments`: Kirim request batch dengan `segments: []`, pastikan server merespons `422 Unprocessable Entity`.
- [ ] `test_path_traversal_prevention`: Coba panggil download endpoint dengan path traversal (contoh: `../../config.yaml`), pastikan server menolak dengan `403 Forbidden` atau `404 Not Found`.

---

## 5. Perintah Verifikasi
```bash
pytest tests/test_api_batch.py -v
```
*Syarat lulus: Semua test batch wajib PASS 100%.*
