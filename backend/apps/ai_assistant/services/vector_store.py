"""
Vector store manager — indexes documents for retrieval, in this instance's own database.

Chunks and their embeddings are DocChunk rows. Embeddings come from the instance's own
embedding model (services/embeddings.py); nearest-neighbour search is mimic.knn, a plain
dot product over unit vectors. No separate vector database.

Usage:
    from apps.ai_assistant.services.vector_store import VectorStoreManager

    vs = VectorStoreManager()
    vs.index_document("path/to/readme.md", "markdown content...", {"source": "readme"})
    results = vs.search("how do I create an order?", n_results=5)
"""
import hashlib
import logging

from django.conf import settings
from django.db import transaction

from mimic.knn import pack, top_k, unpack

from . import embeddings

logger = logging.getLogger(__name__)

COLLECTION_NAME = settings.DOC_COLLECTION

# Chunk size for splitting long documents
CHUNK_SIZE = 1500  # characters
CHUNK_OVERLAP = 200


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def _content_hash(content: str) -> str:
    """Stable hash, to tell whether a chunk changed."""
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]


class VectorStoreManager:
    """Manages one collection of DocChunk rows for document retrieval."""

    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name

    def _rows(self):
        from apps.ai_assistant.models import DocChunk
        return DocChunk.objects.filter(collection=self.collection_name)

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        """
        Index a document: split into chunks, embed, and replace its rows.
        Returns the number of chunks the document now has. A document whose chunks and
        embedding model are unchanged is left as it is (no embedding call).
        """
        from apps.ai_assistant.models import DocChunk

        chunks = _chunk_text(content)
        hashes = [_content_hash(c) for c in chunks]
        meta = metadata or {}
        model = embeddings.embed_model()

        existing = list(self._rows().filter(doc_id=doc_id).order_by("chunk_index")
                        .values_list("content_hash", "embed_model", "metadata"))
        unchanged = (
            [h for h, _, _ in existing] == hashes
            and all(m == model for _, m, _ in existing)
            and all({k: v for k, v in md.items()
                     if k not in ("doc_id", "chunk_index", "total_chunks")} == meta
                    for _, _, md in existing)
        )
        if existing and unchanged:
            return len(chunks)

        vectors = embeddings.embed_documents(chunks) if chunks else []
        rows = [
            DocChunk(
                collection=self.collection_name, doc_id=doc_id, chunk_index=i,
                content=chunk, content_hash=hashes[i],
                metadata={**meta, "doc_id": doc_id, "chunk_index": i, "total_chunks": len(chunks)},
                embedding=pack(vec), dim=len(vec), embed_model=model,
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        with transaction.atomic():
            self._rows().filter(doc_id=doc_id).delete()
            DocChunk.objects.bulk_create(rows)
        return len(rows)

    def search(self, query: str, n_results: int = 5, where: dict | None = None) -> list[dict]:
        """
        Search for relevant document chunks.
        Returns list of {content, metadata, distance}, nearest first. distance is cosine
        distance: 0 = same meaning, 1 = unrelated.

        Raises embeddings.EmbeddingUnavailable when this instance cannot embed the query,
        and ValueError when the index was built with a different embedding model.
        """
        rows = self._rows()
        if where:
            rows = rows.filter(metadata__contains=where)
        model = embeddings.embed_model()
        stale = rows.exclude(embed_model=model).values_list("embed_model", flat=True).first()
        if stale is not None:
            raise ValueError(
                f"The document index was built with embedding model '{stale}', and this "
                f"instance now uses '{model}'. Rebuild it: manage.py index_docs --reset")
        if not rows.exists():
            return []

        q = embeddings.embed_query(query)
        candidates = ((pk, unpack(bytes(emb))) for pk, emb in rows.values_list("pk", "embedding").iterator())
        nearest = top_k(q, candidates, k=n_results)
        found = {r.pk: r for r in self._rows().filter(pk__in=[pk for pk, _ in nearest])}
        return [
            {"content": found[pk].content, "metadata": found[pk].metadata, "distance": distance}
            for pk, distance in nearest
        ]

    def delete_document(self, doc_id: str) -> None:
        """Remove all chunks for a given document."""
        self._rows().filter(doc_id=doc_id).delete()

    def reset(self) -> None:
        """Delete every chunk in the collection."""
        self._rows().delete()
        logger.info("Vector store collection '%s' reset", self.collection_name)

    def stats(self) -> dict:
        """Return basic stats about the collection."""
        return {
            "collection": self.collection_name,
            "count": self._rows().count(),
            "documents": self._rows().values("doc_id").distinct().count(),
            "embed_model": embeddings.embed_model(),
        }
