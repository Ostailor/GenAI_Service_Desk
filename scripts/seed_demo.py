import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from helpdesk_ai.models import Base, Tenant, Ticket, User

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres",
)

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

manifest = {
    "tenants": {},
    "users": {},
    "tickets": {},
}

with Session(engine) as session:
    # Tenants
    tenants = [
        {"name": "Acme Corp", "plan": "basic"},
        {"name": "Globex", "plan": "basic"},
    ]
    for t in tenants:
        tenant = session.scalar(select(Tenant).where(Tenant.name == t["name"]))
        if tenant is None:
            tenant = Tenant(name=t["name"], plan=t["plan"])
            session.add(tenant)
            session.flush()
        manifest["tenants"][t["name"]] = str(tenant.id)

    session.commit()

    # Users
    for tenant_name, tenant_id in manifest["tenants"].items():
        for idx in range(3):
            email = f"user{idx + 1}@{tenant_name.lower().replace(' ', '')}.com"
            user = session.scalar(
                select(User).where(
                    User.email == email, User.tenant_id == uuid.UUID(tenant_id)
                )
            )
            if user is None:
                user = User(
                    tenant_id=uuid.UUID(tenant_id),
                    email=email,
                    role="agent",
                    hashed_pw="",
                )
                session.add(user)
                session.flush()
            manifest["users"][email] = str(user.id)

    session.commit()

    # Tickets
    for email, user_id in manifest["users"].items():
        tenant_id = session.scalar(
            select(User.tenant_id).where(User.id == uuid.UUID(user_id))
        )
        for idx in range(3):
            subject = f"Issue {idx + 1} for {email}"
            ticket = session.scalar(
                select(Ticket).where(
                    Ticket.subject == subject,
                    Ticket.owner_id == uuid.UUID(user_id),
                )
            )
            if ticket is None:
                ticket = Ticket(
                    tenant_id=tenant_id,
                    owner_id=uuid.UUID(user_id),
                    status="open",
                    priority="normal",
                    subject=subject,
                    body="Demo ticket",
                )
                session.add(ticket)
                session.flush()
            manifest["tickets"][subject] = str(ticket.id)

    session.commit()

with open("scripts/seed_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
