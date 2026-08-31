"""Process-wide synthesizer holder. app.py sets it once at startup (real or
mock); batch.py reads it via indirection so tests can monkeypatch freely.
"""
_synthesizer = None


def set_synthesizer(synth) -> None:
    global _synthesizer
    _synthesizer = synth


def get_synthesizer():
    if _synthesizer is None:
        raise RuntimeError("synthesizer not initialized — run app.main() first")
    return _synthesizer
