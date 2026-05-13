"""Lead enrichment from unstructured chat."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.ai.provider import AIProvider


@dataclass
class LeadData:
    name: str | None
    email: str | None
    phone: str | None
    service_interest: str | None
    budget_range: str | None
    placement: str | None
    style_preference: str | None
    conversation_context: str | None = None


_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
)


def message_has_contact_hint(message: str) -> bool:
    if _EMAIL_RE.search(message):
        return True
    digits = "".join(ch for ch in message if ch.isdigit())
    return len(digits) >= 10


_PROMPT = """Extract lead fields from ONE user chat message plus short history context JSON.
Respond ONLY with compact JSON matching keys:
{"name","email","phone","service_interest","budget_range","placement","style_preference","conversation_context"}
Use null where unknown. conversation_context max 280 chars summarizing user's goal.
"""


class LeadExtractor:
    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai = ai_provider

    async def extract_from_message(
        self,
        message: str,
        conversation_history: list[dict[str, str]],
    ) -> LeadData | None:
        payload = [{"role": m["role"], "content": m["content"]} for m in conversation_history[-6:]]
        payload.append({"role": "user", "content": message})
        messages = [
            {"role": "system", "content": _PROMPT},
            *payload,
        ]
        response = await self._ai.chat(messages, temperature=0.2, max_tokens=300)
        data = self._parse(response.content)
        if data is None:
            return None
        ld = LeadData(
            name=_s(data.get("name")),
            email=_s(data.get("email")),
            phone=_s(data.get("phone")),
            service_interest=_s(data.get("service_interest")),
            budget_range=_s(data.get("budget_range")),
            placement=_s(data.get("placement")),
            style_preference=_s(data.get("style_preference")),
            conversation_context=_s(data.get("conversation_context")),
        )
        if not any([ld.name, ld.email, ld.phone, ld.service_interest]):
            return None
        return ld

    @staticmethod
    def _parse(raw: str) -> dict[str, object] | None:
        text = raw.strip()
        match = re.search(r"\{[^\}]+\}", text, flags=re.DOTALL)
        if match is None:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _s(value: object) -> str | None:
    if value is None:
        return None
    txt = str(value).strip()
    return txt if txt else None
