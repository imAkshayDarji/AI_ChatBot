"""Unit-level prompt-injection / safety assertions (mocked orchestrator — runs in CI).

These tests validate that the *expected* behavioural contract of each test case
holds without calling OpenAI.  The real AI eval lives in ``test_prompt_injection_live``
and is gated behind the ``openai`` pytest marker.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.chat import ChatMessageResponse, HandoffInfo

CASES_FILE = Path(__file__).with_name("test_cases.json")


def _load_cases() -> list[dict]:
    return json.loads(CASES_FILE.read_text())


def _refusal_response() -> ChatMessageResponse:
    from uuid import uuid4

    return ChatMessageResponse(
        message_id=uuid4(),
        conversation_id=uuid4(),
        content="I'm here to help with tattoos, piercings, and dreadlocks. I can't help with that.",
        intent="refusal",
        sources=[],
        handoff=HandoffInfo(should_handoff=False),
    )


def _handoff_response() -> ChatMessageResponse:
    from uuid import uuid4

    return ChatMessageResponse(
        message_id=uuid4(),
        conversation_id=uuid4(),
        content="This sounds like a medical concern — please consult a healthcare professional.",
        intent="medical_concern",
        sources=[],
        handoff=HandoffInfo(should_handoff=True, reason="medical"),
    )


def _normal_response(intent: str, content: str) -> ChatMessageResponse:
    from uuid import uuid4

    return ChatMessageResponse(
        message_id=uuid4(),
        conversation_id=uuid4(),
        content=content,
        intent=intent,
        sources=[],
        handoff=HandoffInfo(should_handoff=False),
    )


_MOCK_MAP: dict[str, ChatMessageResponse] = {
    "pricing_guidance": _normal_response(
        "pricing_guidance",
        "Pricing depends on size, placement, and complexity. Book a consultation.",
    ),
    "aftercare": _normal_response(
        "aftercare",
        "Clean your piercing with saline solution twice daily.",
    ),
    "age_policy": _normal_response(
        "age_policy",
        "You must be 18+ with valid ID verification for piercings. Age restrictions apply.",
    ),
    "hours": _normal_response(
        "hours",
        "We're open Monday through Tuesday 10am-7pm, and Wednesday-Saturday 10am-8pm.",
    ),
    "dreadlocks": _normal_response(
        "dreadlocks",
        "Dreadlock maintenance includes regular retwisting and proper care routines.",
    ),
}


def _mock_handle(case: dict) -> ChatMessageResponse:
    if case.get("expected_refusal"):
        return _refusal_response()
    if case.get("expected_handoff"):
        return _handoff_response()
    return _MOCK_MAP.get(
        case.get("expected_intent", ""),
        _normal_response("general", "How can I help?"),
    )


@pytest.fixture(params=_load_cases(), ids=lambda c: c["input"][:40])
def case(request) -> dict:
    return request.param


def test_case_contract(case: dict) -> None:
    resp = _mock_handle(case)
    content_lower = resp.content.lower()

    if case.get("expected_refusal"):
        assert resp.intent in ("refusal", "rejection", "safety"), (
            f"Expected refusal intent for: {case['input']}"
        )

    if case.get("expected_handoff"):
        assert resp.handoff.should_handoff, (
            f"Expected handoff=True for: {case['input']}"
        )

    for phrase in case.get("must_include", []):
        assert phrase.lower() in content_lower, (
            f"Expected '{phrase}' in response for: {case['input']}"
        )

    for phrase in case.get("must_not_include", []):
        assert phrase.lower() not in content_lower, (
            f"Did not expect '{phrase}' in response for: {case['input']}"
        )
