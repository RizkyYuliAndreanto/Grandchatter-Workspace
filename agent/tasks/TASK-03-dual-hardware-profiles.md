# 📋 TASK 03: Implementasi Dual Profile (Low Resource vs Fast Mode)
**SDLC Phase:** Fase 3  
**Status:** ✅ COMPLETED  
**Dependencies:** `TASK-02-concurrency-and-engine-adapter.md`  
**Lokasi Dokumen:** `agent/tasks/TASK-03-dual-hardware-profiles.md`  

---

## 1. Tujuan Task
Memberikan fleksibilitas performa hardware:
1. **Mode Low Resource ("kentang"):** Untuk CPU atau GPU VRAM kecil (≤ 4GB). Memangkas chunking naskah jadi mini (100–150 char) dan membersihkan memori secara agresif (`gc.collect()` + `torch.cuda.empty_cache()`).
2. **Fast Mode ("dewa"):** Untuk GPU VRAM lega (≥ 6GB/8GB+). Menggunakan chunking standar (200–250 char), FP16 + TF32, dan membiarkan VRAM warm untuk throughput maksimal.
3. **Auto-Fallback:** Jika request meminta mode `"fast"` di mesin tanpa CUDA, otomatis dialihkan ke mode hemat tanpa crash 500.

---

## 2. Rincian Langkah Kerja (Execution Steps)

1. **Definisikan Logika Profil (`api/profiles.py`):**
   - Buat fungsi penentu parameter per profil:
     ```python
     def get_profile_params(profile_name: str, has_cuda: bool):
         if not has_cuda and profile_name == "fast":
             profile_name = "low_resource" # Auto fallback
         
         if profile_name == "low_resource":
             return {
                 "max_chunk_chars": 120,
                 "clear_vram_after_chunk": True,
                 "enable_tf32": False,
             }
         else: # fast
             return {
                 "max_chunk_chars": 240,
                 "clear_vram_after_chunk": False,
                 "enable_tf32": True,
             }
     ```

2. **Dinamis Chunker berdasarkan Profil:**
   - Sambungkan parameter `max_chunk_chars` ke fungsi `chunk_text(text, max_chars=...)` di `core.chunker`.

3. **Routine Pembersihan Memori Pasca Inferensi:**
   - Di mode `low_resource`:
     ```python
     import gc
     import torch
     if torch.cuda.is_available():
         torch.cuda.empty_cache()
     gc.collect()
     ```

4. **Integrasikan ke Request Handling di `server.py`:**
   - Klien dapat menyertakan `"profile": "low_resource"` atau `"profile": "fast"`.
   - Jika tidak diisi, gunakan `settings.api.default_profile` dari `config.yaml`.
   - Sertakan header respon: `X-Profile-Used: low_resource` atau `X-Profile-Used: fast`.

---

## 3. Batasan Ketat (Do NOT Do in This Task)
- ❌ **JANGAN** membuat komputasi GPU crash jika dipanggil di CPU (wajib ada pengujian `torch.cuda.is_available()`).
- ❌ **JANGAN** mengubah default limits di `core/settings.py` yang digunakan oleh Gradio `app.py`.

---

## 4. Wajib Unit Test (Definition of Done)
Sebelum task ini dianggap selesai, tambahkan pengujian di **`tests/test_api_profiles.py`** dan pastikan lulus:

- [ ] `test_profile_low_resource_chunking`: Request naskah panjang dengan profile `low_resource` menghasilkan potongan chunk yang lebih kecil (≤ 120 karakter).
- [ ] `test_profile_fast_chunking`: Request naskah panjang dengan profile `fast` menghasilkan potongan chunk standar (sampai ~240 karakter).
- [ ] `test_profile_cpu_auto_fallback`: Jika CUDA di-mock tidak tersedia (`torch.cuda.is_available() == False`), request dengan `"profile": "fast"` tetap sukses dan header `X-Profile-Used` menunjukkan `low_resource`.
- [ ] `test_invalid_profile_name`: Request dengan nama profile ngawur (misal `"super_sonic"`) mengembalikan status `422 Unprocessable Entity` atau fallback aman ke default.

---

## 5. Perintah Verifikasi
```bash
pytest tests/test_api_profiles.py -v
```
*Syarat lulus: Semua test profil wajib PASS 100%.*
