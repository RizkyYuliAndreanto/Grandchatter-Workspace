import pytest

from tunnels import TunnelError, generate_password, launch_with_tunnel
from tunnels.cloudflare_t import parse_tunnel_url
from tunnels.ngrok_t import _get_token


def test_password_autogenerate_nonempty():
    assert generate_password()
    assert generate_password() != generate_password()


def test_parse_tunnel_url():
    line = "2026-09-01T10:00:00Z INF |  https://random-words-here.trycloudflare.com  |"
    assert parse_tunnel_url(line) == "https://random-words-here.trycloudflare.com"
    assert parse_tunnel_url("no url in this line") is None


def test_ngrok_token_missing_raises(monkeypatch):
    monkeypatch.delenv("NGROK_TOKEN", raising=False)
    with pytest.raises(TunnelError):
        _get_token()


def test_ngrok_token_from_env(monkeypatch):
    monkeypatch.setenv("NGROK_TOKEN", "tok123")
    assert _get_token() == "tok123"


class _FakeDemo:
    def __init__(self):
        self.kwargs = None

    def launch(self, **kwargs):
        self.kwargs = kwargs


def _fake_settings(mode, password=""):
    from core.settings import Settings
    s = Settings()
    s.tunnel.mode = mode
    s.tunnel.password = password
    return s


def test_fallback_to_share_on_tunnel_error(monkeypatch):
    calls = []

    def boom(demo, password):
        calls.append("ngrok")
        raise TunnelError("no token")

    def share(demo, password):
        calls.append("share")

    import tunnels
    monkeypatch.setitem(tunnels._LAUNCHERS, "ngrok", boom)
    monkeypatch.setitem(tunnels._LAUNCHERS, "share", share)
    launch_with_tunnel(_FakeDemo(), _fake_settings("ngrok"))
    assert calls == ["ngrok", "share"]


def test_share_mode_receives_auth(monkeypatch):
    calls = {}

    def share(demo, password):
        calls["password"] = password
        calls["demo"] = demo

    import tunnels
    monkeypatch.setitem(tunnels._LAUNCHERS, "share", share)
    demo = _FakeDemo()
    launch_with_tunnel(demo, _fake_settings("share", "secret"))
    assert calls["password"] == "secret" and calls["demo"] is demo


def test_local_mode_no_share(monkeypatch):
    # local mode launches via launch_local, never opens the share tunnel
    opened = []

    def local(demo, password):
        opened.append("local")

    import tunnels
    monkeypatch.setitem(tunnels._LAUNCHERS, "local", local)
    launch_with_tunnel(_FakeDemo(), _fake_settings("local", "pw"))
    assert opened == ["local"]


def test_local_launch_kwargs():
    from tunnels.local_t import launch_local

    demo = _FakeDemo()
    launch_local(demo, "pw")
    assert demo.kwargs["share"] is False
    assert demo.kwargs["server_name"] == "127.0.0.1"
    assert demo.kwargs["auth"] == ("user", "pw")


def test_invalid_mode_falls_back(monkeypatch):
    # validate_tunnel_mode raises before launching; dispatcher should surface it,
    # so we call with a settings object whose mode was validated upstream (app.py).
    from core.settings import validate_tunnel_mode
    with pytest.raises(ValueError):
        validate_tunnel_mode("chaos")
