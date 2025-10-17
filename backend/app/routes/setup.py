from __future__ import annotations
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException
import subprocess
from ..services.bootstrap import ensure_whisper_ready, build_whisper_from_source
from ..config import settings


router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.post("/whisper")
def setup_whisper():
    ok, detail = ensure_whisper_ready()
    # Do not fail with 500; return status for UI to show actionable info
    return {"status": "ok" if ok else "needs_attention", **detail}


@router.post("/ollama")
def setup_ollama(background: BackgroundTasks):
    # Fire-and-forget pulls for summary + embedding models
    def _pull():
        for m in {settings.ollama_summarize_model, settings.ollama_embedding_model}:
            try:
                subprocess.run(["ollama", "pull", m], check=False)
            except Exception:
                pass
    background.add_task(_pull)
    return {"status": "pulling", "models": [settings.ollama_summarize_model, settings.ollama_embedding_model]}


@router.post("/whisper/build")
def setup_whisper_build():
    ok, msg = build_whisper_from_source()
    # After build, ensure model as well and final readiness
    mok, mdetail = ensure_whisper_ready()
    return {
        "status": "ok" if (ok and mok) else "needs_attention",
        "binary": msg,
        "model": mdetail.get("model") if isinstance(mdetail, dict) else mdetail,
        "detail": mdetail,
    }


@router.post("/faster-whisper")
def setup_faster_whisper():
    # Try to load model once to trigger local download/cache
    try:
        from ..services.transcription_fw import _load_fw  # type: ignore
        model = _load_fw()
        # run a no-op to ensure it initialized correctly
        _ = model
        return {"status": "ok", "model": settings.faster_whisper_model}
    except Exception as e:
        return {"status": "needs_attention", "error": str(e)}


@router.post("/pyannote")
def setup_pyannote():
    try:
        from ..services.transcription_fw import _maybe_load_pyannote  # type: ignore
        pipe = _maybe_load_pyannote()
        if pipe is None:
            return {"status": "disabled"}
        return {"status": "ok", "pipeline": settings.pyannote_pipeline}
    except Exception as e:
        return {"status": "needs_attention", "error": str(e)}
