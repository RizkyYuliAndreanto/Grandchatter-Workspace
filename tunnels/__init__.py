"""Tunnel dispatcher: launch a Gradio demo via share | ngrok | cloudflare.

Rules (PRD F5): password auth ALWAYS; failed mode falls back to share, never
crashes the app. Secrets are read only inside tunnels/ngrok_t.py.
"""
import secrets
import traceback

from core.settings import Settings, validate_tunnel_mode
from tunnels.base import GRADIO_PORT, TunnelError  # noqa: F401 (re-exported)
from tunnels.share_t import launch_share
from tunnels.local_t import launch_local
from tunnels.ngrok_t import launch_ngrok
from tunnels.cloudflare_t import launch_cloudflare

_LAUNCHERS = {
    "local": launch_local,
    "share": launch_share,
    "ngrok": launch_ngrok,
    "cloudflare": launch_cloudflare,
}


def generate_password() -> str:
    return secrets.token_urlsafe(6)


def launch_with_tunnel(demo, settings: Settings) -> None:
    """Blocking: launches Gradio with the configured tunnel mode."""
    mode = validate_tunnel_mode(settings.tunnel.mode)
    password = settings.tunnel.password or generate_password()
    if not settings.tunnel.password:
        print(f"[tunnel] auto-generated password: {password}")
    try:
        _LAUNCHERS[mode](demo, password)
    except (TunnelError, Exception) as e:
        if type(e) is not TunnelError:
            print(f"[tunnel] mode {mode!r} crashed unexpectedly: {e}")
            traceback.print_exc()
        else:
            print(f"[tunnel] mode {mode!r} failed: {e}")
        print("[tunnel] falling back to share mode")
        _LAUNCHERS["share"](demo, password)
