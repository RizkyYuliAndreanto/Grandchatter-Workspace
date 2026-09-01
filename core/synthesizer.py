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

        self.device = device or config.model.device or (
            "cuda" if torch.cuda.is_available()
            else "mps" if getattr(torch.backends, "mps", None)
            and torch.backends.mps.is_available() else "cpu")
        print(f"[synth] device: {self.device}")

        self.model = ChatterboxTTS.from_pretrained(device=self.device)

        self.sr = self.model.sr
        self.fp16 = bool(config.model.fp16) and self.device == "cuda"
        if self.fp16:
            print("[synth] fp16 autocast ON (hemat VRAM aktivasi)")

        # Fine-tune: load t3_cfg.safetensors INTO the base instance (never a
        # second model). Log keys — silent failure = model speaks English.
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

        # torchaudio 2.10 dropped file I/O (removed on Kaggle) -> soundfile+soxr.
        import soundfile as sf
        import soxr

        # Trim to first 8s (owner's notebook approach) — consistent timbre.
        info = sf.info(voice_path)
        n_frames = int(info.samplerate * 8)
        wav, sr = sf.read(voice_path, frames=n_frames, dtype="float32",
                          always_2d=True)
        if wav.shape[1] > 1:  # stereo -> mono
            wav = wav.mean(axis=1, keepdims=True)
        if sr != self.sr:
            wav = soxr.resample(wav.squeeze(1), sr, self.sr)[:, None]
        tmp = f"/tmp/voice_{h}.wav" if os.name != "nt" else os.path.join(
            os.environ.get("TEMP", "."), f"voice_{h}.wav")
        sf.write(tmp, wav, self.sr)
        self._cond_cache[h] = tmp
        print(f"[synth] voice prepared: {tmp} ({self.sr}Hz, "
              f"{wav.shape[-1] / self.sr:.1f}s)")
        return tmp

    def synthesize(self, chunk: str, conditioning, settings) -> tuple[np.ndarray, int]:
        """One chunk -> (float32 numpy wav, sr)."""
        import torch

        with torch.inference_mode():
            ctx = (torch.autocast("cuda", dtype=torch.float16)
                   if self.fp16 else torch.inference_mode())
            with ctx:
                wav = self.model.generate(
                    chunk,
                    audio_prompt_path=conditioning,
                    temperature=settings.params.temperature,
                    repetition_penalty=1.2,
                )
        return wav.squeeze().cpu().numpy().astype(np.float32), self.sr
