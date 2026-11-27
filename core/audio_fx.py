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
    """Soft-edge a chunk: fast attack fade-in (click guard) + exponential
    decay fade-out (natural voice release, NOT a hard linear cut). Skipped
    when the chunk is shorter than 2 fades."""
    wav = _f32(wav)
    n = int(sr * ms / 1000)
    if n <= 0 or len(wav) < 2 * n:
        return wav
    wav[:n] *= np.linspace(0.0, 1.0, n, dtype=np.float32)
    # Exponential release: full level -> -60 dB over the fade window.
    wav[-n:] *= np.exp(np.linspace(0.0, -6.9, n, dtype=np.float32))
    return wav


def tail_resonance(wav: np.ndarray, sr: int, ms: int = 120,
                   decay_db: float = 24.0) -> np.ndarray:
    """Extend the chunk with a short decaying 'hum' (natural pause feel):
    the last ~40 ms of audio is repeated and exponentially attenuated, like a
    voice tailing off ("mungkiiin...") instead of stopping dead at the cut."""
    wav = _f32(wav)
    n = int(sr * 40 / 1000)          # source grain: last 40 ms
    tail = int(sr * ms / 1000)       # resonant tail length
    if n <= 0 or tail <= 0 or len(wav) < 2 * n:
        return wav
    grain = wav[-n:]                 # repeated, each pass quieter
    env = np.exp(np.linspace(0.0, -decay_db / 8.6859, tail // n + 1,
                             dtype=np.float32))
    pieces = [grain * env[i] for i in range(tail // n)]
    resonance = np.concatenate(pieces)[:tail].astype(np.float32)
    return np.concatenate([wav, resonance])


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
