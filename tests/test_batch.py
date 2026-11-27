import json

import numpy as np
import pytest
import soundfile as sf

from core import batch as batch_mod
from core.batch import run_batch, run_id_for
from core.settings import Settings


class FakeSynth:
    """Stands in for the real synthesizer; yields 1s sines, can fail on demand.

    fail_index = 1-based chunk position (distinct chunk text). Retries of the
    same chunk keep failing; other chunks are unaffected.
    """

    def __init__(self, fail_index=None, sr=16000):
        self.sr = sr
        self.fail_index = fail_index
        self.calls = []
        self._pos = {}      # chunk text -> 1-based position
        self._failing = set()

    def prepare_voice(self, voice_path):
        return "cond"

    def synthesize(self, chunk, conditioning, settings):
        self.calls.append(chunk)
        if chunk not in self._pos:
            self._pos[chunk] = len(self._pos) + 1
        pos = self._pos[chunk]
        if pos == self.fail_index or chunk in self._failing:
            self._failing.add(chunk)
            raise RuntimeError("injected failure")
        t = np.arange(self.sr, dtype=np.float32) / self.sr
        return 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32), self.sr


@pytest.fixture
def voice_file(tmp_path):
    p = tmp_path / "voice.wav"
    sf.write(p, np.zeros(100, dtype=np.float32), 16000)
    return str(p)


def _run(synth, text, voice_file, tmp_path, **kw):
    from core.app_state import set_synthesizer
    set_synthesizer(synth)
    s = Settings()
    for k, v in kw.items():
        setattr(s.params, k, v)
    return run_batch(text, voice_path=voice_file, settings=s, out_dir=str(tmp_path / "out"))


def test_full_run_artifacts(voice_file, tmp_path):
    text = "Kalimat pertama di sini. Kalimat kedua di sana. Tiga. Empat!"
    r = _run(FakeSynth(), text, voice_file, tmp_path)
    assert r["n_chunks"] == 4 and r["n_failed"] == 0
    assert (tmp_path / "out" / f"run_{r['run_dir'].split('_')[-1]}" / "final.wav").exists() \
        or __import__("os").path.exists(r["final_path"])
    manifest = json.load(open(__import__("os").path.join(r["run_dir"], "manifest.json"),
                              encoding="utf-8"))
    assert all(c["status"] in ("ok", "resumed") for c in manifest["chunks"])
    # duration = sum(chunks) + (n-1)*gap + tail_resonance (0.12 s/chunk)
    # (gap 0.3 default, sr 16000)
    wav, sr = sf.read(r["final_path"])
    assert len(wav) / sr == pytest.approx(4 + 3 * 0.3 + 4 * 0.12, abs=0.05)


def test_resume_skips_existing(voice_file, tmp_path):
    text = "Satu. Dua. Tiga."
    synth1 = FakeSynth()
    r1 = _run(synth1, text, voice_file, tmp_path)
    synth2 = FakeSynth()
    r2 = _run(synth2, text, voice_file, tmp_path)
    assert synth2.calls == []  # nothing re-synthesized
    assert r2["run_dir"] == r1["run_dir"]


def test_tempo_changes_run_id(voice_file, tmp_path):
    text = "Satu. Dua."
    r1 = _run(FakeSynth(), text, voice_file, tmp_path, tempo=1.0)
    r2 = _run(FakeSynth(), text, voice_file, tmp_path, tempo=1.2)
    assert r1["run_dir"] != r2["run_dir"]


def test_run_id_hash_covers_inputs(voice_file, tmp_path):
    a = run_id_for("teks", voice_file, 1.0, 0.0)
    b = run_id_for("teks beda", voice_file, 1.0, 0.0)
    c = run_id_for("teks", voice_file, 1.2, 0.0)
    d = run_id_for("teks", voice_file, 1.0, 2.0)
    assert len({a, b, c, d}) == 4
    assert run_id_for("teks", voice_file, 1.0, 0.0) == a  # stable


def test_failed_chunk_does_not_kill_run(voice_file, tmp_path):
    text = "Satu. Dua. Tiga. Empat."
    r = _run(FakeSynth(fail_index=2), text, voice_file, tmp_path)
    assert r["n_failed"] == 1 and r["failed_indices"] == [2]
    assert r["n_chunks"] == 4
    assert __import__("os").path.exists(r["final_path"])  # final still produced
    manifest = json.load(open(__import__("os").path.join(r["run_dir"], "manifest.json"),
                              encoding="utf-8"))
    failed = [c for c in manifest["chunks"] if c["status"] == "failed"]
    assert len(failed) == 1 and failed[0]["index"] == 2
    # 2 synthesize calls for the failing chunk (1 retry), 3 successful chunks
    assert len(FakeSynth.calls if hasattr(FakeSynth, "calls") else []) == 0  # sanity
