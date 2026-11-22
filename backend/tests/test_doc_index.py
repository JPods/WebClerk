"""The document index lives in the database (DocChunk); embeddings come from the instance's
own model; search is mimic.knn. No separate vector database (Bill, 2026-11-22)."""
import hashlib
import math
import re
from types import SimpleNamespace
from unittest import mock

import httpx
import pytest
from django.test import override_settings

from apps.ai_assistant.models import DocChunk
from apps.ai_assistant.services import embeddings, vector_store
from apps.ai_assistant.services.embeddings import EmbeddingUnavailable
from apps.ai_assistant.services.vector_store import VectorStoreManager

DIM = 64


def _fake_vector(text: str) -> list[float]:
    """A bag of words hashed into DIM buckets: texts sharing words point the same way."""
    v = [0.0] * DIM
    for word in re.findall(r"[a-z]+", text.lower()):
        v[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


@pytest.fixture
def embedder():
    """Stands in for the local embedding model and counts how often it is asked."""
    calls = []

    def fake(texts):
        calls.append(list(texts))
        return [_fake_vector(t.split(": ", 1)[1]) for t in texts]

    with mock.patch.object(embeddings, "_embed", side_effect=fake):
        yield calls


DOCS = {
    "readmes/orders.md": "To create an order open the customer and choose new order then add lines",
    "readmes/invoices.md": "An invoice is made from an order when the goods ship and posts to the ledger",
    "readmes/stock.md": "Stock on hand falls when an invoice ships and rises when a receipt arrives",
}


def _index(vs, meta=None):
    for doc_id, text in DOCS.items():
        vs.index_document(doc_id, text, meta or {"source": "readmes"})


@pytest.mark.django_db
def test_search_returns_the_nearest_chunk_first(embedder):
    vs = VectorStoreManager("t")
    _index(vs)
    found = vs.search("how do I create a new order for a customer", n_results=3)
    assert found[0]["metadata"]["doc_id"] == "readmes/orders.md"
    assert found[0]["content"] == DOCS["readmes/orders.md"]
    distances = [r["distance"] for r in found]
    assert distances == sorted(distances)
    assert 0.0 <= distances[0] < distances[-1] <= 2.0
    assert len(found) == 3


@pytest.mark.django_db
def test_rows_hold_a_packed_unit_vector(embedder):
    vs = VectorStoreManager("t")
    _index(vs)
    row = DocChunk.objects.get(collection="t", doc_id="readmes/stock.md")
    assert (row.dim, len(bytes(row.embedding))) == (DIM, DIM * 4)
    assert row.embed_model == "nomic-embed-text"
    assert row.metadata == {"source": "readmes", "doc_id": "readmes/stock.md",
                            "chunk_index": 0, "total_chunks": 1}
    assert embedder[0][0].startswith("search_document: ")


@pytest.mark.django_db
def test_an_unchanged_document_is_not_embedded_again(embedder):
    vs = VectorStoreManager("t")
    _index(vs)
    asked = len(embedder)
    _index(vs)
    assert len(embedder) == asked
    assert DocChunk.objects.filter(collection="t").count() == 3


@pytest.mark.django_db
def test_a_changed_document_replaces_its_chunks(embedder):
    vs = VectorStoreManager("t")
    long_text = "alpha " * 600          # 3600 characters: three chunks
    assert vs.index_document("doc", long_text) == 3
    assert vs.index_document("doc", "short now") == 1
    rows = DocChunk.objects.filter(collection="t", doc_id="doc")
    assert [(r.chunk_index, r.content) for r in rows] == [(0, "short now")]
    assert rows[0].metadata["total_chunks"] == 1


@pytest.mark.django_db
def test_new_metadata_alone_reindexes(embedder):
    vs = VectorStoreManager("t")
    vs.index_document("doc", "same words", {"category": "a"})
    vs.index_document("doc", "same words", {"category": "b"})
    assert DocChunk.objects.get(collection="t").metadata["category"] == "b"


@pytest.mark.django_db
def test_where_filters_on_metadata_and_collections_are_separate(embedder):
    vs = VectorStoreManager("t")
    vs.index_document("a", "order entry steps", {"category": "transactions"})
    vs.index_document("b", "order entry steps", {"category": "inventory"})
    VectorStoreManager("other").index_document("c", "order entry steps", {"category": "transactions"})
    found = vs.search("order entry", where={"category": "inventory"})
    assert [r["metadata"]["doc_id"] for r in found] == ["b"]
    assert {r["metadata"]["doc_id"] for r in vs.search("order entry")} == {"a", "b"}


@pytest.mark.django_db
def test_delete_reset_and_stats(embedder):
    vs = VectorStoreManager("t")
    _index(vs)
    assert vs.stats() == {"collection": "t", "count": 3, "documents": 3,
                          "embed_model": "nomic-embed-text"}
    vs.delete_document("readmes/stock.md")
    assert vs.stats()["count"] == 2
    vs.reset()
    assert vs.stats()["count"] == 0
    assert vs.search("anything") == []
    assert len(embedder) == 3            # an empty index asks the model nothing


@pytest.mark.django_db
def test_an_index_built_with_another_model_is_refused(embedder):
    vs = VectorStoreManager("t")
    _index(vs)
    with override_settings(EMBED_MODEL="some-other-model"):
        with pytest.raises(ValueError, match="index_docs --reset"):
            vs.search("order")


def test_no_llm_runtime_is_a_refusal_with_a_reason():
    with override_settings(OLLAMA_BASE_URL=""):
        with pytest.raises(EmbeddingUnavailable, match="OLLAMA_BASE_URL is empty"):
            embeddings.embed_query("anything")


@override_settings(OLLAMA_BASE_URL="http://llm.test:11434")
def test_a_missing_model_says_how_to_install_it():
    with mock.patch.object(httpx, "post", return_value=SimpleNamespace(status_code=404, text="")):
        with pytest.raises(EmbeddingUnavailable, match="ollama pull nomic-embed-text"):
            embeddings.embed_query("anything")


@override_settings(OLLAMA_BASE_URL="http://llm.test:11434")
def test_a_runtime_that_does_not_answer_is_a_refusal():
    with mock.patch.object(httpx, "post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(EmbeddingUnavailable, match="did not answer"):
            embeddings.embed_documents(["a"])


@override_settings(OLLAMA_BASE_URL="http://llm.test:11434/")
def test_vectors_come_back_normalized_and_prefixed():
    sent = {}

    def post(url, json, timeout):
        sent.update(url=url, json=json)
        return SimpleNamespace(status_code=200, json=lambda: {"embeddings": [[3.0, 4.0]]}, text="")

    with mock.patch.object(httpx, "post", side_effect=post):
        assert embeddings.embed_query("where is my order") == [0.6, 0.8]
    assert sent["url"] == "http://llm.test:11434/api/embed"
    assert sent["json"] == {"model": "nomic-embed-text", "input": ["search_query: where is my order"]}


@override_settings(OLLAMA_BASE_URL="http://llm.test:11434")
def test_a_short_answer_from_the_model_is_refused():
    reply = SimpleNamespace(status_code=200, json=lambda: {"embeddings": [[1.0, 0.0]]}, text="")
    with mock.patch.object(httpx, "post", return_value=reply):
        with pytest.raises(EmbeddingUnavailable, match="Asked for 2 embeddings"):
            embeddings.embed_documents(["a", "b"])


@pytest.mark.django_db
def test_rag_answers_without_context_when_embedding_is_unavailable(embedder):
    from apps.ai_assistant.services.rag import RAGService
    vs = VectorStoreManager("t")
    _index(vs)
    rag = RAGService(vector_store=vs, llm_client=SimpleNamespace())
    question = "open the customer and choose new order"
    context, sources = rag._retrieve_context(question)
    assert sources[0]["source"] == "readmes/orders.md"
    assert context.startswith("--- Source: readmes/orders.md ---")
    with mock.patch.object(embeddings, "_embed", side_effect=EmbeddingUnavailable("no runtime")):
        assert rag._retrieve_context(question) == ("", [])


@pytest.mark.django_db
def test_qa_search_uses_the_one_index(embedder):
    from apps.ai_assistant.services import qa
    vs = VectorStoreManager()           # the instance's collection, the one qa reads
    vs.index_document("readmes/orders.md", DOCS["readmes/orders.md"], {"category": "transactions"})
    found = qa._search_documents("open the customer and choose new order", category="transactions")
    assert found == [{"content": DOCS["readmes/orders.md"], "source": "readmes/orders.md",
                      "distance": found[0]["distance"]}]
    assert qa._search_documents("create an order", category="inventory") == []
    with mock.patch.object(embeddings, "_embed", side_effect=EmbeddingUnavailable("no runtime")):
        assert qa._search_documents("create an order") == []


def test_no_separate_vector_database_is_imported():
    """chromadb and sentence-transformers are gone from the code and the requirements."""
    from pathlib import Path
    backend = Path(vector_store.__file__).resolve().parents[3]
    requirements = (backend / "requirements.txt").read_text().lower()
    assert "chromadb" not in requirements and "sentence-transformers" not in requirements
    offenders = [str(p.relative_to(backend)) for p in (backend / "apps").rglob("*.py")
                 if re.search(r"^\s*(import|from)\s+(chromadb|sentence_transformers)\b",
                              p.read_text(errors="ignore"), re.M)]
    assert offenders == []
