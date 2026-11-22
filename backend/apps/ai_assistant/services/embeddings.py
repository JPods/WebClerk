"""Embeddings — turn text into a vector with this instance's own embedding model.

The model runs in the instance's local LLM runtime (settings.OLLAMA_BASE_URL); no text
leaves the box. An instance with no LLM runtime has no embeddings: that is a refusal with
a reason, never a guess or a silent empty result.
"""
import httpx
from django.conf import settings

from mimic.knn import normalize

# nomic-embed-text is trained with a task prefix on every input.
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
BATCH = 32
TIMEOUT = 120


class EmbeddingUnavailable(RuntimeError):
    """This instance cannot make embeddings right now; the message says why and what to do."""


def embed_model() -> str:
    return settings.EMBED_MODEL


def _embed(texts: list[str]) -> list[list[float]]:
    base = (settings.OLLAMA_BASE_URL or "").rstrip("/")
    if not base:
        raise EmbeddingUnavailable(
            "No LLM runtime on this hardware (OLLAMA_BASE_URL is empty), so documents cannot "
            "be indexed or searched by meaning here.")
    model = embed_model()
    out: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        batch = texts[start:start + BATCH]
        try:
            r = httpx.post(f"{base}/api/embed", json={"model": model, "input": batch},
                           timeout=TIMEOUT)
        except httpx.HTTPError as e:
            raise EmbeddingUnavailable(f"The LLM runtime at {base} did not answer: {e}") from e
        if r.status_code == 404:
            raise EmbeddingUnavailable(
                f"Embedding model '{model}' is not installed. Run: ollama pull {model}")
        if r.status_code != 200:
            raise EmbeddingUnavailable(
                f"The LLM runtime refused the embedding request ({r.status_code}): {r.text[:200]}")
        vectors = r.json().get("embeddings")
        if not vectors or len(vectors) != len(batch):
            raise EmbeddingUnavailable(
                f"Asked for {len(batch)} embeddings from '{model}', got "
                f"{len(vectors) if vectors else 0}.")
        out.extend(normalize(v) for v in vectors)
    return out


def embed_documents(texts: list[str]) -> list[list[float]]:
    """One unit vector per text, for storing."""
    return _embed([DOCUMENT_PREFIX + t for t in texts])


def embed_query(text: str) -> list[float]:
    """The unit vector for a search question."""
    return _embed([QUERY_PREFIX + text])[0]
