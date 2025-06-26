import subprocess
import time
from pathlib import Path

import asyncio
import pytest

pytest.importorskip("httpx")
import httpx  # noqa: E402

from helpdesk_ai.llm.ollama_client import OllamaClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra"


def _wait_healthy(container_id: str) -> None:
    inspect_fmt = (
        "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}"
    )
    for _ in range(60):
        status = subprocess.check_output(
            ["docker", "inspect", "-f", inspect_fmt, container_id], text=True
        ).strip()
        if status == "healthy":
            return
        if status in {"exited", "unhealthy"}:
            raise AssertionError(f"ollama container status {status}")
        time.sleep(1)
    raise AssertionError("ollama did not become healthy")


@pytest.fixture(scope="module")
def ollama_container():
    if subprocess.run(["which", "docker"], capture_output=True).returncode != 0:
        pytest.skip("docker not available")
    subprocess.run(["docker", "compose", "up", "-d", "ollama"], cwd=INFRA, check=True)
    container_id = subprocess.check_output(
        ["docker", "compose", "ps", "-q", "ollama"], cwd=INFRA, text=True
    ).strip()
    try:
        _wait_healthy(container_id)
        yield
    finally:
        subprocess.run(["docker", "compose", "down"], cwd=INFRA, check=True)


def test_status(ollama_container):
    client = OllamaClient()
    assert client.status()["status"] == "ok"


def test_generate(ollama_container):
    client = OllamaClient()
    text = client.generate("Hello")
    assert text


def test_embeddings(ollama_container):
    client = OllamaClient()
    vec = client.embed("hello world")
    assert len(vec) == 4096


def test_latency_budget(ollama_container, benchmark):
    client = OllamaClient()

    def _call():
        client.generate("hello" * 4)

    result = benchmark(_call)
    assert result.stats["mean"] < 2.0


@pytest.mark.anyio
async def test_concurrent_generation(ollama_container):
    async def worker(idx: int) -> str:
        async with httpx.AsyncClient() as ac:
            resp = await ac.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": f"hi {idx}", "stream": False},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    results = await asyncio.gather(*[worker(i) for i in range(10)])
    assert all(results)
