from dataclasses import dataclass

@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict[str, str]

def section_aware_chunks(
    text: str,
    metadata: dict[str, str],
    chunk_size: int = 1400,
    overlap: int = 180,
) -> list[Chunk]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must exceed overlap")
    out = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        out.append(Chunk(text=text[start:end], metadata=dict(metadata)))
        if end == len(text):
            break
        start = end - overlap
    return out
