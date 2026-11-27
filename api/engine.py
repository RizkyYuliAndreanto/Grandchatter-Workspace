"""TTS Engine Adapter with Normalizer, Dual Hardware Profiles, and Async Concurrency Lock."""
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from fastapi import HTTPException, status

from api.profiles import cleanup_memory, resolve_profile
from core import audio_fx as fx
from core.chunker import chunk_text
from core.normalizer import normalize
from core.settings import Settings
from core.synth_mock import MockSynthesizer

logger = logging.getLogger(__name__)

VALID_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg"}


def resolve_voice_path(voice: str, prompt_dir: Path = Path("prompt_audio"), dry_run: bool = False) -> str:
    """Resolve voice name to audio file path with validation and audio extension check."""
    if not voice or not voice.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice parameter cannot be empty",
        )

    # 1. Cek direct file path (hanya izinkan ekstensi audio yang valid)
    direct = Path(voice)
    if direct.is_file():
        if direct.suffix.lower() not in VALID_AUDIO_EXTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid audio format for voice '{voice}'. Supported: {', '.join(sorted(VALID_AUDIO_EXTS))}",
            )
        return str(direct)

    # 2. Cek di dalam folder prompt_audio
    candidates = [
        prompt_dir / f"{voice}.wav",
        prompt_dir / voice,
        prompt_dir / f"{voice}.mp3",
        prompt_dir / f"{voice}.flac",
    ]
    for c in candidates:
        if c.is_file() and c.suffix.lower() in VALID_AUDIO_EXTS:
            return str(c)

    # 3. Fallback khusus dry-run untuk sample_voice bawaan jika file belum di-upload
    if dry_run and voice in ("sample_voice", "default"):
        return voice

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Voice '{voice}' not found in prompt_audio/",
    )


class TTSEngine:
    """Singleton adapter to manage PyTorch model / Mock with asyncio.Lock concurrency guard."""

    def __init__(self, settings: Settings, dry_run: bool = False, synth=None):
        self.settings = settings
        self.dry_run = dry_run
        self.lock = asyncio.Lock()
        self.last_normalized_text: Optional[str] = None
        self.last_chunks: List[str] = []
        self.last_profile_used: Optional[str] = None

        if synth is not None:
            self.synth = synth
            self.is_ready = True
        elif dry_run:
            self.synth = MockSynthesizer()
            self.is_ready = True
        else:
            try:
                from core.synthesizer import Synthesizer
                self.synth = Synthesizer(settings)
                self.is_ready = True
            except Exception as e:
                logger.error("Failed to load real Synthesizer, falling back to Mock: %s", e)
                self.synth = MockSynthesizer()
                self.is_ready = True

    async def synthesize_safe(
        self,
        text: str,
        voice: str,
        settings: Settings,
        profile_name: Optional[str] = None,
        force_cuda: Optional[bool] = None,
    ) -> Tuple[np.ndarray, int, str, str, List[str]]:
        """Normalize text, chunk according to profile, prepare voice, and synthesize under lock."""
        # 1. Resolve voice path (fast fail)
        voice_path = resolve_voice_path(voice, dry_run=self.dry_run)

        # 2. Normalisasi naskah Bahasa Indonesia
        normalized = normalize(text)
        if not normalized or not normalized.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text normalized to empty string",
            )
        self.last_normalized_text = normalized

        # 3. Tentukan profil hardware (Low resource vs Fast + auto-fallback)
        has_cuda = force_cuda if force_cuda is not None else getattr(self.synth, "device", "") == "cuda"
        profile_cfg = resolve_profile(
            requested=profile_name,
            default=settings.api.default_profile,
            has_cuda=has_cuda,
        )
        self.last_profile_used = profile_cfg.name

        # Aktifkan akselerasi TF32 pada GPU NVIDIA jika profil fast aktif
        if profile_cfg.enable_tf32 and has_cuda:
            try:
                import torch
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception:
                pass

        # 4. Potong naskah berdasarkan profil (120 char di low_resource, 240 char di fast)
        chunks = chunk_text(normalized, max_chars=profile_cfg.max_chunk_chars)
        self.last_chunks = chunks

        # 5. Prepare conditioning voice
        conditioning = await asyncio.to_thread(self.synth.prepare_voice, voice_path)

        # 6. Strict sequential GPU inference via asyncio.Lock
        chunk_wavs = []
        sr = 24000
        async with self.lock:
            for chunk in chunks:
                c_wav, c_sr = await asyncio.to_thread(
                    self.synth.synthesize,
                    chunk,
                    conditioning,
                    settings,
                )
                sr = c_sr
                # Post-process per chunk (tempo, pitch, fade)
                c_wav = fx.time_stretch(c_wav, settings.params.tempo)
                c_wav = fx.pitch_shift(c_wav, sr, settings.params.pitch)
                c_wav = fx.micro_fade(c_wav, sr)
                chunk_wavs.append(c_wav)

                if profile_cfg.clear_vram_after_chunk:
                    cleanup_memory()

        # 7. Merge chunks jika naskah terdiri dari beberapa bagian
        if len(chunk_wavs) == 1:
            final_wav = fx.peak_normalize(chunk_wavs[0])
        else:
            merged = fx.merge_chunks(chunk_wavs, gap_s=settings.params.gap, sr=sr)
            final_wav = fx.peak_normalize(merged)

        return final_wav, sr, normalized, profile_cfg.name, chunks
