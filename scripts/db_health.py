import os

from helpdesk_ai.models import (
    ChatSession,
    Embedding,
    KnowledgeDoc,
    Tenant,
    Ticket,
    User,
)
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres",
)
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    counts = {
        "tenants": session.scalar(select(func.count()).select_from(Tenant)),
        "users": session.scalar(select(func.count()).select_from(User)),
        "tickets": session.scalar(select(func.count()).select_from(Ticket)),
        "docs": session.scalar(select(func.count()).select_from(KnowledgeDoc)),
        "embeddings": session.scalar(select(func.count()).select_from(Embedding)),
        "sessions": session.scalar(select(func.count()).select_from(ChatSession)),
    }
    print(", ".join(f"{k.capitalize()} = {v}" for k, v in counts.items()))

    per_tenant = dict(
        session.execute(
            select(Ticket.tenant_id, func.count()).group_by(Ticket.tenant_id)
        ).all()
    )
    if not per_tenant:
        raise SystemExit(1)

    exit(0)
