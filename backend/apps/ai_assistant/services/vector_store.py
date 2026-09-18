"""
Vector store manager — indexes documents into ChromaDB for RAG retrieval.

Usage:
    from apps.ai_assistant.services.vector_store import VectorStoreManager

    vs = VectorStoreManager()
    vs.index_document("path/to/readme.md", "markdown content...", {"source": "readme"})
    results = vs.search("how do I create an order?", n_results=5)
"""
import hashlib
import logging
import os
from pathlib import Path

import chromadb
from django.conf import settings

logger = logging.getLogger(__name__)

# Where to persist the vector DB on disk
CHROMA_PERSIST_DIR = getattr(
    settings,
    "CHROMA_PERSIST_DIR",
    os.path.join(settings.BASE_DIR, ".chroma_db"),
)
COLLECTION_NAME = getattr(settings, "CHROMA_COLLECTION", "commerce_expert_docs")

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
    """Stable hash for dedup."""
    return hashlib.md5(content.encode()).hexdigest()[:12]


class VectorStoreManager:
    """Manages a ChromaDB collection for document retrieval."""

    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR, collection_name: str = COLLECTION_NAME):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        """
        Index a document by splitting into chunks and upserting into ChromaDB.
        Returns the number of chunks indexed.
        """
        chunks = _chunk_text(content)
        meta = metadata or {}

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}::chunk_{i}::{_content_hash(chunk)}"
            chunk_meta = {
                **meta,
                "doc_id": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(chunk_meta)

        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        return len(ids)

    def search(self, query: str, n_results: int = 5, where: dict | None = None) -> list[dict]:
        """
        Search for relevant document chunks.
        Returns list of {content, metadata, distance}.
        """
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        try:
            results = self.collection.query(**kwargs)
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []

        items = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                items.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
        return items

    def delete_document(self, doc_id: str) -> None:
        """Remove all chunks for a given document."""
        # ChromaDB where filter on metadata
        self.collection.delete(where={"doc_id": doc_id})

    def reset(self) -> None:
        """Delete and recreate the collection."""
        self.client.delete_collection(self.collection_name)
        self._collection = None
        logger.info("Vector store collection '%s' reset", self.collection_name)

    def stats(self) -> dict:
        """Return basic stats about the collection."""
        return {
            "collection": self.collection_name,
            "count": self.collection.count(),
            "persist_dir": self.persist_dir,
        }
