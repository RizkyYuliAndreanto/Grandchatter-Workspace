"""Chatterbox TTS wrapper: ONE model instance + fine-tune t3 into it + voice
conditioning cache. API verified against owner's base-tts.ipynb (see
PROGRESS.md Temuan Teknis): ChatterboxTTS.from_pretrained -> model.t3.load_state_dict,
generate(text, audio_prompt_path=, temperature=, repetition_penalty=), model.sr.
"""
import hashlib
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)


class Synthesizer:
    def __init__(self, config, device=None):
        import torch
        from chatterbox.tts import ChatterboxTTS

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[synth] device: {self.device}")

        self.model = ChatterboxTTS.from_pretrained(device=self.device)

        # Fine-tune: load t3_cfg.safetensors INTO the base instance (never a
        # second model). Log keys — silent failure = model speaks English.
        import torchaudio  # noqa: F401  (ensures audio backend is up)
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file

        repo = config.model.finetune_repo
        path = hf_hub_download(repo_id=repo, filename="t3_cfg.safetensors")
        missing, unexpected = self.model.t3.load_state_dict(load_file(path), strict=False)
        if missing or unexpected:
            logger.warning("fine-tune load: missing=%s unexpected=%s",
                           list(missing)[:8], list(unexpected)[:8])
        print(f"[synth] fine-tune loaded from {repo} "
              f"(missing={len(missing)}, unexpected={len(unexpected)})")

        self.sr = self.model.sr
        self._cond_cache = {}  # voice file hash -> preprocessed temp prompt path

    def prepare_voice(self, voice_path: str):
        """Preprocess + cache conditioning ONCE per voice file (hash-keyed)."""
        if not voice_path or not os.path.isfile(voice_path):
            raise ValueError(f"voice file not found: {voice_path!r}")
        h = hashlib.sha256(open(voice_path, "rb").read()).hexdigest()[:16]
        if h in self._cond_cache:
            logger.info("voice cache hit %s", h)
            return self._cond_cache[h]

        import torch
        import torchaudio as ta

        # Trim to first 8s (owner's notebook approach) — consistent timbre.
        info = ta.info(voice_path)
        wav, sr = ta.load(voice_path, frame_offset=0,
                          num_frames=int(info.sample_rate * 8))
        if wav.shape[0] > 1:  # stereo -> mono
            wav = wav.mean(dim=0, keepdim=True)
        if sr != self.sr:
            wav = ta.functional.resample(wav, sr, self.sr)
        tmp = f"/tmp/voice_{h}.wav" if os.name != "nt" else os.path.join(
            os.environ.get("TEMP", "."), f"voice_{h}.wav")
        ta.save(tmp, wav, self.sr)
        self._cond_cache[h] = tmp
        print(f"[synth] voice prepared: {tmp} ({self.sr}Hz, "
              f"{wav.shape[-1] / self.sr:.1f}s)")
        return tmp

    def synthesize(self, chunk: str, conditioning, settings) -> tuple[np.ndarray, int]:
        """One chunk -> (float32 numpy wav, sr)."""
        import torch

        with torch.inference_mode():
            wav = self.model.generate(
                chunk,
                audio_prompt_path=conditioning,
                temperature=settings.params.temperature,
                repetition_penalty=1.2,
            )
        return wav.squeeze().cpu().numpy().astype(np.float32), self.sr
