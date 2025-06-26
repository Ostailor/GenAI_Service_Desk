from pathlib import Path

import pytest

pytest.importorskip("unstructured.partition.auto")
pytest.importorskip("langchain_text_splitters")

from scripts.load_docs import _chunks, _load_text  # noqa: E402


def test_chunk_counts():
    text = _load_text(Path("docs/sample_docs/sample.pdf"))
    chunks = _chunks(text)
    assert len(chunks) >= 2
