import json
from pathlib import Path

from pytest_benchmark.fixture import BenchmarkFixture
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from helpdesk_ai.llm.ollama_client import OllamaClient
from scripts.load_docs import DEFAULT_COLLECTION, load_manifest


def test_search_latency(benchmark: BenchmarkFixture):
    seed = json.load(open("scripts/seed_manifest.json"))
    load_manifest(Path("scripts/demo_docs.json"), seed["tenants"])
    client = QdrantClient(url="http://localhost:6333")
    vec = OllamaClient().embed("reset password")

    def _search():
        client.search(
            collection_name=DEFAULT_COLLECTION,
            query_vector=vec,
            query_filter=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="tenant_id",
                        match=rest.MatchValue(value=list(seed["tenants"].values())[0]),
                    )
                ]
            ),
            limit=5,
        )

    result = benchmark(_search)
    assert result.stats["median"] < 0.15
