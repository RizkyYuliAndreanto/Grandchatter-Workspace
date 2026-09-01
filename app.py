"""Gradio UI: script -> normalized chunked batch synthesis -> audio + downloads.

Launch: python app.py [--dry-ui]   (dry-ui = MockSynthesizer, no GPU/model)
Model loads BEFORE the tunnel rises so the URL only appears when ready.
"""
import argparse
import os
import time

# Model cache on the project drive (C: is small) — must run before any HF import.
os.environ.setdefault(
    "HF_HOME",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "hf-cache"))

import gradio as gr
import soundfile as sf

from core.batch import run_batch
from core.settings import LIMITS, load_settings
from tunnels import launch_with_tunnel

WARNING = (
    "⚠️ File di Kaggle hilang saat sesi berakhir — DOWNLOAD WAV/ZIP SEBELUM menutup tab!"
)


def _slider(label, key, value):
    lo, hi = LIMITS[key]
    return gr.Slider(minimum=lo, maximum=hi, value=value, label=label)


def build_ui(settings, synth):
    with gr.Blocks(title="Indonesian TTS Studio") as demo:
        gr.Markdown("# 🎙️ Indonesian TTS & Voice Cloning Studio")
        gr.Markdown(WARNING)

        with gr.Row():
            with gr.Column():
                text = gr.Textbox(label="Naskah", lines=8,
                                  placeholder="Tempel naskah di sini...")
                voice = gr.Audio(label="Voice referensi (5-10 detik, bersih)",
                                 type="filepath")
                temp = _slider("Temperature", "temperature", settings.params.temperature)
                tempo = _slider("Tempo (1.0 = normal)", "tempo", settings.params.tempo)
                pitch = _slider("Pitch (semitone)", "pitch", settings.params.pitch)
                gap = _slider("Jeda antar kalimat (detik)", "gap", settings.params.gap)
                btn = gr.Button("Generate Speech", variant="primary")
            with gr.Column():
                out_audio = gr.Audio(label="Hasil", interactive=False)
                out_wav = gr.File(label="Download WAV", interactive=False)
                out_zip = gr.File(label="Download ZIP (final + chunks + manifest)",
                                  interactive=False)
                out_log = gr.Textbox(label="Log", lines=6, interactive=False)

        def generate(script, voice_path, temperature, tempo, pitch, gap,
                    progress=gr.Progress()):
            if not script or not script.strip():
                raise gr.Error("Naskah kosong — isi dulu.")
            if not voice_path:
                raise gr.Error("Voice referensi belum di-upload — cloning butuh sampel suara.")

            settings.params.override({
                "temperature": temperature, "tempo": tempo,
                "pitch": pitch, "gap": gap,
            })
            t0 = time.time()

            def cb(done, total, msg):
                progress(done / total, desc=f"chunk {done}/{total}")

            result = run_batch(script, voice_path, settings,
                               out_dir="outputs", progress_cb=cb)

            n_failed = result["n_failed"]
            log = (f"✅ Selesai: {result['n_chunks']} chunk "
                   f"({n_failed} gagal) | durasi {result['duration_s']:.1f}s | "
                   f"proses {time.time() - t0:.0f}s | run: {result['run_dir']}")
            if n_failed:
                log += f"\n⚠️ Chunk gagal: {result['failed_indices']} — gap menggantikan posisinya."
            wav, sr = _load_wav(result["final_path"])
            zip_path = _zip(result["run_dir"])
            return wav, result["final_path"], zip_path, log

        btn.click(generate,
                  inputs=[text, voice, temp, tempo, pitch, gap],
                  outputs=[out_audio, out_wav, out_zip, out_log])
    return demo


def _load_wav(path):
    """(sr, ndarray) for gr.Audio; silent fallback if file missing."""
    try:
        wav, sr = sf.read(path, always_2d=False)
        return (sr, wav), path
    except Exception as e:  # keep UI alive
        print(f"[app] final.wav unreadable: {e}")
        return None, None


def _zip(run_dir):
    try:
        from core.export import zip_run
        return zip_run(run_dir)
    except Exception as e:
        print(f"[app] zip failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-ui", action="store_true",
                        help="mock synthesizer (no model/GPU) for local UI testing")
    args = parser.parse_args()

    settings = load_settings()
    from core.app_state import set_synthesizer
    if args.dry_ui:
        from core.synth_mock import MockSynthesizer
        set_synthesizer(MockSynthesizer(settings))
        print("[app] DRY-UI mode: mock synthesizer")
    else:
        from core.synthesizer import Synthesizer
        set_synthesizer(Synthesizer(settings))
        print("[app] model ready")

    demo = build_ui(settings, None)  # synthesizer lives in app_state, not passed
    demo.queue()
    launch_with_tunnel(demo, settings)


if __name__ == "__main__":
    main()
