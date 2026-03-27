import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from backend.config import AVAILABLE_MODELS, DEFAULT_TIMEOUT_SECONDS
from backend.keys import get_configured_providers, save_keys
from backend.debate import sessions, create_session, run_debate
from backend.export import save_export

router = APIRouter()


# --- Key management ---

class KeysRequest(BaseModel):
    openai: str | None = None
    anthropic: str | None = None
    google: str | None = None


@router.get("/keys")
async def get_keys():
    return get_configured_providers()


@router.post("/keys")
async def set_keys(req: KeysRequest):
    keys = {k: v for k, v in req.model_dump().items() if v}
    save_keys(keys)
    return {"status": "ok", "configured": get_configured_providers()}


# --- Models ---

@router.get("/models")
async def get_models():
    return AVAILABLE_MODELS


# --- Debate ---

class DebateRequest(BaseModel):
    prompt: str
    models: list[dict]
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@router.post("/debate/start")
async def start_debate(req: DebateRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "Prompt cannot be empty")
    if len(req.models) < 2:
        raise HTTPException(400, "Select at least 2 models")

    session = create_session(req.prompt, req.models, req.timeout_seconds)
    asyncio.create_task(run_debate(session))
    return {"session_id": session.id}


@router.get("/debate/{session_id}/stream")
async def stream_debate(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(session.event_queue.get(), timeout=1.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield f": keepalive\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/debate/{session_id}/export")
async def export_debate(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    path = save_export(session)
    return FileResponse(
        str(path),
        media_type="text/markdown",
        filename=path.name,
    )


@router.post("/debate/{session_id}/stop")
async def stop_debate(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session.stop_requested = True
    return {"status": "stopping"}
