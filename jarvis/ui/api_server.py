"""FastAPI REST and WebSocket server for JARVIS desktop automation and GUI integration."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis.brain.router import action_router
from jarvis.core.config import get_settings
from jarvis.core.context import runtime_context
from jarvis.core.events import Event, EventType, event_bus
from jarvis.memory.semantic_store import semantic_store
from jarvis.monitoring.sys_monitor import sys_monitor
from jarvis.vision.screen_capture import screen_capture
from jarvis.vision.vision_analyzer import vision_analyzer
from jarvis.workflow.workflow_engine import workflow_engine

app = FastAPI(
    title="JARVIS AI Assistant",
    version="1.0.0",
    description="Futuristic Web Interface and Automation API for JARVIS Windows AI Desktop Assistant",
)

# Enable CORS for local web dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files path
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

_latest_screenshot_path: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "web_session"


class NoteCreateRequest(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""


class ReminderCreateRequest(BaseModel):
    title: str
    time_expression: str
    description: Optional[str] = ""


class ContactCreateRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = ""
    relationship: Optional[str] = "contact"


class WhatsAppSendRequest(BaseModel):
    recipient: str
    message: str


class WhatsAppCallRequest(BaseModel):
    recipient: str


# --- Webpage Root ---

@app.get("/")
def get_dashboard_index():
    """Serve the primary HTML5 dashboard interface."""
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Web dashboard index.html not found.")
    return FileResponse(str(index_file))


@app.get("/manifest.json")
def get_manifest():
    """Serve PWA web app manifest."""
    manifest_file = WEB_DIR / "manifest.json"
    return FileResponse(str(manifest_file), media_type="application/manifest+json")


@app.get("/sw.js")
def get_service_worker():
    """Serve PWA service worker."""
    sw_file = WEB_DIR / "sw.js"
    return FileResponse(str(sw_file), media_type="application/javascript")


# --- Telemetry and Health Endpoints ---

@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health status check."""
    return {"status": "healthy", "service": "JARVIS"}


@app.get("/status")
def get_system_status() -> Dict[str, Any]:
    """Retrieve full system metrics, active window, and assistant state."""
    summary = sys_monitor.get_summary()
    ctx = runtime_context.to_dict()
    return {"metrics": summary, "context": ctx}


@app.post("/query")
def process_user_query(req: QueryRequest) -> Dict[str, Any]:
    """Execute query via action router."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    result = action_router.process_query(req.query, conversation_id=req.session_id or "web_session")
    return result


@app.post("/api/voice/listen")
def listen_and_process_voice() -> Dict[str, Any]:
    """Capture audio directly from system microphone, transcribe, and execute action."""
    from jarvis.voice.stt import stt_engine
    text = stt_engine.listen_from_microphone(timeout=4.0, phrase_time_limit=6.0)
    if not text:
        return {"success": False, "transcription": "", "response": "No speech detected. Please speak clearly into your microphone."}
    result = action_router.process_query(text, conversation_id="web_voice_session")
    return {
        "success": True,
        "transcription": text,
        "response": result.get("response", "Command executed, Sir."),
        "actions_executed": result.get("actions_executed", []),
    }


@app.post("/api/voice/transcribe")
async def transcribe_uploaded_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Transcribe browser-recorded audio directly and execute voice command."""
    import os
    import tempfile
    import time
    from jarvis.voice.stt import stt_engine

    contents = await file.read()
    if not contents or len(contents) < 500:
        return {
            "success": False,
            "transcription": "",
            "response": "Audio was too short or empty. Please speak clearly into your microphone.",
        }

    tmp_path = os.path.join(tempfile.gettempdir(), f"upload_voice_{int(time.time() * 1000)}.wav")
    try:
        with open(tmp_path, "wb") as f:
            f.write(contents)

        text = stt_engine.transcribe_audio_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    if not text:
        return {
            "success": False,
            "transcription": "",
            "response": "No speech detected. Please speak closer to your microphone or louder.",
        }

    result = action_router.process_query(text, conversation_id="web_voice_session")
    return {
        "success": True,
        "transcription": text,
        "response": result.get("response", "Command executed, Sir."),
        "actions_executed": result.get("actions_executed", []),
    }


# --- Notes and Reminders ---

@app.get("/notes")
def list_notes(tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """List notes."""
    return semantic_store.list_notes(tag=tag)


@app.post("/notes")
def create_note(req: NoteCreateRequest) -> Dict[str, Any]:
    """Create a new note."""
    return semantic_store.create_note(title=req.title, content=req.content, tags=req.tags or "")


@app.get("/reminders")
def list_reminders() -> List[Dict[str, Any]]:
    """List active reminders."""
    return semantic_store.get_pending_reminders()


# --- Contacts & WhatsApp Endpoints ---

@app.get("/contacts")
def get_contacts() -> List[Dict[str, Any]]:
    """List all saved contacts."""
    return semantic_store.list_contacts()


@app.post("/contacts")
def add_new_contact(req: ContactCreateRequest) -> Dict[str, Any]:
    """Save or update contact in database."""
    return semantic_store.add_contact(
        name=req.name,
        phone=req.phone,
        email=req.email or "",
        relationship=req.relationship or "contact",
    )


@app.post("/whatsapp/send")
def send_whatsapp(req: WhatsAppSendRequest) -> Dict[str, Any]:
    """Open WhatsApp with recipient and prepopulated message."""
    from jarvis.tools.productivity.whatsapp_client import whatsapp_client
    return whatsapp_client.send_message(recipient=req.recipient, message=req.message)


@app.post("/whatsapp/call")
def call_whatsapp(req: WhatsAppCallRequest) -> Dict[str, Any]:
    """Trigger WhatsApp voice/video call with recipient."""
    from jarvis.tools.productivity.whatsapp_client import whatsapp_client
    return whatsapp_client.initiate_call(recipient=req.recipient)


# --- Workflows ---

@app.get("/workflows")
def list_workflows() -> List[Dict[str, Any]]:
    """List registered workflows."""
    return [
        {
            "id": wf.workflow_id,
            "name": wf.name,
            "description": wf.description,
            "step_count": len(wf.steps),
        }
        for wf in workflow_engine._workflows.values()
    ]


@app.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str) -> Dict[str, Any]:
    """Trigger a workflow execution."""
    res = workflow_engine.execute_workflow(workflow_id)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error", "Workflow execution failed."))
    return res


# --- Vision & Screenshot Endpoints ---

@app.post("/api/screenshot")
def take_screenshot_endpoint() -> Dict[str, Any]:
    """Capture screen and store reference for web preview."""
    global _latest_screenshot_path
    res = screen_capture.capture_full_screen()
    if res["success"]:
        _latest_screenshot_path = res["path"]
        return {
            "success": True,
            "width": res["width"],
            "height": res["height"],
            "path": res["path"],
        }
    raise HTTPException(status_code=500, detail=res.get("error", "Screen capture failed"))


@app.get("/api/screenshot/latest")
def get_latest_screenshot():
    """Retrieve the latest captured screenshot image."""
    global _latest_screenshot_path
    if not _latest_screenshot_path or not Path(_latest_screenshot_path).exists():
        # Capture on demand if none exists
        res = screen_capture.capture_full_screen()
        if res["success"]:
            _latest_screenshot_path = res["path"]
        else:
            raise HTTPException(status_code=404, detail="No screenshot available.")
    return FileResponse(str(_latest_screenshot_path), media_type="image/png")


@app.post("/api/vision/analyze")
def analyze_vision_endpoint() -> Dict[str, Any]:
    """Analyze current screen using OCR and multimodal vision."""
    return vision_analyzer.analyze_screen()


# --- WebSocket Real-Time Event Stream ---

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Bi-directional WebSocket for streaming real-time desktop events and audio state."""
    await manager.connect(websocket)

    def forward_event_to_ws(event: Event) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                manager.broadcast({
                    "type": "event",
                    "event_type": event.name,
                    "payload": event.payload,
                    "timestamp": event.timestamp.isoformat(),
                })
            )
        except RuntimeError:
            pass

    # Subscribe forwarder to wildcard events
    event_bus.subscribe("*", forward_event_to_ws)

    try:
        while True:
            data = await websocket.receive_json()
            if "query" in data:
                res = action_router.process_query(data["query"], conversation_id="ws_session")
                await websocket.send_json({"type": "response", "data": res})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        event_bus.unsubscribe("*", forward_event_to_ws)
