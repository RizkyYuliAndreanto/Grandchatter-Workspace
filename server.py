"""FastAPI REST API Server for Indonesian TTS.

Launch:
    python server.py [--dry-run] [--host 127.0.0.1] [--port 8000]
"""
import argparse
import copy
import io
import os
import urllib.parse
import uuid
from pathlib import Path
from typing import Optional

import soundfile as sf
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.auth import get_api_key_validator
from api.engine import TTSEngine
from api.profiles import resolve_profile
from api.schemas import (
    BatchRequest,
    BatchResponse,
    HealthResponse,
    SegmentResult,
    SynthesizeRequest,
    VoicesResponse,
)
from core.settings import Settings, load_settings
from core.synth_mock import MockSynthesizer


def create_app(settings: Optional[Settings] = None, dry_run: bool = False, synth=None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="Indonesian TTS API",
        version="1.0.0",
        description="REST API for Indonesian Text-to-Speech & Voice Cloning",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inisialisasi engine adapter (Task 02: Engine + Normalizer + Concurrency Lock)
    engine = TTSEngine(settings=settings, dry_run=dry_run, synth=synth)
    app.state.engine = engine

    api_key_dependency = get_api_key_validator(settings.api.api_key)

    @app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
    def health_check():
        device_name = "mock-cpu" if dry_run or isinstance(engine.synth, MockSynthesizer) else getattr(engine.synth, "device", "unknown")
        has_cuda = device_name == "cuda"
        resolved_prof = resolve_profile(default=settings.api.default_profile, has_cuda=has_cuda)
        profile_info = resolved_prof.name if (resolved_prof.name == settings.api.default_profile) else f"{resolved_prof.name} (auto-fallback: {device_name})"
        return HealthResponse(
            status="ready" if engine.is_ready else "loading",
            model_loaded=engine.is_ready,
            device=device_name,
            default_profile=profile_info,
        )

    @app.get("/api/v1/voices", response_model=VoicesResponse, tags=["Voices"])
    def list_voices(_: str = Depends(api_key_dependency)):
        prompt_dir = Path("prompt_audio")
        voices = []
        if prompt_dir.exists():
            voices = sorted([f.stem for f in prompt_dir.glob("*.wav")])
        return VoicesResponse(voices=voices)

    @app.post("/api/v1/tts/synthesize", tags=["TTS"])
    async def synthesize_speech(req: SynthesizeRequest, _: str = Depends(api_key_dependency)):
        # Siapkan settings sementara dengan parameter request (in-memory copy tanpa disk I/O)
        synth_settings = copy.deepcopy(settings)
        synth_settings.params.temperature = req.temperature
        synth_settings.params.tempo = req.tempo
        synth_settings.params.pitch = req.pitch

        # Synthesize audio dengan normalizer + dual profile + concurrency lock
        wav, sr, normalized_text, profile_used, chunks = await engine.synthesize_safe(
            text=req.text,
            voice=req.voice,
            settings=synth_settings,
            profile_name=req.profile,
        )

        # Encode ke binary WAV di memory
        buf = io.BytesIO()
        sf.write(buf, wav, sr, format="WAV")
        wav_bytes = buf.getvalue()
        duration_s = round(len(wav) / sr, 2)

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "X-Audio-Duration": str(duration_s),
                "X-Audio-Samplerate": str(sr),
                "X-Audio-Chunks": str(len(chunks)),
                "X-Profile-Used": profile_used,
                "X-Normalized-Text": urllib.parse.quote(normalized_text),
            },
        )

    @app.post("/api/v1/tts/batch", response_model=BatchResponse, tags=["TTS"])
    async def synthesize_batch(req: BatchRequest, _: str = Depends(api_key_dependency)):
        batch_id = f"batch_{uuid.uuid4().hex[:10]}"
        base_dir = Path(settings.api.output_dir).resolve()
        batch_dir = base_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        results = []
        successful_count = 0
        failed_count = 0
        used_ids = set()

        # Iterasi setiap segmen (skala puluhan hingga ratusan naskah)
        for idx, segment in enumerate(req.segments, start=1):
            base_safe_id = "".join(c for c in segment.id if c.isalnum() or c in ("-", "_")).strip() or f"seg_{idx}"

            # Cegah duplikasi file WAV jika klien mengirim ID yang sama
            safe_id = base_safe_id
            counter = 2
            while safe_id in used_ids:
                safe_id = f"{base_safe_id}_{counter}"
                counter += 1
            used_ids.add(safe_id)

            out_file = batch_dir / f"{safe_id}.wav"

            seg_settings = copy.deepcopy(settings)
            seg_settings.params.temperature = req.temperature
            seg_settings.params.tempo = segment.tempo if segment.tempo is not None else req.tempo
            seg_settings.params.pitch = segment.pitch if segment.pitch is not None else req.pitch

            try:
                wav, sr, _, profile_used, _ = await engine.synthesize_safe(
                    text=segment.text,
                    voice=req.voice,
                    settings=seg_settings,
                    profile_name=req.profile,
                )
                sf.write(str(out_file), wav, sr, format="WAV")
                duration_s = round(len(wav) / sr, 2)
                results.append(SegmentResult(
                    id=segment.id,
                    audio_url=f"/api/v1/audio/download/{batch_id}/{safe_id}.wav",
                    duration_s=duration_s,
                    status="success",
                ))
                successful_count += 1
            except Exception as e:
                # Anti-runtuh: satu segmen gagal tidak menggugurkan segmen lainnya
                results.append(SegmentResult(
                    id=segment.id,
                    status="failed",
                    error=str(e),
                ))
                failed_count += 1

        resolved_prof = resolve_profile(req.profile, default=settings.api.default_profile)
        return BatchResponse(
            status="success" if failed_count == 0 else "partial_success",
            batch_id=batch_id,
            profile_used=resolved_prof.name,
            total_segments=len(req.segments),
            successful_segments=successful_count,
            failed_segments=failed_count,
            results=results,
        )

    @app.get("/api/v1/audio/download/{batch_id}/{filename}", tags=["Audio"])
    def download_audio(batch_id: str, filename: str, _: str = Depends(api_key_dependency)):
        # Sanitasi path untuk mencegah path traversal (e.g. ../../)
        if ".." in batch_id or ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: invalid path traversal detected",
            )

        safe_batch_id = Path(batch_id).name
        safe_filename = Path(filename).name
        base_dir = Path(settings.api.output_dir).resolve()
        target_file = (base_dir / safe_batch_id / safe_filename).resolve()

        if not str(target_file).startswith(str(base_dir)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: invalid path target",
            )

        if not target_file.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found",
            )

        return FileResponse(
            path=target_file,
            media_type="audio/wav",
            filename=safe_filename,
        )
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found",
            )

        return FileResponse(
            path=target_file,
            media_type="audio/wav",
            filename=safe_filename,
        )

    return app


def main():
    parser = argparse.ArgumentParser(description="Indonesian TTS REST API Server")
    parser.add_argument("--dry-run", action="store_true", help="Jalankan dengan MockSynthesizer (tanpa GPU/model)")
    parser.add_argument("--host", default=None, help="Host server (default dari config.yaml)")
    parser.add_argument("--port", type=int, default=None, help="Port server (default dari config.yaml)")
    args = parser.parse_args()

    settings = load_settings()
    host = args.host or settings.api.host
    port = args.port or settings.api.port

    app = create_app(settings=settings, dry_run=args.dry_run)
    print(f"🚀 Server TTS berjalan di http://{host}:{port} (dry-run: {args.dry_run})")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
