from __future__ import annotations

import time
from typing import Any

import httpx

BASE_URL = "http://localhost:11434/api"


class OllamaClient:
    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client()

    def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        for delay in (0.0, 0.5, 1.0):
            try:
                resp = self._client.request(method, url, json=json, timeout=30)
                resp.raise_for_status()
                return resp
            except httpx.HTTPError:
                if delay == 1.0:
                    raise
                time.sleep(delay)
        raise RuntimeError("unreachable")

    def status(self) -> dict[str, Any]:
        return self._request("GET", "/status").json()

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        model: str = "llama3",
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system is not None:
            payload["system"] = system
        return (
            self._request("POST", "/generate", json=payload).json().get("response", "")
        )

    def embed(self, text: str, *, model: str = "llama3") -> list[float]:
        payload = {"model": model, "prompt": text}
        return (
            self._request("POST", "/embeddings", json=payload)
            .json()
            .get("embedding", [])
        )
