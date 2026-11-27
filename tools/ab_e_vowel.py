"""A/B test: does the fine-tune distinguish e / é / è / ê?

Synthesizes the same word in 4 spellings and saves WAVs to
outputs/vowel_test/. Listen and compare: if é/è/ê sound different from
plain e, the respelling in normalizer.E_VOWEL_FIXES is worth keeping;
if they sound identical (or wrong), delete that dict.

Run from repo root (after app deps installed):
    python tools/ab_e_vowel.py [path/to/voice.wav]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.settings import load_settings  # noqa: E402

WORDS = {
    "telur": ["telur", "télur", "tèlur", "têlur"],   # which reads as /tə.lur/?
    "bebek": ["bebek", "bébek", "bèbek", "bêbek"],   # which reads as /bɛ.bɛk/?
    "seri":  ["seri", "séri", "sèri", "sêri"],       # /sə.ri/? (séri = award!)
}


def main():
    from core.synthesizer import Synthesizer

    settings = load_settings()
    voice = sys.argv[1] if len(sys.argv) > 1 else settings.model.voice_default
    synth = Synthesizer(settings)
    cond = synth.prepare_voice(voice)

    out_dir = os.path.join("outputs", "vowel_test")
    os.makedirs(out_dir, exist_ok=True)
    for word, spellings in WORDS.items():
        for s in spellings:
            wav, sr = synth.synthesize(
                f"Ia mengatakan {s} tadi.", cond, settings)
            path = os.path.join(out_dir, f"{word}_{s}.wav")
            import soundfile as sf
            sf.write(path, wav, sr)
            print("wrote", path)
    print("\nDengarkan tiap pasangan: apakah é/è/ê berbeda dari e?")


if __name__ == "__main__":
    main()
