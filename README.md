<div align="center">

# 🎙️ Grandchatter Workspace

**Indonesian TTS & Voice Cloning Studio — Text-to-Speech Bahasa Indonesia + zero-shot voice cloning, berjalan penuh di GPU Kaggle, dikendalikan dari browser laptop Anda.**

[![Repo](https://img.shields.io/badge/GitHub-RizkyYuliAndreanto%2FGrandchatter--Workspace-181717?logo=github&logoColor=white)](https://github.com/RizkyYuliAndreanto/Grandchatter-Workspace)

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-Chatterbox-EE4C2C?logo=pytorch&logoColor=white)
![Gradio](https://img.shields.io/badge/UI-Gradio-orange?logo=gradio&logoColor=white)
![Kaggle](https://img.shields.io/badge/Compute-Kaggle%20GPU-20BEFF?logo=kaggle&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-57%20passed-brightgreen)

</div>

---

## ✨ Apa Ini?

Naskah panjang masuk → audio suara natural keluar. Semua pemrosesan model berjalan di **GPU gratis Kaggle (P100/T4 16GB)**, laptop Anda hanya membuka satu halaman web — tanpa install berat, tanpa GPU sendiri, tanpa edit kode untuk mengubah parameter.

```
 Naskah mentah ──► [ Normalizer ] ──► [ Chunker ≤250 char ] ──► [ TTS per chunk (Kaggle GPU) ]
                                                                        │
 Browser laptop ◄── [ Download ZIP ] ◄── [ Merge + Normalize ] ◄── [ Tempo · Pitch · Fade ]
```

## 🚀 Fitur Utama

| | Fitur | Detail |
|---|---|---|
| 🧠 | **Voice Cloning Zero-shot** | Cukup 5–10 detik sampel suara — timbre dipertahankan di seluruh naskah |
| 🇮🇩 | **Fine-tuned Bahasa Indonesia** | Checkpoint [`grandhigh/Chatterbox-TTS-Indonesian`](https://huggingface.co/grandhigh/Chatterbox-TTS-Indonesian) dimuat ke base model |
| 🔢 | **Normalizer Bahasa Indonesia** | `Rp 50.000` → *lima puluh ribu rupiah* · `0812...` → dieja per digit · `14:30 WIB` → *empat belas tiga puluh W I B* |
| 🎛️ | **Kontrol Penuh dari Slider** | Temperature, tempo, pitch (±4 semitone), jeda antar kalimat — **tanpa sentuh kode** |
| 🛡️ | **Crash-Safe Batch** | Tiap chunk langsung ke disk; run terputus = *resume otomatis* dari chunk terakhir |
| 🔁 | **Anti-Runtuh** | Chunk gagal di-retry 1× (temperature bump), dicatat di manifest, run tetap selesai |
| 🌐 | **3 Mode Tunnel + Lokal** | `local` (tanpa tunnel, laptop-only) · `share` (zero-setup) · `ngrok` (domain statis) · `cloudflare` (quick tunnel) — via config, semua ber-password |
| 💾 | **Export Sekali Klik** | ZIP berisi final WAV + semua chunk + manifest.json |
| 🧪 | **57 Unit Test** | Pipeline teks, DSP, batch, resume, tunnel — semua teruji |

## 📦 Instalasi

### Prasyarat
- Akun [Kaggle](https://www.kaggle.com) (kuota GPU gratis 30 jam/minggu)
- GitHub repo privat (tempat kode ini disimpan)

### Jalankan dalam 3 Cell

1. **Upload** `launcher.ipynb` ke Kaggle → Settings kanan: **Accelerator = GPU P100/T4** · **Internet = ON**
2. **Run Cell 1** — clone repo + install (ikuti pola setup yang terbukti untuk Kaggle: `torch` bawaan Kaggle tidak diganti)
3. **Run Cell 2** — tulis config (password tunnel di sini; kosong = auto-generate)
4. **Run Cell 3** — model load ±2 menit → URL `*.gradio.live` + password muncul di output
5. **Buka dari browser laptop/HP** → login → upload suara referensi → Generate 🎧

> ⚠️ **Jangan pakai *Save & Run All*** (headless — tunnel tidak jalan). Tab browser harus tetap terbuka selama sesi.

## 🎚️ Parameter

| Parameter | Rentang | Default | Efek |
|---|---:|---:|---|
| Temperature | 0.1 – 1.0 | 0.25 | Variasi intonasi (rendah = stabil & konsisten aksen) |
| Tempo | 0.8x – 1.5x | 1.0x | Kecepatan bicara, **pitch tetap** (phase-vocoder) |
| Pitch | −4 – +4 | 0 | Nada suara dalam semitone, durasi tetap |
| Gap | 0.1 – 1.0 s | 0.3 s | Jeda antar kalimat (re-merge = gratis, tanpa GPU) |

## 🏗️ Arsitektur

```
indotts-kaggle/
├── app.py                  # Gradio UI + entry point (--dry-ui tanpa GPU; HF_HOME → hf-cache/)
├── launcher.ipynb          # 3-cell Kaggle notebook
├── hf-cache/               # model lokal ±2 GB (gitignored — drive project, bukan C:)
├── core/
│   ├── normalizer.py       # angka/rupiah/HP/jam (14:30 → "empat belas tiga puluh")/akronim
│   ├── chunker.py          # split kalimat → koma → kata; ≤250 char anti-repetisi
│   ├── batch.py            # loop chunk · resume-by-hash · retry · manifest
│   ├── audio_fx.py         # tempo/pitch/fade/merge/normalize — murni float32
│   ├── synthesizer.py      # 1 model instance + fine-tune + conditioning cache + fp16 opsional
│   ├── export.py           # ZIP run folder
│   └── settings.py         # config.yaml + LIMITS (sumber kebenaran rentang)
├── tunnels/                # local · share · ngrok · cloudflare + fallback otomatis
└── tests/                  # 57 test — hijau tanpa GPU
```

**Urutan pipeline terkunci:** normalisasi → chunking → TTS → tempo → pitch → fade → merge → normalize. Setiap urutan punya alasan — dijabarkan di [`tasks/flows/flow-pipeline.md`](tasks/flows/flow-pipeline.md).

## 🎯 Motivasi

> **Hardware bukan alasan untuk tidak memproduksi audio berkualitas.**

Studio TTS lokal biasanya menuntut GPU kelas atas — realitasnya, tidak semua orang punya RTX 4090 di meja kerja. Project ini lahir dari kondisi yang sangat umum di Indonesia: laptop kerja spesifikasi menengah dengan GPU entry-level yang tidak cukup menjalankan inferensi TTS secara nyaman, sementara kebutuhannya nyata — voice-over naskah 10–30 menit untuk konten, narasi, dan materi edukasi.

Solusinya bukan menurunkan kualitas, melainkan **memindahkan beban komputasi ke tempat yang tepat**: GPU P100/T4 16GB gratis di Kaggle (30 jam/minggu), dikendalikan lewat browser dari laptop apa pun. Pipeline dibangun dengan disiplin engineering yang sama seperti sistem produksi sungguhan — chunking anti-repetisi, resume otomatis anti-kegagalan, kualitas DSP yang dijaga, dan 57 unit test — karena **keterbatasan sumber daya membatasi hardware yang dipakai, bukan standar cara membangunnya.**

## 🧪 Development Lokal

```powershell
git clone https://github.com/RizkyYuliAndreanto/Grandchatter-Workspace.git
cd Grandchatter-Workspace
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pytest tests\              # 54 test, tanpa GPU
python app.py --dry-ui     # UI penuh dengan mock synthesizer (tanpa model)
```

### 💻 Run di Laptop (model di-download lokal, tanpa Kaggle)

Bisa jalan langsung di laptop — model diunduh sekali ke `hf-cache/` di folder
project (±2 GB) lalu dipakai offline selamanya.

1. Copy `config.example.yaml` → `config.yaml`, lalu sesuaikan untuk laptop low-end:

```yaml
model:
  device: "cpu"        # paksa CPU (hemat RAM/VRAM, tidak load ke GPU 4GB)
  fp16: false
tunnel:
  mode: "local"        # tanpa tunnel — buka http://127.0.0.1:7860 di browser
  password: "passwordku"
```

2. `python app.py` → buka `http://127.0.0.1:7860` (login: `user` + password config).

**Ekspektasi CPU (Ryzen 5 5600, 16GB RAM):** RTF ≈ 3–6× (audio 1 menit ≈ 3–6 menit
proses). Cukup untuk naskah pendek & proof-of-quality; naskah 10–30 menit tetap
disarankan ke Kaggle GPU (RTF ≈ 0.15×). Jika RAM mepet: tutup aplikasi lain,
dan tetap `device: "cpu"` — auto-detect hanya akan memakai GPU 4GB jika cukup.

> **Mode `local` vs `share`:** `local` = hanya bisa diakses dari laptop itu
> (tercepat, paling aman). `share` = membuka tunnel publik `*.gradio.live`
> (untuk mengakses dari HP/perangkat lain).

## 📄 Dokumentasi

| File | Isi |
|---|---|
| [`PRD.md`](../PRD.md) | Sumber kebenaran fitur + 10 acceptance criteria |
| [`PROGRESS.md`](../PROGRESS.md) | Tracker lintas-AI: status task, keputusan, temuan API |
| [`tasks/`](tasks/) | 15 task file rinci: langkah, wajib/dilarang, konsekuensi |
| [`TECH_STACK.md`](../TECH_STACK.md) | Dependency + keputusan teknis terkunci |

## ⚠️ Batas yang Perlu Tahu

- **Ephemeral** — file Kaggle hilang saat sesi mati; download ZIP sebelum menutup tab
- **Kuota** — 30 jam GPU/minggu; 1 run produksi 10 menit audio ≈ 1.5 jam GPU
- **Link berubah** — URL tunnel baru setiap sesi (kecuali ngrok static domain)
- **Auth wajib** — link tunnel publik; tanpa password orang lain bisa memakai kuota Anda

---

<div align="center">

*Chatterbox TTS fine-tune — dari naskah ke suara Indonesia.* 🇮🇩

</div>

---

## 🙏 Kredit Model

| | Model | Peran | Link |
|---|---|---|---|
| 🧠 | **Chatterbox-TTS** | Base model TTS + voice cloning (Resemble AI) | [GitHub](https://github.com/resemble-ai/chatterbox) · [HuggingFace](https://huggingface.co/ResembleAI/chatterbox) |
| 🇮🇩 | **grandhigh** | Fine-tuning Bahasa Indonesia (`t3_cfg.safetensors`) | [HuggingFace](https://huggingface.co/grandhigh/Chatterbox-TTS-Indonesian) |

> Base model **Chatterbox** dibangun oleh [Resemble AI](https://resemble.ai); kemampuan Bahasa Indonesia datang dari checkpoint fine-tune **`grandhigh/Chatterbox-TTS-Indonesian`** yang dimuat ke dalam base instance melalui `model.t3.load_state_dict`. Terima kasih kepada keduanya — proyek ini hanya membungkusnya menjadi workflow produksi. 🎙️
