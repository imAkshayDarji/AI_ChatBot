"""Public conversational endpoints."""

from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import DBSessionDep, get_chat_orchestrator
from app.core.chat_rate_limit import CHAT_FEEDBACK_LIMITER, split_chat_session_budget
from app.core.config import get_settings
from app.core.errors import ForbiddenError, RateLimitExceededError
from app.core.rate_limit import check_chat_start_rate_limit
from app.db.models.conversation import Conversation
from app.db.models.feedback import AIFeedback
from app.db.models.message import Message
from app.schemas.chat import (
    ChatFeedbackRequest,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatStartResponse,
)
from app.services.analytics.tracker import AnalyticsTracker
from app.services.chat.memory import MemoryService
from app.services.chat.orchestrator import ChatOrchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/start", response_model=ChatStartResponse)
async def chat_start(
    request: Request,
    response: Response,
    body: ChatStartRequest,
    db: DBSessionDep,
) -> ChatStartResponse:
    rl_ip = check_chat_start_rate_limit(request)
    response.headers["X-RateLimit-Remaining"] = str(rl_ip.remaining)
    response.headers["X-RateLimit-Reset"] = str(rl_ip.reset_epoch)

    settings = get_settings()
    session_id_str = str(uuid.uuid4())

    memory = MemoryService(ai_provider=None)
    conv = await memory.get_or_create_conversation(db, session_id_str, body.language)

    tracker = AnalyticsTracker()
    await tracker.track_chat_started(db, conv.id, body.language, channel=body.channel)

    localized = {
        "en": {
            "welcome": (
                f"Hey! Welcome to {settings.STUDIO_NAME}. "
                "What would you like to know — tattoos, piercings, dreadlocks, or booking?"
            ),
            "quick": ["Tattoo pricing", "Piercing info", "Aftercare", "Book consultation"],
        },
        "hi": {
            "welcome": (
                f"नमस्ते! {settings.STUDIO_NAME} में आपका स्वागत है। "
                "आप क्या जानना चाहेंगे — टैटू, पियर्सिंग, ड्रेडलॉक्स, या बुकिंग?"
            ),
            "quick": ["टैटू की कीमत", "पियर्सिंग जानकारी", "बाद में देखभाल", "कंसल्टेशन बुक करें"],
        },
        "gu": {
            "welcome": (
                f"નમસ્તે! {settings.STUDIO_NAME} માં આપનું સ્વાગત છે. "
                "તમે શું જાણવા માંગો છો — ટેટૂ, પિઅર્સિંગ, ડ્રેડલોક્સ, કે બુકિંગ?"
            ),
            "quick": ["ટેટૂની કિંમત", "પિઅર્સિંગ માહિતી", "પછીની સંભાળ", "કન્સલ્ટેશન બુક કરો"],
        },
    }
    lang = body.language if body.language in localized else "en"
    welcome = localized[lang]["welcome"]
    quick = localized[lang]["quick"]
    return ChatStartResponse(session_id=session_id_str, message=welcome, quick_replies=quick)


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(
    body: ChatMessageRequest,
    response: Response,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
) -> ChatMessageResponse:
    rl = split_chat_session_budget(body.session_id)
    if not rl.allowed:
        raise RateLimitExceededError(
            "Too many chat messages for this session.",
            retry_after_seconds=max(1, rl.reset_epoch - int(time.time())),
            rate_limit_remaining=0,
            rate_limit_reset_epoch=rl.reset_epoch,
        )
    response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
    response.headers["X-RateLimit-Reset"] = str(rl.reset_epoch)

    return await orchestrator.handle_message(body)


@router.post("/message/stream")
async def chat_message_stream(
    body: ChatMessageRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
) -> StreamingResponse:
    rl = split_chat_session_budget(body.session_id)
    if not rl.allowed:
        raise RateLimitExceededError(
            "Too many chat messages for this session.",
            retry_after_seconds=max(1, rl.reset_epoch - int(time.time())),
            rate_limit_remaining=0,
            rate_limit_reset_epoch=rl.reset_epoch,
        )

    streaming_headers = {
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_epoch),
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }

    async def event_gen():
        prepared = await orchestrator.prepare_turn(body)
        if isinstance(prepared, ChatMessageResponse):
            payload = {
                "error": "conversation_short_circuit",
                "detail": prepared.model_dump(mode="json"),
            }
            yield f"event: error\ndata: {json.dumps(jsonable_encoder(payload))}\n\n"
            return

        accumulated: list[str] = []
        async for token in orchestrator.stream_model_tokens(prepared):
            accumulated.append(token)
            chunk = {"content": token}
            yield f"event: chunk\ndata: {json.dumps(jsonable_encoder(chunk))}\n\n"

        full_text = "".join(accumulated)
        finished = await orchestrator.finalize_streamed_turn(body, prepared, full_text)
        done_payload = json.dumps(jsonable_encoder(finished.model_dump(mode="json")))
        yield f"event: done\ndata: {done_payload}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=streaming_headers)


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def chat_feedback(
    body: ChatFeedbackRequest,
    db: DBSessionDep,
    response: Response,
) -> None:
    rl = CHAT_FEEDBACK_LIMITER.check(body.session_id)
    if not rl.allowed:
        raise RateLimitExceededError(
            "Too many feedback submissions for this session.",
            retry_after_seconds=max(1, rl.reset_epoch - int(time.time())),
            rate_limit_remaining=0,
            rate_limit_reset_epoch=rl.reset_epoch,
        )
    response.headers["X-RateLimit-Remaining"] = str(rl.remaining)
    response.headers["X-RateLimit-Reset"] = str(rl.reset_epoch)

    stmt = (
        select(Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Message.id == body.message_id,
            Conversation.session_id == body.session_id,
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise ForbiddenError("Feedback is only allowed for messages in your current session.")

    fb = AIFeedback(message_id=body.message_id, rating=body.rating, comment=body.comment)
    db.add(fb)
    await db.commit()


__all__ = ["router"]
