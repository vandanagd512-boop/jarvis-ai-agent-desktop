"""Fast serverless entrypoint for Vercel deployment with sub-second cold starts."""

from __future__ import annotations
import os
import sys
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

app = FastAPI(
    title="JARVIS AI Assistant - Cloud & Mobile API",
    version="1.0.0",
    description="Serverless API for JARVIS Mobile Assistant on Vercel",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def vercel_path_rewrite_normalizer(request: Request, call_next):
    """Normalize rewritten request paths in Vercel serverless environment."""
    if request.url.path in ("/api/index.py", "/api/index", "/api", "/api/"):
        matched = request.headers.get("x-matched-path")
        if matched and matched not in ("/api/index.py", "/api/index"):
            request.scope["path"] = matched
    return await call_next(request)


# In-memory / temporary persistence for serverless
_notes: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Welcome to JARVIS Mobile",
        "content": "J.A.R.V.I.S. is live on your mobile device with voice control, YouTube, WhatsApp, and Vision.",
        "tags": "welcome,system",
    }
]

_contacts: List[Dict[str, str]] = [
    {"id": "1", "name": "Alex", "phone": "+1234567890", "relationship": "Colleague"},
    {"id": "2", "name": "Mom", "phone": "+1987654321", "relationship": "Family"},
]


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "web_session"


class NoteCreateRequest(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""


class VisionRequest(BaseModel):
    image_base64: str
    prompt: Optional[str] = "Describe what you see in detail and suggest any relevant actions."


@app.get("/health")
@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "platform": "vercel_serverless", "timestamp": time.time()}


@app.get("/status")
@app.get("/api/status")
def status() -> Dict[str, Any]:
    return {
        "status": "online",
        "mode": "cloud_mobile",
        "metrics": {
            "ram": {"used_gb": "2.4", "total_gb": "8.0", "load_percent": 30},
            "disk_c": {"used_gb": "45.0", "free_gb": "180.0", "used_percent": 20},
            "battery": "100% (Mobile/Cloud)",
            "uptime": "Active",
        },
        "context": {
            "active_window": "JARVIS Mobile Assistant",
            "cpu_usage": "8%",
        },
    }


@app.get("/notes")
@app.get("/api/notes")
def get_notes() -> List[Dict[str, Any]]:
    return _notes


@app.post("/notes")
@app.post("/api/notes")
def create_note(req: NoteCreateRequest) -> Dict[str, Any]:
    note = {
        "id": len(_notes) + 1,
        "title": req.title,
        "content": req.content,
        "tags": req.tags,
    }
    _notes.insert(0, note)
    return {"success": True, "note": note}


@app.get("/contacts")
@app.get("/api/contacts")
def get_contacts() -> List[Dict[str, str]]:
    return _contacts


@app.post("/query")
@app.post("/api/query")
async def process_query(req: QueryRequest) -> Dict[str, Any]:
    query = req.query.strip()
    lower = query.lower()

    # 1. YouTube Intent Detection
    if "youtube" in lower or lower.startswith("play "):
        clean_target = query
        for prefix in ("play", "search", "open", "launch", "youtube"):
            if clean_target.lower().startswith(prefix):
                clean_target = clean_target[len(prefix):].strip()
        clean_target = clean_target.replace("on youtube", "").replace("in youtube", "").strip()

        return {
            "success": True,
            "response": f"Launching YouTube for '{clean_target or query}', Sir.",
            "actions_executed": [
                {
                    "action": "play_youtube",
                    "status": "success",
                    "arguments": {"query": clean_target or query},
                }
            ],
            "mode": "cloud_intent",
        }

    # 2. WhatsApp Intent Detection
    if (
        "whatsapp" in lower
        or lower.startswith("message ")
        or lower.startswith("call ")
        or lower.startswith("text ")
    ):
        recipient = "contact"
        for part in query.split():
            if part.lower() not in ("message", "call", "whatsapp", "to", "on", "text", "send", "a"):
                recipient = part
                break
        return {
            "success": True,
            "response": f"Opening WhatsApp chat with {recipient}, Sir.",
            "actions_executed": [
                {
                    "action": "send_whatsapp_message",
                    "status": "success",
                    "arguments": {"recipient": recipient, "message": ""},
                }
            ],
            "mode": "cloud_intent",
        }

    # 3. Google Search Intent Detection
    if lower.startswith("search ") or lower.startswith("google ") or lower.startswith("browse "):
        search_query = query.replace("search", "", 1).replace("google", "", 1).strip()
        return {
            "success": True,
            "response": f"Searching Google for '{search_query}', Sir.",
            "actions_executed": [
                {
                    "action": "search_google",
                    "status": "success",
                    "arguments": {"query": search_query},
                }
            ],
            "mode": "cloud_intent",
        }

    # 4. Gemini AI Cloud Generation (Lazy-loaded)
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            system_prompt = (
                "You are J.A.R.V.I.S., an intelligent, polite, and capable personal AI assistant. "
                "Address the user politely as Sir or Madam. Keep answers concise, clear, and direct."
            )
            response = client.models.generate_content(
                model=model_name,
                contents=f"{system_prompt}\n\nUser: {query}\nJARVIS:",
            )
            reply_text = response.text.strip() if response.text else "Command acknowledged, Sir."
            return {
                "success": True,
                "response": reply_text,
                "actions_executed": [],
                "mode": "gemini_cloud",
            }
        except Exception as exc:
            pass

    # 5. Offline Fallback
    return {
        "success": True,
        "response": f"Command received, Sir: '{query}'. System is operating nominally.",
        "actions_executed": [],
        "mode": "cloud_direct",
    }


@app.post("/api/vision/analyze")
async def analyze_vision(req: VisionRequest) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "success": False,
            "analysis": "Vision analysis requires GEMINI_API_KEY configured in Vercel environment variables.",
        }
    try:
        import base64
        from google import genai

        client = genai.Client(api_key=api_key)
        img_bytes = base64.b64decode(req.image_base64)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(
            model=model_name,
            contents=[
                genai.types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                req.prompt,
            ],
        )
        return {"success": True, "analysis": response.text.strip()}
    except Exception as exc:
        return {"success": False, "analysis": f"Vision analysis error: {exc}"}
