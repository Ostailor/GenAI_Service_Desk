from pathlib import Path

from scripts.load_docs import _chunks, _load_text


def test_chunk_counts():
    text = _load_text(Path("docs/sample_docs/sample.pdf"))
    chunks = _chunks(text)
    assert len(chunks) >= 2
