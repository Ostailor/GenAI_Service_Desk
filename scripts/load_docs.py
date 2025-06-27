from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Iterable

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    RecursiveCharacterTextSplitter = None
try:
    from qdrant_client import QdrantClient
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    QdrantClient = None
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    PointStruct,
    VectorParams,
)

try:
    from unstructured.partition.auto import partition
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    partition = None

from helpdesk_ai.llm.ollama_client import OllamaClient

DEFAULT_COLLECTION = "docs"


def _load_text(path: Path) -> str:
    if partition is None:  # pragma: no cover - optional dependency
        raise RuntimeError("unstructured package is required for _load_text")
    elements = partition(filename=str(path))
    return "\n".join(e.text for e in elements if hasattr(e, "text"))


def _chunks(text: str) -> list[str]:
    if RecursiveCharacterTextSplitter is None:  # pragma: no cover
        raise RuntimeError("langchain-text-splitters is required for _chunks")
    splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=20)
    return splitter.split_text(text)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(DEFAULT_COLLECTION):
        return
    client.create_collection(
        collection_name=DEFAULT_COLLECTION,
        vectors_config=VectorParams(size=4096, distance=Distance.COSINE),
        # The hnsw_config parameter now expects an HnswConfigDiff object.
        hnsw_config=HnswConfigDiff(m=16, ef_construct=64, full_scan_threshold=10000),
    )


def _points(
    doc_id: str, tenant_id: str, chunks: Iterable[str], client: OllamaClient
) -> list[PointStruct]:
    chunk_list = list(chunks)
    resp = client._request(
        "POST",
        "/embeddings",
        json={"model": "llama3", "prompt": chunk_list},
    )
    vectors = resp.json().get("embedding", [])

    points = []
    for idx, (chunk, vec) in enumerate(zip(chunk_list, vectors)):
        points.append(
            PointStruct(
                # Qdrant requires point IDs to be a valid UUID or an integer.
                # Use a deterministic UUID derived from the checksum and index.
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}-{idx}")),
                vector=vec,
                payload={
                    "tenant_id": tenant_id,
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "text": chunk,
                },
            )
        )
    return points


def load_manifest(manifest_path: Path, tenant_map: dict[str, str]) -> None:
    client = OllamaClient()
    qdrant = QdrantClient(url="http://localhost:6333")
    _ensure_collection(qdrant)

    with open(manifest_path) as f:
        docs = json.load(f)

    start = time.time()
    total_vectors = 0
    for entry in docs:
        path = Path(entry["path"])
        tenant_name = entry["tenant"]
        tenant_id = tenant_map[tenant_name]
        checksum = _sha256(path)
        doc_id = checksum
        text = _load_text(path)
        # If the document is empty or could not be parsed, skip it.
        if not text.strip():
            print(f"Warning: No text extracted from {path}, skipping.")
            continue
        chunks = _chunks(text)
        points = _points(doc_id, tenant_id, chunks, client)
        qdrant.upsert(collection_name=DEFAULT_COLLECTION, points=points)
        total_vectors += len(points)
    duration = time.time() - start
    print(f"Ingested {total_vectors} vectors in {duration:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, required=False, default=Path("scripts/demo_docs.json")
    )
    parser.add_argument(
        "--seed-manifest", type=Path, default=Path("scripts/seed_manifest.json")
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        raise SystemExit(f"manifest {args.manifest} not found")
    if not args.seed_manifest.exists():
        raise SystemExit(f"seed manifest {args.seed_manifest} not found")

    with open(args.seed_manifest) as f:
        tenant_map = json.load(f)["tenants"]

    load_manifest(args.manifest, tenant_map)


if __name__ == "__main__":
    main()
