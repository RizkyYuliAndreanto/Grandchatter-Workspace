"""Local mode: no tunnel — localhost only (fastest, for low-end laptop runs)."""
from tunnels.share_t import launch_share


def launch_local(demo, password: str) -> None:
    launch_share(demo, password, local_only=True)
