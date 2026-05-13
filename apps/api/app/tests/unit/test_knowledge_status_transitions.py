import pytest

from app.core.errors import KnowledgeStatusTransitionError
from app.services.knowledge_document_service import validate_knowledge_status_transition


def test_draft_to_active_allowed() -> None:
    validate_knowledge_status_transition("draft", "active")


def test_draft_to_archived_rejected() -> None:
    with pytest.raises(KnowledgeStatusTransitionError):
        validate_knowledge_status_transition("draft", "archived")


def test_active_to_archived_allowed() -> None:
    validate_knowledge_status_transition("active", "archived")


def test_archived_to_active_allowed() -> None:
    validate_knowledge_status_transition("archived", "active")


def test_same_status_noop() -> None:
    validate_knowledge_status_transition("draft", "draft")
