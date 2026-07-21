import pytest
from finai.rag.ingestion.chunking import section_aware_chunks

def test_chunking():
    chunks = section_aware_chunks("x"*3000, {"ticker":"AAPL"}, 1000, 100)
    assert len(chunks) == 4
    assert chunks[0].metadata["ticker"] == "AAPL"

def test_invalid_chunking():
    with pytest.raises(ValueError):
        section_aware_chunks("x", {}, 100, 100)
