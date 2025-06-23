# GenAI Service Desk

A reference implementation of a multi-tenant IT helpdesk powered by generative AI. This repository contains the infrastructure and application code for later phases.

## Smoke test

Use `./smoke.sh` to spin up the Docker Compose stack and verify that every
service becomes healthy. Once up, the script applies Alembic migrations,
loads demo seed data and runs a database health probe before tearing the stack
down.
