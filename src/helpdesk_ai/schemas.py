from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class TenantSchema(BaseModel):
    id: uuid.UUID | None = None
    name: str
    plan: str | None = None
    created_at: datetime | None = None


class UserSchema(BaseModel):
    id: uuid.UUID | None = None
    tenant_id: uuid.UUID
    email: EmailStr
    role: str
    hashed_pw: str | None = None
    created_at: datetime | None = None


class TicketSchema(BaseModel):
    id: uuid.UUID | None = None
    tenant_id: uuid.UUID
    owner_id: uuid.UUID
    status: str
    priority: str
    subject: str
    body: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeDocSchema(BaseModel):
    id: uuid.UUID | None = None
    tenant_id: uuid.UUID
    title: str
    path: str
    checksum: str | None = None
    added_at: datetime | None = None


class EmbeddingSchema(BaseModel):
    id: uuid.UUID | None = None
    doc_id: uuid.UUID
    chunk_index: int
    vector: list[float]
    token_count: int


class ChatSessionSchema(BaseModel):
    id: uuid.UUID | None = None
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime | None = None
    summary: str | None = None
