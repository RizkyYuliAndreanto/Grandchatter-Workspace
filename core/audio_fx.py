"""Pure DSP audio effects: tempo, pitch, micro-fade, merge, peak-normalize.

numpy in -> numpy out, float32, NO file IO (batch.py owns IO), NO resampling
(synthesizer.py owns voice preprocessing). Call order per chunk: time_stretch
-> pitch_shift -> micro_fade; merge + peak_normalize after the loop.
See tasks/flows/flow-pipeline.md stages [4]-[8].
"""
import logging

import librosa
import numpy as np

from core.settings import LIMITS

logger = logging.getLogger(__name__)


def _f32(wav: np.ndarray) -> np.ndarray:
    return np.asarray(wav, dtype=np.float32)


def time_stretch(wav: np.ndarray, rate: float) -> np.ndarray:
    """rate = tempo: 1.2 -> 20% shorter. Pitch unchanged. Clamped to LIMITS."""
    lo, hi = LIMITS["tempo"]
    rate = max(lo, min(hi, float(rate)))
    if rate == 1.0:
        return _f32(wav)
    return _f32(librosa.effects.time_stretch(y=_f32(wav), rate=rate))


def pitch_shift(wav: np.ndarray, sr: int, n_steps: float) -> np.ndarray:
    """n_steps in semitones (+2 = two semitones up). Duration unchanged. Clamped."""
    lo, hi = LIMITS["pitch"]
    n_steps = max(lo, min(hi, float(n_steps)))
    if n_steps == 0:
        return _f32(wav)
    return _f32(librosa.effects.pitch_shift(y=_f32(wav), sr=sr, n_steps=n_steps))


def micro_fade(wav: np.ndarray, sr: int, ms: int = 10) -> np.ndarray:
    """Linear fade in/out of `ms` milliseconds (NOT samples). Skipped when the
    chunk is shorter than 2 fades. Prevents clicks at chunk boundaries."""
    wav = _f32(wav)
    n = int(sr * ms / 1000)
    if n <= 0 or len(wav) < 2 * n:
        return wav
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    wav[:n] *= ramp
    wav[-n:] *= ramp[::-1]
    return wav


def merge_chunks(chunks: list[np.ndarray], gap_s: float, sr: int) -> np.ndarray:
    """Concatenate chunks with `gap_s` silence BETWEEN them (not at the ends)."""
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    gap = np.zeros(int(gap_s * sr), dtype=np.float32)
    pieces: list[np.ndarray] = []
    for i, c in enumerate(chunks):
        if i:
            pieces.append(gap)
        pieces.append(_f32(c))
    return np.concatenate(pieces)


def peak_normalize(wav: np.ndarray, target: float = 0.95) -> np.ndarray:
    """Scale peak amplitude to `target`. Silent audio returned as-is (no div/0)."""
    wav = _f32(wav)
    peak = float(np.max(np.abs(wav))) if wav.size else 0.0
    if peak == 0.0:
        return wav
    return _f32(wav * (target / peak))


def duration_s(wav: np.ndarray, sr: int) -> float:
    return len(wav) / sr
