import pytest

pytestmark = pytest.mark.slow

pytest.importorskip("httpx")

from helpdesk_ai.llm.ollama_client import OllamaClient  # noqa: E402


def test_embedding_dimension():
    client = OllamaClient()
    vec = client.embed("hello world")
    # The llama3 model uses an embedding size of 4096
    assert len(vec) == 4096
