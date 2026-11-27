"""Tests for Task 01: Mock Server, Schemas, and API Key Authentication."""
import io
import soundfile as sf
from fastapi.testclient import TestClient

from core.settings import Settings
from server import create_app

VALID_API_KEY = "test-secret-key-123"


def get_test_client():
    settings = Settings()
    settings.api.api_key = VALID_API_KEY
    app = create_app(settings=settings, dry_run=True)
    return TestClient(app)


def test_health_endpoint():
    client = get_test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["model_loaded"] is True
    assert data["device"] == "mock-cpu"
    assert "default_profile" in data


def test_auth_missing_key():
    client = get_test_client()
    resp = client.get("/api/v1/voices")
    assert resp.status_code == 401
    assert "Invalid or missing API Key" in resp.json()["detail"]


def test_auth_invalid_key():
    client = get_test_client()
    resp = client.get("/api/v1/voices", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401
    assert "Invalid or missing API Key" in resp.json()["detail"]


def test_auth_with_whitespace():
    client = get_test_client()
    # Header yang memuat spasi di awal/akhir tetap diterima karena di-strip
    resp = client.get("/api/v1/voices", headers={"X-API-Key": f"  {VALID_API_KEY}  "})
    assert resp.status_code == 200


def test_voices_valid():
    client = get_test_client()
    resp = client.get("/api/v1/voices", headers={"X-API-Key": VALID_API_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert "voices" in data
    assert isinstance(data["voices"], list)


def test_synthesize_mock_wav():
    client = get_test_client()
    payload = {
        "text": "Halo ini adalah naskah uji coba untuk video short.",
        "voice": "sample_voice",
        "temperature": 0.25,
        "tempo": 1.0,
        "pitch": 0.0,
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert "X-Audio-Duration" in resp.headers

    # Verifikasi bahwa binary output adalah WAV valid yang dapat dibaca soundfile
    buf = io.BytesIO(resp.content)
    wav, sr = sf.read(buf)
    assert len(wav) > 0
    assert sr == 24000


def test_synthesize_empty_text():
    client = get_test_client()
    payload = {
        "text": "",
        "voice": "sample_voice",
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 422  # Pydantic min_length=1 validation error
