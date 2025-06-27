import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

pytest.importorskip("qdrant_client")
pytest.importorskip("pytest_benchmark")
pytest.importorskip("httpx")

from pytest_benchmark.fixture import BenchmarkFixture  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.http import models as rest  # noqa: E402

from helpdesk_ai.llm.ollama_client import OllamaClient  # noqa: E402
from scripts.load_docs import DEFAULT_COLLECTION, load_manifest  # noqa: E402


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
