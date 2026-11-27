"""Tests for Task 02: Engine Integration, Text Normalizer, and Concurrency Lock."""
import concurrent.futures
import urllib.parse
from fastapi.testclient import TestClient

from core.settings import Settings
from server import create_app

VALID_API_KEY = "test-secret-key-123"


def get_test_client():
    settings = Settings()
    settings.api.api_key = VALID_API_KEY
    app = create_app(settings=settings, dry_run=True)
    return TestClient(app)


def test_normalizer_integrated():
    client = get_test_client()
    payload = {
        "text": "Nomor 123 dengan harga Rp 50.000 jam 14:30 WIB",
        "voice": "sample_voice",
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"

    normalized_header = resp.headers.get("X-Normalized-Text")
    assert normalized_header is not None
    decoded = urllib.parse.unquote(normalized_header)
    # Memastikan angka biasa, angka rupiah, dan jam dinormalisasi ke teks bahasa Indonesia
    assert "seratus dua puluh tiga" in decoded
    assert "lima puluh ribu rupiah" in decoded
    assert "empat belas tiga puluh" in decoded


def test_concurrent_requests_handled():
    client = get_test_client()

    def send_req(i: int):
        payload = {
            "text": f"Naskah pengujian antrean ke-{i}.",
            "voice": "sample_voice",
        }
        return client.post(
            "/api/v1/tts/synthesize",
            json=payload,
            headers={"X-API-Key": VALID_API_KEY},
        )

    # Kirim 5 request secara bersamaan melalui ThreadPool
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_req, i) for i in range(5)]
        responses = [f.result() for f in futures]

    assert len(responses) == 5
    for resp in responses:
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"


def test_voice_not_found():
    client = get_test_client()
    payload = {
        "text": "Uji coba suara tidak ada",
        "voice": "suara_yang_tidak_pernah_ada_xyz999",
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 404
    assert "not found in prompt_audio/" in resp.json()["detail"]


def test_voice_invalid_extension():
    client = get_test_client()
    # Mengirim file non-audio (misal file konfigurasi/teks)
    payload = {
        "text": "Uji coba ekstensi file ilegal",
        "voice": "requirements.txt",
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 400
    assert "Invalid audio format" in resp.json()["detail"]
