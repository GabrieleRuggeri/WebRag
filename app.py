from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator

from backend.chat_store import ChatStore
from backend.deep_research import DeepResearch
from backend.question_answering import QA
from backend.web_search import WebSearch
from utils.env_loader import load_env
from utils.logging_config import configure_logging_from_env, get_logger
from utils.utilities import generate_conversation_title

# Ensure environment variables and logging are configured before anything else
load_env()
configure_logging_from_env()
logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"

AVAILABLE_MODELS = ["qwen2.5:1.5b", "llama3.2:3b", "mistral"]
DEFAULT_MODEL = AVAILABLE_MODELS[0]
DEFAULT_TEMPERATURE = 0.5

app = FastAPI(title="WebRage Chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.warning("Static directory %s does not exist", STATIC_DIR)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
store = ChatStore()


class MessageRequest(BaseModel):
    user_id: str = Field(..., alias="user_id")
    conversation_id: str = Field(..., alias="conversation_id")
    prompt: str
    model: str = Field(DEFAULT_MODEL)
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=0.0, le=1.0)
    mode: str = Field("chat")

    @validator("model")
    def validate_model(cls, value: str) -> str:
        if value not in AVAILABLE_MODELS:
            raise ValueError("Unsupported model selection")
        return value

    @validator("mode")
    def validate_mode(cls, value: str) -> str:
        allowed = {"chat", "deep_research", "web_search"}
        if value not in allowed:
            raise ValueError("Unsupported mode")
        return value


class ConversationCreateRequest(BaseModel):
    user_id: str


def _render_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [{"role": m["role"], "content": m["content"]} for m in messages]


async def _run_llm(ai: QA, prompt: str) -> str:
    def _call_llm() -> str:
        return ai.run(prompt)

    return await run_in_threadpool(_call_llm)


async def _run_deep_research(prompt: str) -> str:
    def _call_deep_research() -> str:
        researcher = DeepResearch()
        return researcher.search(prompt)

    return await run_in_threadpool(_call_deep_research)


async def _run_web_search(prompt: str, ai: QA) -> str:
    def _call_web_search() -> str:
        web_search_client = WebSearch()
        search_results = web_search_client.search(prompt, num_results=5)
        search_context = "\n".join(
            [
                f"- {result.get('title', 'Untitled')}: {result.get('content', '')}"
                for result in search_results
            ]
        )
        enhanced_prompt = (
            f"{prompt}\n\nHere are some relevant search results:\n{search_context}"
        )
        return ai.run(enhanced_prompt)

    return await run_in_threadpool(_call_web_search)


def _conversation_title(
    ai: QA, user_id: str, conversation_id: str, fallback: str, *, is_deep: bool
) -> str:
    conv = store.get_conversation(user_id, conversation_id)
    if not conv or conv.get("title"):
        return conv.get("title") if conv else fallback

    try:
        if is_deep:
            messages = store.get_messages(user_id, conversation_id)
            title = generate_conversation_title(ai, messages, fallback)
        else:
            title = fallback[:80]
        if title:
            store.rename_conversation(user_id, conversation_id, title)
        return title
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Failed to generate conversation title: %s", exc)
        return fallback[:80]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, uid: Optional[str] = None, cid: Optional[str] = None):
    user_id = uid or str(uuid.uuid4())
    conversation_id = store.ensure_conversation(user_id, cid)

    if uid != user_id or cid != conversation_id:
        url = request.url.include_query_params(uid=user_id, cid=conversation_id)
        return RedirectResponse(str(url))

    messages = store.get_messages(user_id, conversation_id)
    conversations = store.list_conversations(user_id)

    context = {
        "request": request,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "messages": _render_messages(messages),
        "messages_json": json.dumps(_render_messages(messages), ensure_ascii=False),
        "conversations": conversations,
        "conversations_json": json.dumps(conversations, ensure_ascii=False),
        "models": AVAILABLE_MODELS,
        "selected_model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/api/conversations")
async def list_conversations(user_id: str):
    conversations = store.list_conversations(user_id)
    return {"conversations": conversations}


@app.post("/api/conversations")
async def create_conversation(payload: ConversationCreateRequest):
    conversation_id = store.create_conversation(payload.user_id)
    return {"conversation_id": conversation_id}


@app.post("/api/message")
async def send_message(payload: MessageRequest):
    conversation_id = store.ensure_conversation(payload.user_id, payload.conversation_id)
    if conversation_id != payload.conversation_id:
        logger.info(
            "Conversation %s invalid for user %s. Using %s instead.",
            payload.conversation_id,
            payload.user_id,
            conversation_id,
        )
        payload.conversation_id = conversation_id

    ai = QA(model_name=payload.model, temperature=payload.temperature)
    user_content = payload.prompt
    is_deep = payload.mode == "deep_research"

    if is_deep:
        user_content = f"[Deep Research Mode] {payload.prompt}"

    store.append_message(payload.user_id, payload.conversation_id, "user", user_content)
    title = _conversation_title(
        ai,
        payload.user_id,
        payload.conversation_id,
        payload.prompt,
        is_deep=is_deep,
    )

    start_time = time.time()
    try:
        if payload.mode == "deep_research":
            assistant_reply = await _run_deep_research(payload.prompt)
        elif payload.mode == "web_search":
            assistant_reply = await _run_web_search(payload.prompt, ai)
        else:
            assistant_reply = await _run_llm(ai, payload.prompt)
    except ValueError as exc:
        logger.error("Processing failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime failures
        logger.exception("Processing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate response") from exc

    generation_time = time.time() - start_time
    store.append_message(
        payload.user_id,
        payload.conversation_id,
        "assistant",
        assistant_reply,
    )

    conversations = store.list_conversations(payload.user_id)
    conv_title = title or next(
        (
            c.get("title")
            for c in conversations
            if c.get("id") == payload.conversation_id
        ),
        f"Conversation {payload.conversation_id[:8]}",
    )

    return JSONResponse(
        {
            "assistant": {
                "role": "assistant",
                "content": assistant_reply,
            },
            "generation_time": generation_time,
            "model": payload.model,
            "temperature": payload.temperature,
            "mode": payload.mode,
            "conversation_id": payload.conversation_id,
            "conversation_title": conv_title,
            "conversations": conversations,
        }
    )


@app.post("/api/upload")
async def upload_document(
    user_id: str = Form(...),
    conversation_id: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # We don't persist uploads yet; acknowledge receipt for UI consistency
    await file.read()  # consume the file content
    message = f"Uploaded: {file.filename}"
    logger.info(
        "Received upload for user=%s conversation=%s filename=%s",
        user_id,
        conversation_id,
        file.filename,
    )
    return {"status": "ok", "message": message}


@app.get("/api/health")
async def healthcheck():
    return {"status": "ok"}
