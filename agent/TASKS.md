# 📋 DAFTAR TASK EKSEKUSI (STEP-BY-STEP WORKFLOW)
**Fitur:** Local REST API Server (Indonesian TTS & Voice Cloning)  
**Status:** READY FOR STAGED EXECUTION  
**Lokasi Dokumen:** `agent/TASKS.md`  

---

## ⚠️ ATURAN EKSEKUSI UNTUK AI AGENT
1. **Dilarang Mengeksekusi Semuanya Sekaligus (Anti-All-At-Once):** AI Agent WAJIB mengeksekusi task satu per satu secara berurutan.
2. **Kewajiban Unit Test:** Setiap task memiliki syarat unit test yang spesifik. AI Agent **DILARANG** melanjutkan ke task berikutnya sebelum unit test task saat ini dibuat dan dinyatakan **PASS 100%**.

---

## 📌 Rangkaian Task

| No | File Task | Fokus Utama | Wajib Unit Test | Status |
|:---:|---|---|---|:---:|
| **01** | [TASK-01-mock-server-and-auth.md](tasks/TASK-01-mock-server-and-auth.md) | FastAPI skeleton, Auth `X-API-Key`, Pydantic Schemas, `--dry-run` Mock | `tests/test_api_mock.py` | ✅ Completed |
| **02** | [TASK-02-concurrency-and-engine-adapter.md](tasks/TASK-02-concurrency-and-engine-adapter.md) | Normalizer naskah Indo, Engine adapter, `asyncio.Lock` anti-CUDA OOM | `tests/test_api_concurrency.py` | ✅ Completed |
| **03** | [TASK-03-dual-hardware-profiles.md](tasks/TASK-03-dual-hardware-profiles.md) | Dual Profile (Kentang / `low_resource` vs Dewa / `fast`) + auto-fallback | `tests/test_api_profiles.py` | ✅ Completed |
| **04** | [TASK-04-batch-endpoint-and-downloads.md](tasks/TASK-04-batch-endpoint-and-downloads.md) | Endpoint multi-segmen (30 naskah short) + file download per segmen | `tests/test_api_batch.py` | ✅ Completed |
| **05** | [TASK-05-full-suite-hardening-and-docs.md](tasks/TASK-05-full-suite-hardening-and-docs.md) | Full regression (57 tests lama + tests baru PASS), dokumentasi klien | `pytest -v` (Semua Hijau) | ✅ Completed |

---

## 🏁 Alur Kerja Saat Memulai:
Ketika Anda memberikan instruksi kepada AI Agent (misalnya: *"Kerjakan Task 01"*), AI Agent akan:
1. Membaca [agent/tasks/TASK-01-mock-server-and-auth.md](tasks/TASK-01-mock-server-and-auth.md).
2. Mengeksekusi hanya poin-poin yang diminta di Task 01.
3. Menulis unit test yang disyaratkan di `tests/test_api_mock.py`.
4. Menjalankan pengujian `pytest tests/test_api_mock.py -v`.
5. Melaporkan hasil pengujian kepada Anda sebelum meminta izin lanjut ke Task 02.
