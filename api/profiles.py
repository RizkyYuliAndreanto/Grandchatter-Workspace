"""Hardware Profiles: Low Resource (Kentang) vs Fast Mode (Dewa)."""
import gc
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProfileConfig:
    name: str
    max_chunk_chars: int
    clear_vram_after_chunk: bool
    enable_tf32: bool
    fp16: bool


PROFILES = {
    "low_resource": ProfileConfig(
        name="low_resource",
        max_chunk_chars=120,
        clear_vram_after_chunk=True,
        enable_tf32=False,
        fp16=False,
    ),
    "fast": ProfileConfig(
        name="fast",
        max_chunk_chars=240,
        clear_vram_after_chunk=False,
        enable_tf32=True,
        fp16=True,
    ),
}


def is_cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def cleanup_memory() -> None:
    """Explicit VRAM and Python garbage collection for low_resource mode."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    gc.collect()


def resolve_profile(
    requested: Optional[str] = None,
    default: str = "low_resource",
    has_cuda: Optional[bool] = None,
) -> ProfileConfig:
    """Resolve requested profile with automatic CPU fallback.

    If 'fast' is requested on a machine without CUDA, automatically fall back to 'low_resource'.
    """
    if has_cuda is None:
        has_cuda = is_cuda_available()

    target = (requested or default or "low_resource").lower().strip()
    if target not in PROFILES:
        target = "low_resource"

    # Auto-fallback: CPU-only machine cannot run fast CUDA mode
    if target == "fast" and not has_cuda:
        target = "low_resource"

    return PROFILES[target]
