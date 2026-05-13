"""Wire chat retrieval, guardrails, model call, persistence, analytics."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.conversation import Conversation
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, HandoffInfo, SourceReference
from app.services.ai.language import LanguageService
from app.services.ai.model_router import ModelRouter
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.provider import AIProvider, AIResponse
from app.services.ai.safety import HandoffDecision, SafetyService
from app.services.analytics.tracker import AnalyticsTracker
from app.services.chat.intent import IntentClassifier, IntentResult
from app.services.chat.memory import MemoryService
from app.services.chat.response_parts import (
    build_conversation_preview,
    split_suggestions,
    strip_html_scripts,
)
from app.services.leads.extractor import LeadExtractor, message_has_contact_hint
from app.services.leads.service import LeadService
from app.services.rag.retriever import RetrievalResult, RetrieverService

logger = logging.getLogger(__name__)

_EMPTY_RETRY_SYSTEM = (
    "Your prior reply was empty. Answer the user's last message briefly "
    "and helpfully in one paragraph."
)


def _handoff_info(
    *,
    should: bool,
    reason: str | None,
    message: str,
) -> HandoffInfo:
    st = get_settings()
    return HandoffInfo(
        should_handoff=should,
        reason=reason,
        message=message,
        contact_phone=st.STUDIO_PHONE,
        contact_instagram=st.STUDIO_INSTAGRAM_URL,
    )


def _complexity(intent: str) -> str:
    return "complex" if intent == "recommendation" else "simple"


@dataclass
class _TurnPrepared:
    conv: Conversation
    intent_res: IntentResult
    chunks: list[RetrievalResult]
    history: list[dict[str, str]]
    messages: list[dict[str, str]]
    model: str
    hand_before_ai: HandoffDecision


class ChatOrchestrator:
    """Routes chat traffic through retrieval, prompting, persistence."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        memory: MemoryService,
        retriever: RetrieverService,
        prompt_builder: PromptBuilder,
        ai_provider: AIProvider,
        safety: SafetyService,
        intent_classifier: IntentClassifier,
        lead_extractor: LeadExtractor,
        analytics: AnalyticsTracker,
        model_router: ModelRouter,
        lead_service: LeadService,
    ) -> None:
        self._db = db
        self._memory = memory
        self._retriever = retriever
        self._prompt = prompt_builder
        self._ai = ai_provider
        self._safety = safety
        self._intent = intent_classifier
        self._leads_x = lead_extractor
        self._analytics = analytics
        self._router = model_router
        self._lead_service = lead_service
        self._language = LanguageService()

    def _effective_context_flag(self, intent: str, has_chunks: bool) -> bool:
        return True if intent == "greeting" else has_chunks

    async def _safe_track(self, coro: Awaitable[object]) -> None:
        try:
            await coro
        except Exception:
            logger.warning("analytics non_blocking_failed", exc_info=True)

    async def _prepare_core(
        self,
        request: ChatMessageRequest,
    ) -> ChatMessageResponse | _TurnPrepared:
        settings = get_settings()
        conv = await self._memory.get_or_create_conversation(
            self._db,
            request.session_id,
            request.language,
        )

        inj = self._safety.check_user_input(request.message)
        if not inj.is_safe:
            await self._memory.store_message(
                self._db,
                conv.id,
                "user",
                request.message,
                intent="blocked",
                metadata={"issues": inj.detected_issues},
            )
            reply = (
                "I can't assist with that kind of request — ask about tattoos, piercings, "
                "dreadlocks, or studio booking instead."
            )
            asst = await self._memory.store_message(self._db, conv.id, "assistant", reply)
            return ChatMessageResponse(
                message_id=asst.id,
                conversation_id=conv.id,
                content=reply,
                intent="blocked",
                sources=[],
                handoff=_handoff_info(should=False, reason=None, message=""),
                suggested_replies=[],
            )

        intent_res = await self._intent.classify(request.message)
        await self._memory.store_message(
            self._db,
            conv.id,
            "user",
            request.message,
            intent=intent_res.intent,
            confidence=intent_res.confidence,
        )

        lang_name = self._language.get_language_name(request.language)

        if self._safety.check_medical_concern(request.message):
            txt = (
                "This sounds like it might need attention from a medical professional."
                " If you suspect an infection or serious complication, seek medical care urgently."
                f" You can also reach the studio at {settings.STUDIO_PHONE}."
            )
            sanitized = strip_html_scripts(txt)
            asst = await self._memory.store_message(
                self._db,
                conv.id,
                "assistant",
                sanitized,
                intent="handoff",
            )
            conv.status = "handoff"
            await self._db.commit()
            await self._safe_track(
                self._analytics.track_handoff(self._db, conv.id, "medical/infection concern"),
            )
            return ChatMessageResponse(
                message_id=asst.id,
                conversation_id=conv.id,
                content=sanitized,
                intent=intent_res.intent,
                sources=[],
                handoff=_handoff_info(
                    should=True,
                    reason="medical/infection concern",
                    message=sanitized,
                ),
                suggested_replies=[],
            )

        chunks = await self._retriever.retrieve(request.message.strip(), language=request.language)
        has_chunks = len(chunks) > 0
        has_ctx = self._effective_context_flag(intent_res.intent, has_chunks)

        if not has_chunks and intent_res.intent not in ("greeting",):
            await self._safe_track(
                self._analytics.track_rag_no_result(self._db, conv.id, request.message),
            )

        hand_before = self._safety.should_handoff(
            request.message,
            intent_res.intent,
            intent_res.confidence,
            has_ctx,
        )

        history = await self._memory.get_conversation_history(self._db, conv.id)
        summary = await self._memory.summarize_if_needed(self._db, conv.id)
        msgs = self._prompt.build_chat_prompt(
            user_message=request.message,
            retrieved_context=chunks,
            conversation_history=list(history),
            language=request.language,
            lead_info=None,
            conversation_summary=summary,
            language_name=lang_name,
        )

        model_pick = self._router.select_model(intent_res.intent, _complexity(intent_res.intent))
        model = model_pick or settings.CHAT_MODEL

        return _TurnPrepared(
            conv=conv,
            intent_res=intent_res,
            chunks=chunks,
            history=history,
            messages=msgs,
            model=model,
            hand_before_ai=hand_before,
        )

    async def _finalize_turn(
        self,
        request: ChatMessageRequest,
        prep: _TurnPrepared,
        ai_full: str,
        finish_reason_val: str | None,
    ) -> ChatMessageResponse:
        settings = get_settings()
        hand_decision = prep.hand_before_ai

        parsed_content, suggestions_val = split_suggestions(ai_full or "")
        if not parsed_content.strip() and (ai_full or "").strip():
            parsed_content = strip_html_scripts(ai_full or "")
            suggestions_val = []
        sanitized_reply = strip_html_scripts(parsed_content)

        if not sanitized_reply.strip():
            sanitized_reply = (
                "I'm having trouble responding right now. "
                f"Please contact the studio at {settings.STUDIO_PHONE}."
            )
            hand_decision = HandoffDecision(True, "empty_ai_response")

        lead_flag = prep.intent_res.intent in ("booking_inquiry", "lead_capture")
        extract_gate = lead_flag or message_has_contact_hint(request.message)

        lead_created_here = False
        conv = prep.conv
        if extract_gate and conv.lead_id is None:
            try:
                preview = build_conversation_preview(prep.history, request.message)
                combined = preview + "\nUser last message:\n" + request.message
                ld = await self._lead_service.extract_and_create_lead(
                    self._db,
                    self._leads_x,
                    combined,
                    conv.id,
                    prep.history,
                )
                if ld:
                    lead_created_here = True
                    await self._safe_track(
                        self._analytics.track_event(self._db, conv.id, "lead_capture_prompted", {}),
                    )
                    await self._safe_track(
                        self._analytics.track_lead_created(self._db, ld.id, "chat"),
                    )
            except Exception:
                logger.exception("lead_pipeline_failed conversation_id=%s", conv.id)

        conv_reload = (
            await self._db.execute(select(Conversation).where(Conversation.id == conv.id))
        ).scalar_one()

        studio_line = (
            f"You can reach the studio on {settings.STUDIO_PHONE}"
            f" or Instagram: {settings.STUDIO_INSTAGRAM_URL}."
        )
        display_body = sanitized_reply
        if hand_decision.should_handoff:
            display_body = f"{sanitized_reply}\n\n{studio_line}"

        assistant_core = strip_html_scripts(display_body)
        assistant_row = await self._memory.store_message(
            self._db,
            conv_reload.id,
            "assistant",
            assistant_core,
            intent=prep.intent_res.intent,
            confidence=prep.intent_res.confidence,
            metadata={"finish_reason": finish_reason_val, "suggestions": suggestions_val},
        )

        if hand_decision.should_handoff:
            conv_reload.status = "handoff"
            await self._db.commit()

        sources = [
            SourceReference(
                document_title=c.source_title,
                chunk_text=c.chunk_text[:500],
                score=c.score,
            )
            for c in prep.chunks[:5]
        ]

        await self._safe_track(
            self._analytics.track_message(
                self._db,
                conv_reload.id,
                "user",
                prep.intent_res.intent,
                channel=request.channel,
            ),
        )
        await self._safe_track(
            self._analytics.track_event(
                self._db,
                conv_reload.id,
                "assistant_response",
                {"intent": prep.intent_res.intent},
            ),
        )
        if hand_decision.should_handoff:
            await self._safe_track(
                self._analytics.track_handoff(
                    self._db,
                    conv_reload.id,
                    hand_decision.reason or "handoff",
                ),
            )
        if prep.intent_res.intent == "pricing_guidance":
            await self._safe_track(
                self._analytics.track_event(self._db, conv_reload.id, "pricing_question", {}),
            )
        elif prep.intent_res.intent == "aftercare":
            await self._safe_track(
                self._analytics.track_event(self._db, conv_reload.id, "aftercare_question", {}),
            )
        elif prep.intent_res.intent == "recommendation":
            await self._safe_track(
                self._analytics.track_event(
                    self._db,
                    conv_reload.id,
                    "recommendation_requested",
                    {},
                ),
            )

        captures = extract_gate or lead_created_here
        hi = _handoff_info(
            should=hand_decision.should_handoff,
            reason=hand_decision.reason,
            message=assistant_core,
        )

        return ChatMessageResponse(
            message_id=assistant_row.id,
            conversation_id=conv_reload.id,
            content=assistant_core,
            intent=prep.intent_res.intent,
            sources=sources,
            handoff=hi,
            lead_capture_suggested=lead_flag or captures,
            suggested_replies=suggestions_val,
        )

    async def handle_message(self, request: ChatMessageRequest) -> ChatMessageResponse:
        prepared = await self._prepare_core(request)
        if isinstance(prepared, ChatMessageResponse):
            return prepared

        ai_full = ""
        finish_reason_val: str | None = None
        for attempt in range(2):
            to_send = list(prepared.messages)
            if attempt == 1:
                to_send.append({"role": "system", "content": _EMPTY_RETRY_SYSTEM})
            resp: AIResponse = await self._ai.chat(to_send, model=prepared.model)
            ai_full = resp.content
            finish_reason_val = resp.finish_reason
            if ai_full and ai_full.strip():
                break

        return await self._finalize_turn(request, prepared, ai_full, finish_reason_val)

    async def stream_model_tokens(self, prepared: _TurnPrepared) -> AsyncIterator[str]:
        async for token in self._ai.chat_stream(prepared.messages, model=prepared.model):
            yield token

    async def prepare_turn(
        self, request: ChatMessageRequest
    ) -> ChatMessageResponse | _TurnPrepared:
        """Expose preparation for streaming routes (stores user + runs RAG)."""
        return await self._prepare_core(request)

    async def finalize_streamed_turn(
        self,
        request: ChatMessageRequest,
        prepared: _TurnPrepared,
        accumulated_text: str,
    ) -> ChatMessageResponse:
        """Persist assistant message after SSE token stream completes."""
        finish = "stream"
        if not accumulated_text.strip():
            for attempt in range(2):
                to_send = list(prepared.messages)
                if attempt == 1:
                    to_send.append({"role": "system", "content": _EMPTY_RETRY_SYSTEM})
                resp = await self._ai.chat(to_send, model=prepared.model)
                accumulated_text = resp.content
                finish = resp.finish_reason
                if accumulated_text.strip():
                    break
        return await self._finalize_turn(request, prepared, accumulated_text, finish)
