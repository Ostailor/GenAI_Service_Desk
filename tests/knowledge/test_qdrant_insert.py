import json
from pathlib import Path

import pytest

pytest.importorskip("qdrant_client")
pytest.importorskip("httpx")

from qdrant_client import QdrantClient  # noqa: E402

from scripts.load_docs import DEFAULT_COLLECTION, load_manifest  # noqa: E402


def test_qdrant_insert(tmp_path):
    seed = json.load(open("scripts/seed_manifest.json"))
    load_manifest(Path("scripts/demo_docs.json"), seed["tenants"])
    client = QdrantClient(url="http://localhost:6333")
    stats = client.count(collection_name=DEFAULT_COLLECTION, exact=True)
    assert stats.count > 0
