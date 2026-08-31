"""Zip one run folder for download. Stdlib zipfile only.
/kaggle/working is ephemeral — the ZIP is how results leave the session
(see tasks/flows/flow-session-kaggle.md step 10).
"""
import re
import zipfile
from datetime import datetime
from pathlib import Path

_MANIFEST = "manifest.json"
_FINAL = "final.wav"
_CHUNK = re.compile(r"chunk_\d{4}\.wav$")


def zip_run(run_dir: str, out_dir: str = None) -> str:
    """Zip final.wav + manifest.json + all chunk_XXXX.wav from run_dir.
    Returns the zip path; raises FileNotFoundError on empty/missing dir."""
    run = Path(run_dir)
    if not run.is_dir():
        raise FileNotFoundError(f"run dir not found: {run_dir}")

    members = [run / _MANIFEST, run / _FINAL] + sorted(
        p for p in run.iterdir() if _CHUNK.match(p.name))

    if not any(m.exists() and m.stat().st_size > 0 for m in members):
        raise FileNotFoundError(f"nothing to zip in {run_dir} (no manifest/final/chunks)")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(out_dir) if out_dir else run.parent
    zip_path = out_path / f"run_{run.name}_{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for m in members:
            if m.exists() and m.stat().st_size > 0:
                zf.write(m, arcname=f"{run.name}/{m.name}")
    return str(zip_path)
