from __future__ import annotations

import httpx
from fastapi import FastAPI, status

app = FastAPI()


@app.get("/knowledge/ready", status_code=status.HTTP_200_OK)
async def knowledge_ready() -> dict[str, str]:
    async with httpx.AsyncClient() as ac:
        # Use /readyz to check if the service is ready for traffic.
        r1 = await ac.get("http://qdrant:6333/readyz", timeout=5)
        r1.raise_for_status()
        # The /api/status endpoint does not exist. Use the root endpoint.
        r2 = await ac.get("http://ollama:11434/", timeout=5)
        r2.raise_for_status()
    return {"status": "ok"}
