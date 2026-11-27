# 🤖 AGENT MASTER DIRECTIVE & EXECUTION PLAYBOOK
**Target Feature:** Local REST API Server for External Applications (Video Shorts & Multi-Segment Automation)  
**Location:** `agent/agent.md`  
**Status:** ACTIVE & BINDING  
**Target Platform:** Windows 11 / Local Workstation (CPU & GPU)

---

## ⚠️ MANDATORY RULE BEFORE EXECUTION (AI AGENT MUST READ)
> **SETIAP AI AGENT YANG DIBERIKAN TUGAS MENGEKSEKUSI FITUR REST API INI WAJIB MEMBACA DAN MEMATUHI SELURUH DOKUMEN DALAM FOLDER `agent/` TERLEBIH DAHULU.**  
> Dokumen telah dipecah menjadi 4 modul terpisah agar mudah ditinjau dan divalidasi:
> 
> 1. [PRD.md](PRD.md) — Kebutuhan produk, use case video short 60s & dokumenter, in-scope vs out-of-scope.
> 2. [DEV.md](DEV.md) — Arsitektur teknis, spesifikasi endpoint, schema request/response, dan profil kentang vs dewa.
> 3. [SDLC.md](SDLC.md) — Roadmap pengerjaan 5 fase bertahap dari mock hingga hardening.
> 4. [GUARDRAILS.md](GUARDRAILS.md) — Aturan ketat, proteksi VRAM, zero-regression 57 tests, dan batasan cakupan.
> 5. [TASKS.md](TASKS.md) & [tasks/](tasks/) — Rangkaian 5 task bertahap (wajib lulus unit test per task).

---

## 🗺️ Ringkasan Cepat Arsitektur

```
[Aplikasi Eksternal (Video Shorts / 30 Naskah)]
        │
        │ HTTP (Header: X-API-Key)
        ▼
[server.py (FastAPI)] ◄─── Dijalankan terpisah dari GUI (app.py)
        │
        ├──► 🛡️ Auth Check (X-API-Key)
        ├──► 🔒 Concurrency Lock (asyncio.Lock anti-CUDA OOM)
        ├──► 🎛️ Profile Selector (low_resource "kentang" vs fast "dewa")
        ├──► 🇮🇩 core.normalizer (Normalisasi naskah Indonesia)
        └──► 🎙️ core.synthesizer (Generate WAV audio)
```

---

## 📋 Checklist Eksekusi Sesuai SDLC

Semua fase telah berhasil dieksekusi dan diverifikasi secara bertahap:

- [x] **Fase 1: Desain Kontrak & Mock Server**
  - Schema Pydantic siap diuji (`api/schemas.py`).
  - Auth dependency `X-API-Key` aktif (`api/auth.py`).
  - Server dapat berjalan dalam mode `--dry-run` tanpa GPU (`tests/test_api_mock.py`).
- [x] **Fase 2: Engine Integration & Concurrency Lock**
  - Terhubung dengan adapter engine (`api/engine.py`) dan normalizer teks bahasa Indonesia.
  - Inferensi GPU diproteksi `asyncio.Lock()` anti-CUDA OOM (`tests/test_api_concurrency.py`).
- [x] **Fase 3: Implementasi Dual Profile**
  - Mode `low_resource` (chunker hemat 120 char + VRAM clearing) berfungsi.
  - Mode `fast` (chunker standar 240 char + FP16/TF32 throughput) berfungsi.
  - Auto-fallback jika GPU tidak terdeteksi (`tests/test_api_profiles.py`).
- [x] **Fase 4: Testing & Hardening**
  - Test batch multi-segmen (30 naskah & skala 100 naskah) dan proteksi path-traversal dibuat (`tests/test_api_batch.py`).
  - **Seluruh 57 unit test lama tetap PASS**.
- [x] **Fase 5: Dokumentasi & Contoh Pemanggil**
  - Panduan integrasi cURL, Python, dan Node.js siap digunakan di [`agent/CLIENT_INTEGRATION.md`](CLIENT_INTEGRATION.md).
  - Update panduan eksekusi lokal pada [`README.md`](../README.md).

---

## 🚨 Peringatan Pelanggaran Guardrails
Jika AI Agent terbukti:
1. Memodifikasi `app.py` hingga merusak fungsionalitas Gradio UI,
2. Menghilangkan atau merusak salah satu dari 57 unit test lama,
3. Menjalankan inferensi PyTorch paralel tanpa proteksi antrean (resiko CUDA OOM),
4. Memasukkan kode video editing/stitching ke dalam repositori ini,

Maka hasil kerja dianggap **GAGAL (REJECTED)** dan harus dikembalikan ke commit sebelumnya.
