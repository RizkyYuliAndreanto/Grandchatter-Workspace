import numpy as np
import pytest

from core import audio_fx as fx

SR = 24000


def sine(freq: float, seconds: float, sr: int = SR) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return 0.5 * np.sin(2 * np.pi * freq * t).astype(np.float32)


def dominant_freq(wav: np.ndarray, sr: int = SR) -> float:
    spec = np.abs(np.fft.rfft(wav))
    return float(np.argmax(spec) * sr / len(wav))


# --- tempo ----------------------------------------------------------------

def test_time_stretch_shortens():
    wav = sine(440, 3.0)
    out = fx.time_stretch(wav, rate=1.2)
    assert 2.5 * 0.97 <= fx.duration_s(out, SR) <= 2.5 * 1.03


def test_time_stretch_identity_at_one():
    wav = sine(440, 1.0)
    assert fx.duration_s(fx.time_stretch(wav, 1.0), SR) == pytest.approx(1.0, abs=0.01)


def test_time_stretch_clamps_out_of_range():
    wav = sine(440, 1.0)
    # rate 99 clamps to 1.5; result shorter but finite, no crash
    out = fx.time_stretch(wav, rate=99)
    assert fx.duration_s(out, SR) < 1.0


# --- pitch ------------------------------------------------------------------

def test_pitch_shift_raises_frequency():
    out = fx.pitch_shift(sine(440, 2.0), SR, n_steps=2)
    assert dominant_freq(out) == pytest.approx(440 * 2 ** (2 / 12), rel=0.02)


def test_pitch_shift_keeps_duration():
    out = fx.pitch_shift(sine(440, 2.0), SR, n_steps=2)
    assert fx.duration_s(out, SR) == pytest.approx(2.0, abs=0.05)


def test_pitch_zero_identity():
    wav = sine(440, 1.0)
    assert np.array_equal(fx.pitch_shift(wav, SR, 0), wav)


# --- micro fade ---------------------------------------------------------------

def test_micro_fade_ends_near_zero():
    wav = np.full(SR, 0.5, dtype=np.float32)
    out = fx.micro_fade(wav, SR, ms=10)
    n = int(SR * 10 / 1000)
    assert abs(out[0]) < 0.01
    assert abs(out[-1]) < 0.01
    assert abs(out[n * 2]) == pytest.approx(0.5)  # middle untouched


def test_micro_fade_unit_is_ms_not_samples():
    # 10 "samples" would be 0.4ms at 24kHz; 10ms must be 240 samples
    wav = np.full(SR, 0.5, dtype=np.float32)
    out = fx.micro_fade(wav, SR, ms=10)
    assert abs(out[int(SR * 0.005)]) < 0.5  # 5ms in: still ramping


def test_micro_fade_short_chunk_no_crash():
    tiny = np.full(10, 0.5, dtype=np.float32)  # < 2 fades at 24kHz/10ms
    out = fx.micro_fade(tiny, SR, ms=10)
    assert np.array_equal(out, tiny)


def test_micro_fade_exponential_decay_not_linear():
    # Natural release: fade-out must decay faster at the start (exp) than a
    # linear ramp would — sample at 1/4 into the window sits well below half.
    wav = np.full(SR, 0.5, dtype=np.float32)
    out = fx.micro_fade(wav, SR, ms=100)
    n = int(SR * 0.1)
    quarter = out[-n:][n // 4]
    assert quarter < 0.25 * 0.5  # exp(-6.9*0.25) ≈ 0.18 of full amplitude


# --- tail resonance -----------------------------------------------------------

def test_tail_resonance_extends_and_decays():
    wav = sine(440, 1.0)
    out = fx.tail_resonance(wav, SR, ms=120)
    assert fx.duration_s(out, SR) == pytest.approx(1.12, abs=0.001)
    tail = out[int(1.0 * SR):]
    # tail starts audible (the hum) and decays toward silence
    assert float(np.max(np.abs(tail[:400]))) > 0.05
    assert float(np.max(np.abs(tail[-100:]))) < float(np.max(np.abs(tail[:400]))) / 3


def test_tail_resonance_short_chunk_no_crash():
    tiny = np.full(10, 0.5, dtype=np.float32)
    assert np.array_equal(fx.tail_resonance(tiny, SR, ms=120), tiny)


# --- merge -----------------------------------------------------------------

def test_merge_with_gap():
    a, b, c = sine(440, 1.0), sine(880, 1.0), sine(220, 1.0)
    out = fx.merge_chunks([a, b, c], gap_s=0.3, sr=SR)
    assert fx.duration_s(out, SR) == pytest.approx(3.6, abs=0.001)
    # gap region is silent
    assert np.max(np.abs(out[int(1.0 * SR):int(1.3 * SR)])) == 0.0
    # no gap at the ends: first/last chunk starts mid-wave (amplitude near peak phase)
    assert float(np.max(np.abs(out[:1000]))) > 0.1   # first 1000 samples contain signal
    assert float(np.max(np.abs(out[-1000:]))) > 0.1  # last 1000 samples contain signal


def test_merge_empty():
    assert len(fx.merge_chunks([], 0.3, SR)) == 0


# --- peak normalize ----------------------------------------------------------

def test_peak_normalize_target():
    wav = sine(440, 1.0) * 0.3
    out = fx.peak_normalize(wav, 0.95)
    assert np.max(np.abs(out)) == pytest.approx(0.95, abs=0.01)


def test_peak_normalize_silent_no_crash():
    silent = np.zeros(SR, dtype=np.float32)
    assert np.max(np.abs(fx.peak_normalize(silent))) == 0.0


def test_output_dtype_float32():
    wav64 = sine(440, 0.5).astype(np.float64)
    assert fx.time_stretch(wav64, 1.2).dtype == np.float32
    assert fx.pitch_shift(wav64, SR, 1).dtype == np.float32
    assert fx.micro_fade(wav64, SR).dtype == np.float32
    assert fx.peak_normalize(wav64).dtype == np.float32
