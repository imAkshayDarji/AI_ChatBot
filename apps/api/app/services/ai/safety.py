"""Guardrails for user input classification and escalation."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SafetyResult:
    is_safe: bool
    detected_issues: list[str]
    blocked_patterns: list[str]


@dataclass
class HandoffDecision:
    should_handoff: bool
    reason: str | None


INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+instructions",
    r"reveal\s+(your|the)\s+(system|hidden)\s+prompt",
    r"show\s+(hidden|your)\s+rules",
    r"access\s+admin",
    r"delete\s+database",
    r"change\s+your\s+policies",
    r"pretend\s+you\s+are\s+not\s+a\s+chatbot",
]

_MEDICAL_KEYWORDS = (
    "infection",
    "pus",
    "swollen",
    "swelling",
    "oozing",
    "red streaks",
    "fever",
    "bleeding",
    "painful",
    "infected",
    "hot to touch",
    "foul smell",
)

_AGE_TRIGGERS = (
    r"\bminor\b",
    r"\bunder\s*(18|sixteen|seventeen)\b",
)


class SafetyService:
    def check_user_input(self, text: str) -> SafetyResult:
        lowered = text.lower()
        blocked: list[str] = []
        issues: list[str] = []

        for pat in INJECTION_PATTERNS:
            if re.search(pat, lowered, flags=re.I):
                blocked.append(pat)
                issues.append("injection")

        safe = len(blocked) == 0
        return SafetyResult(is_safe=safe, detected_issues=issues, blocked_patterns=blocked)

    def check_medical_concern(self, text: str) -> bool:
        lowered = text.lower()
        for kw in _MEDICAL_KEYWORDS:
            if kw == "painful":
                continue
            if kw in lowered:
                return True
        if "painful" in lowered and (
            any(x in lowered for x in ("piercing", "tattoo", "site", "area", "wound"))
        ):
            return True
        return False

    def check_age_topic(self, text: str) -> bool:
        lowered = text.lower()
        if re.search(r"can i get (a )?tattoo", lowered) and re.search(
            r"(16|17|minor|years old)",
            lowered,
        ):
            return True
        for pat in _AGE_TRIGGERS:
            if re.search(pat, lowered, flags=re.I) and (
                "tattoo" in lowered or "piercing" in lowered
            ):
                return True
        return False

    def should_handoff(
        self,
        text: str,
        intent: str,
        confidence: float,
        has_context: bool,
    ) -> HandoffDecision:
        if self.check_medical_concern(text):
            return HandoffDecision(True, "medical/infection concern")

        lowered = text.lower()

        exact_price_signals = ["exact price", "final price", "promise me"]
        if any(sig in lowered for sig in exact_price_signals) and intent in (
            "pricing_guidance",
            "booking_inquiry",
            "lead_capture",
        ):
            return HandoffDecision(True, "exact price request")

        booking_confirm = ["confirm booking", "booked for tomorrow", "is my booking confirmed"]
        if any(sig in lowered for sig in booking_confirm):
            return HandoffDecision(True, "booking confirmation request")

        if intent == "handoff_request":
            return HandoffDecision(True, "handoff_request")

        if any(
            t in lowered for t in ("i'm furious", "sue you", "terrible service", "unacceptable")
        ):
            return HandoffDecision(True, "angry/frustrated user")

        if intent == "recommendation" and any(
            s in lowered for s in ("full sleeve", "full back", "custom sleeve", "entire portrait")
        ):
            return HandoffDecision(True, "complex custom design request")

        if not has_context and intent == "general" and confidence < 0.55:
            return HandoffDecision(True, "no relevant RAG context")

        if not has_context and confidence < 0.35:
            return HandoffDecision(True, "no relevant RAG context")

        if confidence < 0.25:
            return HandoffDecision(True, "low confidence")

        return HandoffDecision(False, None)
