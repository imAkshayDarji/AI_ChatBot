"""Conversation intent classification."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.ai.provider import AIProvider

INTENTS = (
    "greeting",
    "pricing_guidance",
    "service_info",
    "aftercare",
    "recommendation",
    "booking_inquiry",
    "studio_policy",
    "opening_hours",
    "lead_capture",
    "handoff_request",
    "feedback",
    "general",
)

KEYWORD_INTENTS: dict[str, tuple[str, ...]] = {
    "opening_hours": (
        "hours",
        " open",
        "close",
        "timing",
        "schedule",
        "समय",
        "સમય",
    ),
    "pricing_guidance": (
        "price",
        "cost",
        "how much",
        "rate",
        "कितना",
        "કેટલા",
    ),
    "aftercare": (
        "aftercare",
        " clean",
        "heal",
        "maintenance",
        "देखभाल",
        "સંભાળ",
    ),
    "booking_inquiry": (
        "book",
        "appointment",
        "schedule",
        "बुक",
        "બુક",
    ),
}

_CONTEXT_HINTS = {
    "aftercare": True,
    "booking_inquiry": True,
    "lead_capture": True,
    "opening_hours": True,
    "pricing_guidance": True,
    "recommendation": True,
    "service_info": True,
    "studio_policy": True,
}

_AI_CLASSIFY_PROMPT = """Classify intent for one user message about
a tattoo/piercing/dreadlocks studio chatbot.
Respond with ONLY JSON object: {"intent": "<intent>", "confidence": <0-1 float>}
Allowed intents exactly: """

_AI_SUFFIX = """

Message:"""


@dataclass
class IntentResult:
    intent: str
    confidence: float
    requires_context: bool


class IntentClassifier:
    """Keyword fast path plus optional AI refinement."""

    def __init__(self, ai_provider: AIProvider | None = None) -> None:
        self._ai = ai_provider

    def _infer_requires_context(self, intent: str) -> bool:
        return _CONTEXT_HINTS.get(intent, False)

    def _keyword_intent(self, message: str) -> IntentResult | None:
        lowered = message.lower()

        stripped_lead = lowered.lstrip().split(maxsplit=1)[0].strip("!?,.，。 ")
        greeting_tokens = {
            "hi",
            "hello",
            "hey",
            "namaste",
            "નમસ્તે",
            "नमस्ते",
        }
        if stripped_lead in greeting_tokens:
            return IntentResult("greeting", 0.9, self._infer_requires_context("greeting"))

        pad = f" {lowered} "

        best: tuple[str, int] | None = None
        for intent, tokens in KEYWORD_INTENTS.items():
            for t in tokens:
                if t in pad or t in lowered:
                    score = len(t)
                    if best is None or score > best[1]:
                        best = (intent, score)
                    break
        if best is None:
            return None
        conf = 0.88 if best[1] >= 4 else 0.82
        return IntentResult(best[0], conf, self._infer_requires_context(best[0]))

    async def _ai_classify(self, message: str) -> IntentResult:
        if self._ai is None:
            return IntentResult("general", 0.4, False)

        allowed = ", ".join(INTENTS)
        ai_messages = [
            {
                "role": "system",
                "content": _AI_CLASSIFY_PROMPT + allowed + _AI_SUFFIX,
            },
            {"role": "user", "content": message},
        ]
        response = await self._ai.chat(ai_messages, temperature=0.2, max_tokens=80)
        parsed = self._parse_ai_payload(response.content)
        intent = parsed.get("intent") if parsed else None
        confidence = float(parsed.get("confidence") or 0.5) if parsed else 0.5
        if not intent or intent not in INTENTS:
            intent = "general"
            confidence = min(confidence, 0.45)
        return IntentResult(intent, confidence, self._infer_requires_context(intent))

    @staticmethod
    def _parse_ai_payload(raw: str) -> dict[str, object] | None:
        text = raw.strip()
        match = re.search(r"\{[^\}]+\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    async def classify(self, message: str) -> IntentResult:
        kw = self._keyword_intent(message)
        if kw is not None:
            return kw
        return await self._ai_classify(message)
