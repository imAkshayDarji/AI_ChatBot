from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

MAX_LIMIT = 100
DEFAULT_SKIP = 0
DEFAULT_LIMIT = 20


def pagination_params(
    skip: Annotated[int, Query(ge=0)] = DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=1)] = DEFAULT_LIMIT,
) -> tuple[int, int]:
    clamped_limit = min(limit, MAX_LIMIT)
    return skip, clamped_limit


class KnowledgeDocumentCreate(BaseModel):
    title: str
    source_type: str
    language: str | None = Field(default="en")
    content: str
    status: str = Field(default="draft")
    source_url: str | None = None
    metadata_json: dict | None = None


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = None
    source_type: str | None = None
    language: str | None = None
    content: str | None = None
    status: str | None = None
    source_url: str | None = None
    metadata_json: dict | None = None


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    source_type: str
    source_url: str | None
    language: str | None
    content: str
    status: str
    metadata_json: dict | None = None
    content_hash: str | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_text: str
    chunk_index: int
    service_type: str
    language: str | None = None
    created_at: datetime
