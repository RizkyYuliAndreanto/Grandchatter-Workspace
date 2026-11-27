# 📋 TASK 05: Full Hardening, Regresi Penuh, dan Dokumentasi Integrasi
**SDLC Phase:** Fase 4 (Bagian 2) & Fase 5  
**Status:** ✅ COMPLETED  
**Dependencies:** `TASK-04-batch-endpoint-and-downloads.md`  
**Lokasi Dokumen:** `agent/tasks/TASK-05-full-suite-hardening-and-docs.md`  

---

## 1. Tujuan Task
1. Menjalankan pengujian regresi menyeluruh untuk membuktikan bahwa penambahan fitur API tidak merusak 57 unit test bawaan.
2. Memastikan Gradio UI (`app.py`) tetap menyala dan berfungsi normal.
3. Menyediakan dokumentasi integrasi lengkap beserta contoh kode klien (Python, Node.js, cURL) agar siap dihubungkan langsung ke aplikasi eksternal pembuat video.

---

## 2. Rincian Langkah Kerja (Execution Steps)

1. **Jalankan Regresi Penuh (Full Regression):**
   - Jalankan `pytest tests/ -v`.
   - Pastikan **57 unit test lama tetap 100% HIJAU**.
   - Pastikan semua file test API baru (`test_api_mock.py`, `test_api_concurrency.py`, `test_api_profiles.py`, `test_api_batch.py`) juga **100% HIJAU**.

2. **Verifikasi Kemandirian Gradio UI (`app.py`):**
   - Jalankan tes smoke `python app.py --dry-ui` (atau test UI yang ada) untuk memastikan antarmuka browser Gradio tidak terdampak sedikit pun oleh server FastAPI.

3. **Buat File Panduan Integrasi (`agent/CLIENT_INTEGRATION.md` atau `docs/API_CLIENT_GUIDE.md`):**
   - **cURL:** Contoh hit endpoint single dan batch dari terminal / script bash.
   - **Python:** Contoh skrip `requests`/`httpx` untuk mengirim 30 naskah video short dan menyimpan audionya ke folder lokal.
   - **Node.js / TypeScript:** Contoh kode `fetch`/`axios` untuk aplikasi berbasis web/backend JS.

4. **Update README.md (Section Opsional API):**
   - Tambahkan cara menyalakan server API di `README.md`:
     ```bash
     # Menjalankan REST API server lokal
     python server.py --port 8000
     
     # Mode testing tanpa GPU
     python server.py --dry-run
     ```

---

## 3. Batasan Ketat (Do NOT Do in This Task)
- ❌ **JANGAN** menandai task ini selesai jika ada SATU PUN dari 57 unit test lama yang gagal (FAIL/ERROR).
- ❌ **JANGAN** menambahkan ketergantungan (dependencies) berat baru yang tidak perlu ke `requirements.txt`.

---

## 4. Wajib Unit Test & Quality Gate (Definition of Done)
Sebelum task ini dianggap selesai, jalankan seluruh suite pengujian di repo:

```bash
pytest -v
```

- [ ] Seluruh 57 unit test lama lulus (`57 passed`).
- [ ] Seluruh unit test API baru lulus (`N passed`).
- [ ] Total test berstatus hijau: `(57 + N) passed, 0 failed`.
- [ ] Gradio UI diverifikasi tetap independen.
- [ ] Dokumentasi klien teruji dan dapat dieksekusi.

---

## 5. Output Akhir
Fitur REST API dinyatakan **SELESAI & SIAP PRODUKSI (PRODUCTION-READY)** untuk dihubungkan ke aplikasi pembuat video eksternal.
