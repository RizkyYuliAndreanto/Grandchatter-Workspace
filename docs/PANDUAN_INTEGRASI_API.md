# 🔌 PANDUAN INTEGRASI APLIKASI EKSTERNAL (API GUIDE)
**Grandchatter Workspace — Indonesian TTS & Voice Cloning Studio**  
**Dokumentasi:** Cara Aplikasi Eksternal Melakukan Hit & Menggunakan REST API TTS  
**Lokasi Dokumen:** `docs/PANDUAN_INTEGRASI_API.md`

---

## 🎯 Konsep Kerja & Pembagian Tugas

Dalam alur produksi konten otomatis (seperti **Video Short 60 detik berisi 30 baris naskah**, atau **video dokumenter panjang**):

- **Tugas Aplikasi Eksternal Anda:**
  1. Memotong naskah sesuai kebutuhan scene / timeline video.
  2. Mengirim naskah teks ke server TTS via HTTP REST API.
  3. Menerima file audio WAV dari server TTS.
  4. Menyusun file audio ke timeline video (editing, subtitle, latar musik, dsb).
- **Tugas Server TTS Ini (Audio Factory):**
  1. Memvalidasi API Key (`X-API-Key`).
  2. Menormalisasi naskah bahasa Indonesia (angka, uang rupiah, jam digital, akronim) secara otomatis.
  3. Mensintesis audio menggunakan model AI dengan timbre suara referensi (voice cloning).
  4. Mengatur efek audio DSP (tempo, pitch, micro-fade).
  5. Mengembalikan binary stream audio atau link unduhan per segmen.

```
┌─────────────────────────────────┐
│     Aplikasi Eksternal Anda     │
│ (Video Maker / Bot / Generator) │
└────────────────┬────────────────┘
                 │
                 │ 1. Kirim Naskah JSON + X-API-Key
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                       TTS REST SERVER                       │
│ 1. Cek Auth (X-API-Key)                                     │
│ 2. Normalisasi Teks Indo ("Rp 50.000" -> "lima puluh ribu") │
│ 3. Antrean Inferensi AI Aman (asyncio.Lock anti-CUDA OOM)  │
│ 4. Eksekusi Profil Hardware (low_resource vs fast)          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ 2. Kembalikan Audio WAV / Link Segmen
                 ▼
┌─────────────────────────────────┐
│     Aplikasi Eksternal Anda     │
│ (Memasang WAV ke Timeline Video)│
└─────────────────────────────────┘
```

---

## 🔐 1. Informasi Server & Autentikasi

- **Base URL Server Lokal:** `http://127.0.0.1:8000`
- **Swagger UI (Uji Coba di Browser):** `http://127.0.0.1:8000/docs`
- **Header Autentikasi Wajib:**
  ```http
  X-API-Key: dev-local-secret-key
  Content-Type: application/json
  ```
  *(API Key dapat diubah di file `config.yaml` atau melalui environment variable `TTS_API_KEY`).*

---

## 🎛️ 2. Pemilihan Profil Hardware (`profile`)

Klien dapat menyertakan parameter `"profile"` di body JSON untuk menyesuaikan performa dengan spesifikasi komputer yang menjalankan server TTS:

| Nilai Profil | Target Perangkat | Karakteristik Teknis |
|---|---|---|
| `"low_resource"` *(Default)* | **Device Kentang:** CPU biasa atau GPU VRAM kecil (≤ 4GB seperti GTX 1650 / RTX 3050 Laptop). | Potongan naskah diperpendek (maksimal 120 karakter) dan memori VRAM/RAM dibersihkan secara agresif (`gc.collect()` + `empty_cache()`) setiap selesai 1 chunk agar laptop tidak panas atau hang. |
| `"fast"` | **Device Dewa:** GPU VRAM lega (≥ 6GB/8GB+ seperti RTX 3060, 4070, 4090). | Potongan naskah standar (240 karakter), akselerasi TF32 + FP16 aktif untuk kecepatan maksimal. |

> **Fitur Auto-Fallback:** Jika aplikasi eksternal meminta profil `"fast"` namun server sedang berjalan di laptop tanpa GPU NVIDIA (CPU-only), server secara otomatis akan beralih ke mode hemat (`low_resource`) tanpa menghasilkan error.

---

## 📡 3. Spesifikasi Lengkap Endpoint

### 🔹 Endpoint 1: Single Segment Direct Audio (`POST /api/v1/tts/synthesize`)
Gunakan endpoint ini untuk mensintesis 1 baris/segmen naskah secara langsung. Server langsung mengembalikan **binary audio WAV stream** yang bisa langsung diputar atau disimpan ke file.

- **URL:** `POST /api/v1/tts/synthesize`
- **Headers:** `X-API-Key: <secret_key>`, `Content-Type: application/json`
- **Request Body (JSON):**
  ```json
  {
    "text": "Selamat datang di fakta menarik part satu. Harganya Rp 50.000 saja.",
    "voice": "sample_voice",
    "profile": "fast",
    "temperature": 0.25,
    "tempo": 1.0,
    "pitch": 0.0
  }
  ```
- **Response Headers:**
  - `Content-Type: audio/wav`
  - `X-Audio-Duration: 3.4` (Durasi audio dalam detik)
  - `X-Audio-Samplerate: 24000` (Sample rate WAV)
  - `X-Audio-Chunks: 1` (Jumlah potongan naskah)
  - `X-Profile-Used: fast` (Profil yang digunakan)
  - `X-Normalized-Text: ...` (Teks naskah yang sudah dibersihkan/dieja, URL-encoded)
- **Response Body:** Binary WAV audio file.

---

### 🔹 Endpoint 2: Batch Multi-Segmen (`POST /api/v1/tts/batch`)
Gunakan endpoint ini untuk mengirim **30 script video short sekaligus** atau **ratusan naskah dokumenter** dalam 1 kali HTTP request.

- **URL:** `POST /api/v1/tts/batch`
- **Headers:** `X-API-Key: <secret_key>`, `Content-Type: application/json`
- **Request Body (JSON):**
  ```json
  {
    "voice": "sample_voice",
    "profile": "low_resource",
    "tempo": 1.0,
    "pitch": 0.0,
    "temperature": 0.25,
    "segments": [
      { "id": "scene_01", "text": "Fakta pertama yang belum banyak orang tahu." },
      { "id": "scene_02", "text": "Hewan ini mampu bertahan hidup tanpa makan berbulan-bulan.", "tempo": 1.1 },
      { "id": "scene_03", "text": "Di tahun 1990an, populasi mereka mencapai 500.000 ekor." }
    ]
  }
  ```
- **Response Body (JSON):**
  ```json
  {
    "status": "success",
    "batch_id": "batch_8f3a12b4cd",
    "profile_used": "low_resource",
    "total_segments": 3,
    "successful_segments": 3,
    "failed_segments": 0,
    "results": [
      {
        "id": "scene_01",
        "audio_url": "/api/v1/audio/download/batch_8f3a12b4cd/scene_01.wav",
        "duration_s": 2.4,
        "status": "success",
        "error": null
      },
      {
        "id": "scene_02",
        "audio_url": "/api/v1/audio/download/batch_8f3a12b4cd/scene_02.wav",
        "duration_s": 3.1,
        "status": "success",
        "error": null
      },
      {
        "id": "scene_03",
        "audio_url": "/api/v1/audio/download/batch_8f3a12b4cd/scene_03.wav",
        "duration_s": 2.8,
        "status": "success",
        "error": null
      }
    ]
  }
  ```

---

### 🔹 Endpoint 3: Unduh File Audio Batch (`GET /api/v1/audio/download/{batch_id}/{filename}`)
Mengunduh file audio WAV hasil proses batch berdasarkan `audio_url` yang diterima.

- **URL:** `GET /api/v1/audio/download/{batch_id}/{filename}`
- **Headers:** `X-API-Key: <secret_key>`
- **Response:** Binary audio file (`Content-Type: audio/wav`).

---

### 🔹 Endpoint 4: Daftar Suara yang Tersedia (`GET /api/v1/voices`)
Mengetahui nama-nama preset suara yang tersedia di server (file di folder `prompt_audio/`).

- **URL:** `GET /api/v1/voices`
- **Headers:** `X-API-Key: <secret_key>`
- **Response (JSON):**
  ```json
  {
    "voices": ["sample_voice", "narator_cowok", "narator_cewek"]
  }
  ```

---

### 🔹 Endpoint 5: Cek Status Server (`GET /health`)
Memeriksa apakah server siap dan mengetahui profil hardware yang aktif (tidak memerlukan API Key).

- **URL:** `GET /health`
- **Response (JSON):**
  ```json
  {
    "status": "ready",
    "model_loaded": true,
    "device": "cuda",
    "default_profile": "fast"
  }
  ```

---

## 💻 4. Contoh Kode Integrasi (Copy-Paste Ready)

### A. Python: Eksekusi 30 Naskah Video Short Sekaligus
Contoh skrip otomatis untuk mengirim 30 baris naskah, menunggu proses selesai, dan langsung mengunduh 30 file audio ke folder lokal:

```python
import os
import requests

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-local-secret-key"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# 1. Daftar 30 naskah dari aplikasi video short Anda
naskah_list = [
    "Tahukah Anda fakta mencengangkan tentang lautan kita?",
    "Lebih dari delapan puluh persen lautan belum pernah dijelajahi manusia.",
    "Di kedalaman seribu meter, cahaya matahari tidak bisa menembus air sama sekali.",
    # ... tambahkan hingga 30 naskah
]

segments = [
    {"id": f"scene_{i+1:02d}", "text": text}
    for i, text in enumerate(naskah_list)
]

payload = {
    "voice": "sample_voice",
    "profile": "low_resource",  # atau "fast" jika GPU Anda lega
    "tempo": 1.0,
    "segments": segments
}

print(f"🚀 Mengirim {len(segments)} segmen naskah ke Server TTS...")
response = requests.post(f"{BASE_URL}/api/v1/tts/batch", json=payload, headers=HEADERS)

if response.status_code == 200:
    batch_data = response.json()
    print(f"✅ Batch Selesai! Batch ID: {batch_data['batch_id']}")
    print(f"   Sukses: {batch_data['successful_segments']}/{batch_data['total_segments']}")

    # 2. Simpan setiap audio ke folder hasil untuk disatukan ke video
    output_dir = "hasil_audio_short"
    os.makedirs(output_dir, exist_ok=True)

    for item in batch_data["results"]:
        if item["status"] == "success":
            audio_url = f"{BASE_URL}{item['audio_url']}"
            audio_res = requests.get(audio_url, headers=HEADERS)
            file_dest = os.path.join(output_dir, f"{item['id']}.wav")
            with open(file_dest, "wb") as f:
                f.write(audio_res.content)
            print(f"   💾 Tersimpan: {file_dest} ({item['duration_s']} detik)")
        else:
            print(f"   ❌ Gagal pada {item['id']}: {item['error']}")
else:
    print("❌ Request Error:", response.status_code, response.text)
```

---

### B. JavaScript / Node.js: Hit Per Segmen (Single Line)
Contoh pemanggilan dari backend Node.js (Express/Next.js/Electron) menggunakan `fetch`:

```javascript
const fs = require('fs');

async function synthesizeLine(sceneId, text) {
  const url = "http://127.0.0.1:8000/api/v1/tts/synthesize";
  const headers = {
    "X-API-Key": "dev-local-secret-key",
    "Content-Type": "application/json"
  };

  const body = {
    text: text,
    voice: "sample_voice",
    profile: "low_resource",
    tempo: 1.0
  };

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      throw new Error(`HTTP Error: ${res.status} - ${await res.text()}`);
    }

    const duration = res.headers.get("X-Audio-Duration");
    const arrayBuffer = await res.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const filename = `${sceneId}.wav`;
    fs.writeFileSync(filename, buffer);
    console.log(`✅ File tersimpan: ${filename} (Durasi: ${duration} detik)`);
    return { filename, duration };
  } catch (err) {
    console.error(`❌ Gagal pada ${sceneId}:`, err.message);
  }
}

// Jalankan sintesis
synthesizeLine("scene_01", "Halo semuanya, selamat datang di channel fakta singkat!");
```

---

### C. cURL (Terminal / Bash Script)
Contoh pemanggilan cepat dari shell Linux / Mac / Git Bash:

```bash
# 1. Single synthesis langsung simpan ke output.wav
curl -X POST "http://127.0.0.1:8000/api/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-local-secret-key" \
     -d '{
       "text": "Naskah pengujian langsung dari cURL terminal.",
       "voice": "sample_voice",
       "profile": "fast"
     }' \
     --output "output.wav"

# 2. Batch request multi-segmen
curl -X POST "http://127.0.0.1:8000/api/v1/tts/batch" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-local-secret-key" \
     -d '{
       "voice": "sample_voice",
       "segments": [
         {"id": "s1", "text": "Segmen satu video."},
         {"id": "s2", "text": "Segmen dua video."}
       ]
     }'
```

---

## ⚠️ 5. Kode Status HTTP & Penanganan Masalah

| Kode Status | Arti | Penyebab Umum & Solusi |
|---|---|---|
| **`200 OK`** | Berhasil | Audio berhasil di-generate atau diunduh. |
| **`400 Bad Request`** | Parameter Salah | File audio referensi tidak berformat `.wav`/`.mp3`, teks kosong setelah normalisasi, atau parameter ID tidak valid. |
| **`401 Unauthorized`** | Kunci Ditolak | Header `X-API-Key` tidak ada atau salah. Cek nilai key di `config.yaml`. |
| **`403 Forbidden`** | Akses Dilarang | Terdeteksi upaya path traversal (`..` atau manipulasi path) saat memanggil endpoint download audio. |
| **`404 Not Found`** | Tidak Ditemukan | Nama voice tidak ada di folder `prompt_audio/` atau file audio batch belum dibuat/sudah terhapus. |
| **`422 Unprocessable`** | Validasi Gagal | Format payload JSON tidak sesuai (misal: array `segments: []` kosong, nilai tempo di luar 0.8–1.5, atau nama profile tidak dikenal). |

---

## 💡 6. Tips Integrasi Maksimal
1. **Pemberian ID Segmen yang Terurut:** Gunakan format ID zero-padded seperti `"scene_01"`, `"scene_02"` hingga `"scene_30"`. Ini memudahkan aplikasi eksternal Anda membaca dan menyusun audio ke timeline video sesuai urutan abjad.
2. **Preset Suara Baru:** Cukup masukkan file rekaman audio orang bersih berdurasi 5–10 detik ke folder `prompt_audio/suara_baru.wav`. Di payload API, Anda tinggal memanggil `"voice": "suara_baru"`.
3. **Efisiensi Batch:** Untuk video short 60s, kirim seluruh 30 naskah dalam satu request `POST /api/v1/tts/batch`. Ini jauh lebih hemat overhead jaringan daripada melakukan 30 kali HTTP request terpisah.
