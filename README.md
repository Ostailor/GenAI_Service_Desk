# GenAI Service Desk

A reference implementation of a multi-tenant IT helpdesk powered by generative AI. This repository contains the infrastructure and application code for later phases.

## Smoke test

Use `./smoke.sh` to spin up the Docker Compose stack and verify that every
service becomes healthy. Once up, the script applies Alembic migrations,
loads demo seed data and runs a database health probe before tearing the stack
down.

## Local LLM runtime

Phase 2 introduces an Ollama container running the Llama 3 8B model. Pull the
model and verify the CLI:

```bash
ollama pull llama3
ollama serve &
curl http://localhost:11434/api/generate -d '{"model":"llama3","prompt":"ping"}'
```

The Compose stack runs the model on CPU unless you add a GPU reservation. If you
have an NVIDIA card, uncomment the `deploy` block in `infra/compose.yml` or add
an equivalent `--gpus` flag when running Docker.

The 70B variant requires over 140&nbsp;GB of VRAM and disk so remains optional.
