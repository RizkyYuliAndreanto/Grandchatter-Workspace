"""Mock synthesizer for --dry-ui: no model, no GPU. Generates a soft sine that
varies with temperature so parameter changes are audible in local UI tests.
"""
import numpy as np

from core import audio_fx as fx

SR = 24000


class MockSynthesizer:
    def __init__(self, config=None):
        self.sr = SR

    def prepare_voice(self, voice_path: str):
        return voice_path or "mock"

    def synthesize(self, chunk: str, conditioning, settings):
        p = settings.params
        # Frequency rises with temperature (audible feedback), length from text.
        freq = 180 + 120 * p.temperature
        n = max(int(len(chunk) * 0.05 * SR), SR // 4)  # ~0.05s per char, min 0.25s
        t = np.arange(n, dtype=np.float32) / SR
        return 0.4 * np.sin(2 * np.pi * freq * t).astype(np.float32), SR
