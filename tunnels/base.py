"""Shared tunnel constants/errors — kept out of __init__ to avoid circular imports."""


class TunnelError(Exception):
    """Raised by a launcher when its mode cannot start (bad token, binary fail)."""


GRADIO_PORT = 7860
