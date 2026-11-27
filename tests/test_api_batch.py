"""Tests for Task 04: Batch Multi-Segment Synthesis and Audio Download."""
import io
import shutil
from pathlib import Path

import soundfile as sf
from fastapi.testclient import TestClient

from core.settings import Settings
from server import create_app

VALID_API_KEY = "test-secret-key-123"
TEST_OUTPUT_DIR = "outputs/test_api_batch"


def get_test_client():
    settings = Settings()
    settings.api.api_key = VALID_API_KEY
    settings.api.output_dir = TEST_OUTPUT_DIR
    app = create_app(settings=settings, dry_run=True)
    return TestClient(app)


def setup_module():
    # Buat direktori output pengujian
    Path(TEST_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def teardown_module():
    # Bersihkan direktori output pengujian
    if Path(TEST_OUTPUT_DIR).exists():
        shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)


def test_batch_30_segments():
    client = get_test_client()
    segments = [
        {"id": f"scene_{i:02d}", "text": f"Naskah fakta nomor {i} untuk video short."}
        for i in range(1, 31)
    ]
    payload = {
        "voice": "sample_voice",
        "profile": "low_resource",
        "segments": segments,
    }
    resp = client.post(
        "/api/v1/tts/batch",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_segments"] == 30
    assert data["successful_segments"] == 30
    assert data["failed_segments"] == 0
    assert len(data["results"]) == 30

    # Cek setiap segmen memiliki audio_url dan durasi positif
    for item in data["results"]:
        assert item["status"] == "success"
        assert item["audio_url"] is not None
        assert item["duration_s"] > 0


def test_batch_high_capacity_100_segments():
    """Uji kapasitas skala besar (100+ naskah sekaligus)."""
    client = get_test_client()
    segments = [
        {"id": f"seg_{i:03d}", "text": f"Segmen dokumenter babak {i}."}
        for i in range(1, 101)
    ]
    payload = {
        "voice": "sample_voice",
        "profile": "low_resource",
        "segments": segments,
    }
    resp = client.post(
        "/api/v1/tts/batch",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_segments"] == 100
    assert data["successful_segments"] == 100
    assert len(data["results"]) == 100


def test_batch_audio_downloadable():
    client = get_test_client()
    payload = {
        "voice": "sample_voice",
        "segments": [
            {"id": "intro", "text": "Selamat datang di pembukaan."},
            {"id": "outro", "text": "Terima kasih sudah menonton."},
        ],
    }
    resp = client.post(
        "/api/v1/tts/batch",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    intro_url = results[0]["audio_url"]

    # Unduh file audio hasil generate
    down_resp = client.get(intro_url, headers={"X-API-Key": VALID_API_KEY})
    assert down_resp.status_code == 200
    assert down_resp.headers["content-type"] == "audio/wav"

    # Verifikasi integritas audio WAV
    buf = io.BytesIO(down_resp.content)
    wav, sr = sf.read(buf)
    assert len(wav) > 0
    assert sr == 24000


def test_batch_empty_segments():
    client = get_test_client()
    payload = {
        "voice": "sample_voice",
        "segments": [],
    }
    resp = client.post(
        "/api/v1/tts/batch",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 422  # Pydantic min_length=1 validation error


def test_path_traversal_prevention():
    client = get_test_client()
    # Mencoba mengakses path di luar folder yang diizinkan (wajib 403 Forbidden)
    resp = client.get(
        "/api/v1/audio/download/batch_123/..%2F..%2Fconfig.yaml",
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_batch_duplicate_segment_ids():
    client = get_test_client()
    # Dua segmen berbeda sengaja dikirim dengan ID yang sama
    payload = {
        "voice": "sample_voice",
        "segments": [
            {"id": "scene_same", "text": "Naskah pertama dengan ID kembar."},
            {"id": "scene_same", "text": "Naskah kedua dengan ID kembar."},
        ],
    }
    resp = client.post(
        "/api/v1/tts/batch",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    # Pastikan URL download keduanya berbeda sehingga tidak saling menimpa
    url1 = results[0]["audio_url"]
    url2 = results[1]["audio_url"]
    assert url1 != url2
    assert "scene_same.wav" in url1
    assert "scene_same_2.wav" in url2
