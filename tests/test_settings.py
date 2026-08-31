import pytest
import yaml

from core.settings import LIMITS, Settings, load_settings, validate_tunnel_mode


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no config.yaml / example here
    s = load_settings()
    assert s.params.temperature == 0.25
    assert s.tunnel.mode == "share"
    assert s.output.mp3 is False


def test_load_example_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = {"params": {"temperature": 0.5}, "tunnel": {"mode": "NGROK"}}
    (tmp_path / "config.example.yaml").write_text(yaml.safe_dump(cfg))
    s = load_settings()
    assert s.params.temperature == 0.5
    assert s.tunnel.mode == "ngrok"  # lowercased by validate


def test_explicit_path_beats_defaults(tmp_path):
    p = tmp_path / "my.yaml"
    p.write_text(yaml.safe_dump({"params": {"tempo": 1.2}}))
    s = load_settings(str(p))
    assert s.params.tempo == 1.2
    assert s.params.temperature == 0.25  # untouched default


def test_override_clamps():
    s = Settings()
    s.override({"tempo": 99})
    assert s.params.tempo == LIMITS["tempo"][1]
    s.override({"pitch": -10})
    assert s.params.pitch == LIMITS["pitch"][0]
    s.override({"temperature": 0.7})
    assert s.params.temperature == 0.7  # in range stays


def test_override_unknown_ignored():
    s = Settings()
    s.override({"nonsense": 5})
    assert s.params.tempo == 1.0  # nothing changed


def test_validate_tunnel_mode():
    assert validate_tunnel_mode("NGROK") == "ngrok"
    assert validate_tunnel_mode("share") == "share"
    with pytest.raises(ValueError):
        validate_tunnel_mode("foo")


def test_bad_tunnel_mode_in_file_raises(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump({"tunnel": {"mode": "chaos"}}))
    with pytest.raises(ValueError):
        load_settings(str(p))
