from helpdesk_ai.llm.ollama_client import OllamaClient


def test_embedding_dimension():
    client = OllamaClient()
    vec = client.embed("hello world")
    assert len(vec) == 768
