# 🛡️ GUARDRAILS & ATURAN KETAT
**Fitur:** Local REST API Server (Indonesian TTS & Voice Cloning)  
**Status:** BINDING & ENFORCED  
**Lokasi Dokumen:** `agent/GUARDRAILS.md`  

---

## ⚠️ PERINGATAN UNTUK AI AGENT
Dokumen ini memuat batasan absolut (invariants) yang **TIDAK BOLEH DILANGGAR** dalam kondisi apa pun saat mengembangkan atau memodifikasi fitur REST API.

---

### 🚫 Guardrail 1: Larangan Mengubah / Merusak Gradio UI (`app.py`)
1. File `app.py` adalah milik antarmuka GUI Gradio untuk testing dan voice cloning manual.
2. Server REST API **HARUS BERDIRI SENDIRI** di file terpisah (misalnya `server.py` dan paket `api/`).
3. Dilarang memasang kode backend API langsung ke dalam file `app.py`.
4. Keduanya boleh berbagi modul inti di folder `core/`, tetapi tidak boleh saling bergantung secara langsung (*loose coupling*).

---

### 🚫 Guardrail 2: Zero Regression (57 Unit Test Wajib Tetap Hijau)
1. Repositori ini memiliki 57 unit test yang sudah teruji di folder `tests/`.
2. Penambahan fitur API tidak boleh memodifikasi atau menghapus unit test yang sudah ada tanpa izin tertulis.
3. Sebelum pekerjaan dinyatakan selesai, jalankan `pytest`:
   - Seluruh 57 test lama **WAJIB PASS**.
   - Test baru (`tests/test_api.py`) **WAJIB PASS**.

---

### 🚫 Guardrail 3: Proteksi Memory & GPU Concurrency (Anti-Crash OOM)
1. Model deep learning PyTorch sangat rentan terhadap *CUDA Out Of Memory* jika di-hit secara paralel oleh banyak request.
2. **Aturan Mutlak:** Akses ke inferensi model (`Synthesizer.synthesize` atau batch generator) **WAJIB** dilindungi oleh `asyncio.Lock()` atau antrean sekuensial.
3. Dilarang menjalankan inferensi GPU paralel tak terbatas di mesin lokal.

---

### 🚫 Guardrail 4: Keamanan API Key & Validasi Cepat (Fast-Fail)
1. Validasi header `X-API-Key` harus dieksekusi di lapisan pertama (Middleware / Dependency).
2. Jika API Key tidak ada atau salah, server harus langsung merespons `401 Unauthorized` dalam hitungan milidetik.
3. Dilarang membiarkan request yang tidak sah menjalankan pembersihan teks (normalizer), pembacaan file disk, atau inferensi model.

---

### 🚫 Guardrail 5: Fail-Safe Profile (Graceful Degradation)
1. Jika klien meminta profil `"fast"` namun sistem dijalankan pada lingkungan tanpa GPU (CPU-only), server dilarang melempar error `500 Internal Server Error`.
2. Server harus otomatis melakukan *fallback* ke mode CPU / `low_resource` secara aman dan tetap mengembalikan audio.

---

### 🚫 Guardrail 6: Batasan Tanggung Jawab (Scope Boundary)
1. Server TTS ini adalah **Audio Factory**, bukan Video Editor.
2. Dilarang menambahkan logika penggabungan video (FFmpeg video rendering, overlay subtitle, timeline editing) ke dalam repositori ini.
3. Tanggung jawab server berakhir ketika file audio berkualitas tinggi berhasil disintesis dan dikembalikan ke aplikasi eksternal.
