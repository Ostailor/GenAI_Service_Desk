import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from helpdesk_ai.llm.ollama_client import OllamaClient
from scripts.load_docs import DEFAULT_COLLECTION, load_manifest

DATA = json.load(open(Path(__file__).parent / "qa_pairs.json"))


def test_recall_at_5():
    seed = json.load(open("scripts/seed_manifest.json"))
    load_manifest(Path("scripts/demo_docs.json"), seed["tenants"])
    client = QdrantClient(url="http://localhost:6333")
    hits = 0
    for pair in DATA:
        doc_path = pair["doc"]
        query = pair["question"]
        vec = OllamaClient().embed(query)
        result = client.search(
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
        if any(doc_path in p.payload.get("text", "") for p in result):
            hits += 1
    recall = hits / len(DATA)
    assert recall >= 0.8
