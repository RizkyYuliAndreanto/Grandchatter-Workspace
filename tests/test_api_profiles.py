"""Tests for Task 03: Dual Hardware Profiles (Low Resource vs Fast Mode)."""
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.profiles import PROFILES, resolve_profile
from core.settings import Settings
from server import create_app

VALID_API_KEY = "test-secret-key-123"

# Naskah panjang lebih dari 300 karakter untuk menguji perbedaan chunking
LONG_TEXT = (
    "Tahukah Anda bahwa paus biru adalah hewan terbesar yang pernah hidup di bumi, "
    "bahkan jauh lebih besar daripada dinosaurus terbesar yang pernah ditemukan oleh para arkeolog? "
    "Panjang tubuhnya bisa mencapai lebih dari tiga puluh meter, dan lidahnya saja memiliki bobot "
    "yang setara dengan seekor gajah dewasa di daratan Asia atau Afrika."
)


def get_test_client():
    settings = Settings()
    settings.api.api_key = VALID_API_KEY
    app = create_app(settings=settings, dry_run=True)
    return TestClient(app), app


def test_resolve_profile_pure_logic():
    # Dengan CUDA tersedia
    p_fast = resolve_profile("fast", has_cuda=True)
    assert p_fast.name == "fast"
    assert p_fast.max_chunk_chars == 240
    assert p_fast.clear_vram_after_chunk is False

    # Tanpa CUDA (Auto Fallback)
    p_fallback = resolve_profile("fast", has_cuda=False)
    assert p_fallback.name == "low_resource"
    assert p_fallback.max_chunk_chars == 120
    assert p_fallback.clear_vram_after_chunk is True

    # Low resource eksplisit
    p_low = resolve_profile("low_resource", has_cuda=True)
    assert p_low.name == "low_resource"


def test_profile_low_resource_chunking():
    client, app = get_test_client()
    payload = {
        "text": LONG_TEXT,
        "voice": "sample_voice",
        "profile": "low_resource",
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    assert resp.status_code == 200
    assert resp.headers["X-Profile-Used"] == "low_resource"

    # Verifikasi jumlah potongan chunk dan panjang per chunk di engine
    engine = app.state.engine
    assert len(engine.last_chunks) > 1
    for chunk in engine.last_chunks:
        assert len(chunk) <= PROFILES["low_resource"].max_chunk_chars + 15  # batas aman kata


def test_profile_fast_chunking():
    client, app = get_test_client()
    # Mocking CUDA agar fast mode aktif
    with patch("api.profiles.is_cuda_available", return_value=True):
        payload = {
            "text": LONG_TEXT,
            "voice": "sample_voice",
            "profile": "fast",
        }
        resp = client.post(
            "/api/v1/tts/synthesize",
            json=payload,
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 200
        assert resp.headers["X-Profile-Used"] == "fast"

        engine = app.state.engine
        for chunk in engine.last_chunks:
            assert len(chunk) <= PROFILES["fast"].max_chunk_chars + 15


def test_profile_cpu_auto_fallback():
    client, app = get_test_client()
    # Mocking CUDA tidak tersedia (CPU only)
    with patch("api.profiles.is_cuda_available", return_value=False):
        payload = {
            "text": "Naskah singkat untuk uji coba fallback CPU.",
            "voice": "sample_voice",
            "profile": "fast",  # Minta fast di mesin tanpa GPU
        }
        resp = client.post(
            "/api/v1/tts/synthesize",
            json=payload,
            headers={"X-API-Key": VALID_API_KEY},
        )
        assert resp.status_code == 200
        # Wajib auto fallback ke low_resource tanpa melempar error 500
        assert resp.headers["X-Profile-Used"] == "low_resource"


def test_invalid_profile_name():
    client, _ = get_test_client()
    payload = {
        "text": "Naskah dengan nama profil tidak terdaftar.",
        "voice": "sample_voice",
        "profile": "super_sonic_ultra_dewa",
    }
    resp = client.post(
        "/api/v1/tts/synthesize",
        json=payload,
        headers={"X-API-Key": VALID_API_KEY},
    )
    # Pydantic Literal validation error (422)
    assert resp.status_code == 422


def test_health_check_profile_info():
    client, _ = get_test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_profile" in data
    # Memverifikasi bahwa profil dilaporkan dengan benar
    assert "low_resource" in data["default_profile"]
