"""Central settings: load config.yaml (fallback to config.example.yaml), clamp overrides."""
import logging
import os
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)

# Single source of truth for parameter ranges (UI sliders + CLI read these).
LIMITS = {
    "temperature": (0.1, 1.0),
    "tempo": (0.8, 1.5),
    "pitch": (-4.0, 4.0),
    "gap": (0.1, 1.0),
}

TUNNEL_MODES = ("local", "share", "ngrok", "cloudflare")

VALIDATE_TUNNEL_ERROR = "tunnel.mode must be one of {} (got {{!r}})".format(", ".join(TUNNEL_MODES))


def validate_tunnel_mode(mode: str) -> str:
    mode = str(mode).strip().lower()
    if mode not in TUNNEL_MODES:
        raise ValueError(VALIDATE_TUNNEL_ERROR.format(mode))
    return mode


@dataclass
class ModelConfig:
    finetune_repo: str = "grandhigh/Chatterbox-TTS-Indonesian"
    voice_default: str = "prompt_audio/sample_voice.wav"
    device: str = ""  # empty = auto (cuda > mps > cpu); set "cpu" to force
    fp16: bool = False  # half precision on cuda: ~half VRAM, minor quality risk


@dataclass
class TunnelConfig:
    mode: str = "share"
    password: str = ""  # empty = auto-generate, printed to console


@dataclass
class Params:
    temperature: float = 0.25
    tempo: float = 1.0
    pitch: float = 0.0
    gap: float = 0.3

    def override(self, params: dict) -> None:
        """Clamp values outside LIMITS instead of raising (UI sliders are bounded,
        but manual config edits may not be)."""
        for key, value in (params or {}).items():
            if key not in LIMITS:
                logger.warning("override: unknown param %r ignored", key)
                continue
            lo, hi = LIMITS[key]
            clamped = max(lo, min(hi, float(value)))
            if clamped != value:
                logger.warning("override: %s=%s clamped to %s", key, value, clamped)
            setattr(self, key, clamped)


@dataclass
class OutputConfig:
    mp3: bool = False
    keep_chunks: bool = True


@dataclass
class ApiConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    api_key: str = "dev-local-secret-key"
    default_profile: str = "low_resource"
    output_dir: str = "outputs/api"


@dataclass
class Settings:
    model: ModelConfig = field(default_factory=ModelConfig)
    tunnel: TunnelConfig = field(default_factory=TunnelConfig)
    params: Params = field(default_factory=Params)
    output: OutputConfig = field(default_factory=OutputConfig)
    api: ApiConfig = field(default_factory=ApiConfig)

    def override(self, params: dict) -> None:
        """Clamp values outside LIMITS instead of raising (UI sliders are bounded,
        but manual config edits may not be). Delegates to Params.override."""
        self.params.override(params)


def _parse(data: dict) -> Settings:
    s = Settings()
    s.model = ModelConfig(**(data.get("model") or {}))
    s.tunnel = TunnelConfig(**(data.get("tunnel") or {}))
    s.tunnel.mode = validate_tunnel_mode(s.tunnel.mode)
    s.params = Params(**(data.get("params") or {}))
    s.output = OutputConfig(**(data.get("output") or {}))
    s.api = ApiConfig(**(data.get("api") or {}))
    if os.environ.get("TTS_API_KEY"):
        s.api.api_key = os.environ["TTS_API_KEY"]
    return s


def load_settings(path: str = None) -> Settings:
    """Load config.yaml; fall back to config.example.yaml; fall back to defaults.
    Never raises on missing files."""
    candidates = [path, "config.yaml", "config.example.yaml"]
    for p in candidates:
        if p and os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return _parse(data)
    logger.warning("no config file found, using defaults")
    return Settings()
