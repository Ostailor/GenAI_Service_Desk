import json
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from scripts.load_docs import DEFAULT_COLLECTION, load_manifest


def test_tenant_isolation():
    seed = json.load(open("scripts/seed_manifest.json"))
    load_manifest(Path("scripts/demo_docs.json"), seed["tenants"])
    client = QdrantClient(url="http://localhost:6333")
    wrong_tenant = str(uuid.uuid4())
    result = client.search(
        collection_name=DEFAULT_COLLECTION,
        query_vector=[0.0] * 768,
        query_filter=rest.Filter(
            must=[
                rest.FieldCondition(
                    key="tenant_id", match=rest.MatchValue(value=wrong_tenant)
                )
            ]
        ),
        limit=5,
    )
    assert len(result) == 0
