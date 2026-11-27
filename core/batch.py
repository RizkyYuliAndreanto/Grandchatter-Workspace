"""Batch synthesis: chunks -> per-chunk FX -> progressive disk writes -> merge.

Guarantees (PRD F4):
- run_id = hash(script + voice bytes + tempo|pitch)  -> same inputs resume free;
  gap is NOT in the hash (re-merge with a new gap costs no GPU).
- every chunk is written to disk BEFORE the next is synthesized (crash-safe);
- a failed chunk never kills the run: 1 retry at temperature+0.05, then
  status=failed in manifest and the loop continues.
Pipeline order per chunk is LAW (flows/flow-pipeline.md): synth -> tempo ->
pitch -> fade. Gap + peak-normalize happen at merge time.
"""
import hashlib
import json
import logging
import os
import traceback
from pathlib import Path

import numpy as np
import soundfile as sf

from core import audio_fx as fx
from core.chunker import chunk_text
from core.normalizer import normalize

logger = logging.getLogger(__name__)

MIN_WAV_BYTES = 44  # a WAV header with no data = corrupt, re-synthesize


def run_id_for(script: str, voice_path: str, tempo: float, pitch: float) -> str:
    h = hashlib.sha256()
    h.update(script.encode("utf-8"))
    if voice_path and os.path.isfile(voice_path):
        with open(voice_path, "rb") as f:
            h.update(f.read())
    h.update(f"{tempo}|{pitch}".encode())
    return h.hexdigest()[:8]


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


def run_batch(text: str, voice_path: str, settings, out_dir: str = "outputs",
              progress_cb=None) -> dict:
    """Synthesize a full script. progress_cb(done, total, message) optional.
    Returns dict with run_dir, final_path, n_chunks, n_failed, failed_indices,
    duration_s, elapsed_s."""
    import time
    t0 = time.time()

    run_id = run_id_for(text, voice_path, settings.params.tempo, settings.params.pitch)
    run_dir = Path(out_dir) / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    normalized = normalize(text)
    chunks = chunk_text(normalized)
    if not chunks:
        raise ValueError("no chunks produced from script")

    def report(done, msg):
        if progress_cb:
            progress_cb(done, len(chunks), msg)

    manifest = {"run_id": run_id, "n_chunks": len(chunks),
                "params": {"temperature": settings.params.temperature,
                           "tempo": settings.params.tempo,
                           "pitch": settings.params.pitch,
                           "gap": settings.params.gap},
                "chunks": []}

    conditioning = synth_prepare(settings, voice_path)

    wavs, failed_indices = [], []
    sr = None
    for i, chunk in chunks_with_meta(chunks):
        path = run_dir / f"chunk_{i:04d}.wav"
        if path.exists() and path.stat().st_size > MIN_WAV_BYTES:
            wav, sr = sf.read(path, dtype="float32")
            wavs.append(wav)
            manifest["chunks"].append({"index": i, "status": "resumed"})
            report(i, f"resume chunk {i}/{len(chunks)}")
            continue

        wav, chunk_sr, status = _synth_one(settings, chunk, conditioning)
        if wav is None:
            failed_indices.append(i)
            manifest["chunks"].append({"index": i, "text": chunk, "status": "failed"})
            _write_manifest(run_dir, manifest)
            report(i, f"chunk {i} FAILED, continuing")
            continue
        sr = chunk_sr

        # Pipeline order: tempo -> pitch -> fade -> tail resonance
        # (flow-pipeline.md [4]-[6] + natural-pause release).
        if settings.params.tempo != 1.0:
            wav = fx.time_stretch(wav, settings.params.tempo)
        if settings.params.pitch != 0.0:
            wav = fx.pitch_shift(wav, sr, settings.params.pitch)
        wav = fx.micro_fade(wav, sr)
        wav = fx.tail_resonance(wav, sr)

        sf.write(path, wav, sr)  # crash-safe: on disk BEFORE next chunk
        wavs.append(wav)
        manifest["chunks"].append({"index": i, "text": chunk, "status": "ok",
                                   "duration_s": fx.duration_s(wav, sr)})
        _write_manifest(run_dir, manifest)
        report(i, f"chunk {i}/{len(chunks)}")

    merged = fx.merge_chunks(wavs, settings.params.gap, sr)
    merged = fx.peak_normalize(merged)
    final_path = run_dir / "final.wav"
    sf.write(final_path, merged, sr)

    manifest["status"] = "done"
    manifest["failed_indices"] = failed_indices
    manifest["duration_s"] = fx.duration_s(merged, sr)
    manifest["elapsed_s"] = time.time() - t0
    _write_manifest(run_dir, manifest)

    if not settings.output.keep_chunks:
        for i, _ in chunks_with_meta(chunks):
            p = run_dir / f"chunk_{i:04d}.wav"
            if p.exists():
                p.unlink()

    return {"run_dir": str(run_dir), "final_path": str(final_path),
            "n_chunks": len(chunks), "n_failed": len(failed_indices),
            "failed_indices": failed_indices,
            "duration_s": manifest["duration_s"],
            "elapsed_s": manifest["elapsed_s"]}


def chunks_with_meta(chunks):
    return list(enumerate(chunks, start=1))


def _synth_one(settings, chunk, conditioning):
    """Synthesize with 1 retry at temperature+0.05. Returns (wav, sr, status)."""
    from core.settings import LIMITS
    for attempt, temp in enumerate((settings.params.temperature,
                                    min(settings.params.temperature + 0.05,
                                        LIMITS["temperature"][1]))):
        try:
            wav, sr = synth_synthesize(settings, chunk, conditioning)
            return np.asarray(wav, dtype=np.float32), sr, "ok"
        except Exception:
            logger.warning("chunk synthesis failed (attempt %d, temp %.2f):\n%s",
                           attempt + 1, temp, traceback.format_exc())
    return None, None, "failed"


# --- synthesizer indirection (kept tiny so tests can monkeypatch) ------------

def synth_prepare(settings, voice_path):
    from core.app_state import get_synthesizer
    return get_synthesizer().prepare_voice(voice_path)


def synth_synthesize(settings, chunk, conditioning):
    from core.app_state import get_synthesizer
    return get_synthesizer().synthesize(chunk, conditioning, settings)
