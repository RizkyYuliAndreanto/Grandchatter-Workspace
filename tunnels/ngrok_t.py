"""ngrok mode: pyngrok tunnel. Token from Kaggle Secrets (or NGROK_TOKEN env).
Missing token -> TunnelError -> dispatcher falls back to share.
"""
import os

from tunnels.base import GRADIO_PORT, TunnelError


def _get_token() -> str:
    # Kaggle Secrets first (module only exists on Kaggle), then plain env var.
    try:
        from kaggle_secrets import UserSecretsClient
        token = UserSecretsClient().get_secret("NGROK_TOKEN")
        if token:
            return token
    except ImportError:
        pass
    token = os.environ.get("NGROK_TOKEN", "")
    if not token:
        raise TunnelError(
            "NGROK_TOKEN not found: add it via Kaggle Add-ons -> Secrets (or env var)")
    return token


def launch_ngrok(demo, password: str) -> None:
    import ngrok  # pyngrok package installs module name "ngrok"

    token = _get_token()
    ngrok.set_auth_token(token)
    url = ngrok.connect(GRADIO_PORT, "http").public_url
    print(f"[tunnel] ngrok URL: {url}")
    demo.launch(
        share=False,
        auth=("user", password),
        server_name="0.0.0.0",
        server_port=GRADIO_PORT,
    )
