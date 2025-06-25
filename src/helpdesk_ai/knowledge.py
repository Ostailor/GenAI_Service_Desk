from __future__ import annotations

import httpx
from fastapi import FastAPI, status

app = FastAPI()


@app.get("/knowledge/ready", status_code=status.HTTP_200_OK)
async def knowledge_ready() -> dict[str, str]:
    async with httpx.AsyncClient() as ac:
        r1 = await ac.get("http://qdrant:6333/healthz", timeout=5)
        r1.raise_for_status()
        r2 = await ac.get("http://ollama:11434/api/status", timeout=5)
        r2.raise_for_status()
    return {"status": "ok"}
