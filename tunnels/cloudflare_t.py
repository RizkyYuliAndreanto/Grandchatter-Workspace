"""cloudflare mode: quick tunnel via the cloudflared binary (no account needed).
Binary is downloaded ONLY when this mode is selected (never at import time).
URL is parsed from cloudflared stdout by a pure helper (unit-tested).
"""
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from tunnels.base import GRADIO_PORT, TunnelError

_CLOUDFLARED_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

URL_TIMEOUT_S = 60


def parse_tunnel_url(line: str) -> str | None:
    """Extract the trycloudflare URL from one cloudflared stdout line (pure)."""
    m = _CLOUDFLARED_URL.search(line)
    return m.group(0) if m else None


def _binary_path() -> Path:
    exe = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    return Path(__file__).resolve().parent.parent / exe


def _ensure_binary() -> Path:
    """Reuse repo-local binary if present, else download for this platform."""
    path = _binary_path()
    if path.exists():
        return path
    name = "cloudflared-windows-amd64.exe" if sys.platform == "win32" else "cloudflared-linux-amd64"
    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{name}"
    print(f"[tunnel] downloading cloudflared: {url}")
    import urllib.request
    urllib.request.urlretrieve(url, path)
    if sys.platform != "win32":
        path.chmod(0o755)
    return path


def _start_tunnel(binary: Path) -> str:
    """Run cloudflared, return the public URL (raises TunnelError on timeout)."""
    proc = subprocess.Popen(
        [str(binary), "tunnel", "--url", f"http://localhost:{GRADIO_PORT}",
         "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace")
    found: list[str] = []

    def reader():
        for line in proc.stdout:
            url = parse_tunnel_url(line)
            if url:
                found.append(url)

    threading.Thread(target=reader, daemon=True).start()
    deadline = time.time() + URL_TIMEOUT_S
    while time.time() < deadline and not found:
        time.sleep(0.5)
    if not found:
        proc.kill()
        raise TunnelError(f"cloudflared did not report a URL within {URL_TIMEOUT_S}s")
    return found[0]


def launch_cloudflare(demo, password: str) -> None:
    binary = _ensure_binary()
    url = _start_tunnel(binary)
    print(f"[tunnel] cloudflare URL: {url}")
    demo.launch(
        share=False,
        auth=("user", password),
        server_name="0.0.0.0",
        server_port=GRADIO_PORT,
    )
