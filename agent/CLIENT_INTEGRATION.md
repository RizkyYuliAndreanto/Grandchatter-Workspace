# 🔌 PANDUAN INTEGRASI APLIKASI EKSTERNAL (CLIENT GUIDE)
**Target:** Integrasi Aplikasi Video Maker / Shorts / Pipeline Otomatis dengan REST API TTS  
**Lokasi Dokumen:** `agent/CLIENT_INTEGRATION.md`  

---

## 1. Menjalankan Server TTS Lokal

Sebelum aplikasi eksternal Anda menembak API, nyalakan server TTS di terminal:

```bash
# Mode Normal (GPU CUDA aktif)
python server.py --host 127.0.0.1 --port 8000

# Mode Testing Cepat (Dry-run tanpa GPU/model)
python server.py --dry-run --port 8000
```

- **Base URL:** `http://127.0.0.1:8000`
- **Default API Key:** `dev-local-secret-key` *(Dapat diubah di `config.yaml` atau via ENV `TTS_API_KEY`)*
- **Header Autentikasi Wajib:** `X-API-Key: dev-local-secret-key`

---

## 2. Pilihan Profil Perangkat (Hardware Profile)

Klien dapat menyertakan field `"profile"` di body JSON:
- `"profile": "low_resource"` → **Device Kentang** (CPU / GPU VRAM ≤ 4GB). Memangkas chunking (120 char) dan membersihkan memori secara agresif agar laptop tidak freeze.
- `"profile": "fast"` → **Device Dewa** (GPU VRAM ≥ 6GB/8GB+). Kecepatan maksimal, FP16 + TF32 throughput. *(Jika dipanggil di CPU, otomatis fallback aman ke low_resource).*

---

## 3. Contoh Integrasi: Single Segment (`POST /api/v1/tts/synthesize`)

Gunakan endpoint ini untuk preview suara atau merender naskah satu per satu secara langsung (langsung me-return binary audio WAV).

### A. Contoh cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-local-secret-key" \
     -d '{
       "text": "Selamat datang di fakta menarik hari ini. Harga barang ini Rp 50.000 saja.",
       "voice": "sample_voice",
       "profile": "fast",
       "temperature": 0.25,
       "tempo": 1.0,
       "pitch": 0.0
     }' \
     --output "output_scene.wav"
```

### B. Contoh Python (`requests`)
```python
import requests

url = "http://127.0.0.1:8000/api/v1/tts/synthesize"
headers = {
    "X-API-Key": "dev-local-secret-key",
    "Content-Type": "application/json"
}
payload = {
    "text": "Halo! Naskah ini akan langsung dibacakan dengan suara alami.",
    "voice": "sample_voice",
    "profile": "fast",
    "tempo": 1.0
}

response = requests.post(url, json=payload, headers=headers)
if response.status_code == 200:
    with open("hasil_suara.wav", "wb") as f:
        f.write(response.content)
    print("Suara berhasil disimpan! Durasi:", response.headers.get("X-Audio-Duration"), "detik")
else:
    print("Error:", response.status_code, response.text)
```

### C. Contoh Node.js / JavaScript (`fetch` + `fs`)
```javascript
const fs = require('fs');

async function generateSpeech() {
  const response = await fetch("http://127.0.0.1:8000/api/v1/tts/synthesize", {
    method: "POST",
    headers: {
      "X-API-Key": "dev-local-secret-key",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: "Fakta pertama yang wajib kamu ketahui di video short ini.",
      voice: "sample_voice",
      profile: "fast"
    })
  });

  if (response.ok) {
    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    fs.writeFileSync("scene_01.wav", buffer);
    console.log("Audio tersimpan: scene_01.wav");
  } else {
    console.error("Gagal:", response.status, await response.text());
  }
}

generateSpeech();
```

---

## 4. Contoh Integrasi: Batch Multi-Segmen (`POST /api/v1/tts/batch`)

Gunakan endpoint ini untuk memproses **30 script video short sekaligus** (atau **ratusan naskah dokumenter**) dalam 1 kali request HTTP.

### A. Contoh cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tts/batch" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: dev-local-secret-key" \
     -d '{
       "voice": "sample_voice",
       "profile": "low_resource",
       "tempo": 1.0,
       "segments": [
         { "id": "scene_01", "text": "Tahukah Anda fakta pertama ini?" },
         { "id": "scene_02", "text": "Hewan ini mampu bertahan hidup tanpa makan berminggu-minggu." },
         { "id": "scene_03", "text": "Harganya bisa mencapai Rp 50.000.000 per ekor." }
       ]
     }'
```

Response JSON:
```json
{
  "status": "success",
  "batch_id": "batch_a1b2c3d4e5",
  "profile_used": "low_resource",
  "total_segments": 3,
  "successful_segments": 3,
  "failed_segments": 0,
  "results": [
    {
      "id": "scene_01",
      "audio_url": "/api/v1/audio/download/batch_a1b2c3d4e5/scene_01.wav",
      "duration_s": 2.3,
      "status": "success"
    },
    {
      "id": "scene_02",
      "audio_url": "/api/v1/audio/download/batch_a1b2c3d4e5/scene_02.wav",
      "duration_s": 3.8,
      "status": "success"
    },
    {
      "id": "scene_03",
      "audio_url": "/api/v1/audio/download/batch_a1b2c3d4e5/scene_03.wav",
      "duration_s": 3.1,
      "status": "success"
    }
  ]
}
```

### B. Contoh Python: Kirim 30 Naskah & Download Semua File Audio
```python
import os
import requests

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-local-secret-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# 1. Siapkan 30 naskah yang sudah dipecah oleh aplikasi video Anda
segments_data = [
    {"id": f"scene_{i:02d}", "text": f"Ini adalah naskah untuk segmen video ke-{i}."}
    for i in range(1, 31)
]

payload = {
    "voice": "sample_voice",
    "profile": "low_resource",  # atau "fast" jika GPU lega
    "tempo": 1.0,
    "segments": segments_data
}

# 2. Kirim ke Server TTS
print("Mengirim 30 segmen naskah ke TTS Server...")
res = requests.post(f"{BASE_URL}/api/v1/tts/batch", json=payload, headers=HEADERS)

if res.status_code == 200:
    data = res.json()
    print(f"Batch selesai! ID: {data['batch_id']} | Total: {data['successful_segments']}/{data['total_segments']}")
    
    # 3. Download dan simpan masing-masing audio ke folder lokal aplikasi video Anda
    os.makedirs("audio_output", exist_ok=True)
    for seg in data["results"]:
        if seg["status"] == "success":
            download_url = f"{BASE_URL}{seg['audio_url']}"
            audio_data = requests.get(download_url, headers=HEADERS).content
            file_path = f"audio_output/{seg['id']}.wav"
            with open(file_path, "wb") as f:
                f.write(audio_data)
            print(f"  Downloaded: {file_path} ({seg['duration_s']} detik)")
        else:
            print(f"  Segmen {seg['id']} gagal: {seg['error']}")
else:
    print("Error:", res.status_code, res.text)
```

---

## 5. Endpoint Pendukung

### A. Cek Status Server & Model (`GET /health`)
- **URL:** `http://127.0.0.1:8000/health`
- **Auth:** Tidak perlu.
- **Response:**
  ```json
  {
    "status": "ready",
    "model_loaded": true,
    "device": "cuda",
    "default_profile": "low_resource"
  }
  ```

### B. Daftar Suara Tersedia (`GET /api/v1/voices`)
- **URL:** `http://127.0.0.1:8000/api/v1/voices`
- **Auth:** Wajib `X-API-Key`.
- **Response:**
  ```json
  {
    "voices": ["sample_voice", "narator_cowok", "narator_cewek"]
  }
  ```
  *(Anda bisa menambahkan suara referensi baru dengan menyalin file `.wav` ke folder `prompt_audio/`).*
