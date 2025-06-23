# Coding Style and Database Guidelines

All table names, columns, and constraints use `snake_case`.
Constraint names are prefixed with the date to avoid collisions.
Each business table carries a `tenant_id` column so PostgreSQL row-level security can enforce isolation.

## Entities
- Tenant
- User
- Ticket
- KnowledgeDoc
- Embedding
- ChatSession
