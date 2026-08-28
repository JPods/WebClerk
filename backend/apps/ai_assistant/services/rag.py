"""
RAG (Retrieval-Augmented Generation) service — ties the vector store and LLM together.

This is the main entry point for the AI assistant. It:
1. Takes a user question + optional mode
2. Retrieves relevant context from the vector store
3. Optionally wraps the query with mode-specific framing
4. Sends both to Ollama for generation
5. Returns the answer with source references

Modes: general, developer, debugger, user_support, code_review, test_writer

Usage:
    from apps.ai_assistant.services.rag import RAGService

    rag = RAGService()
    answer = rag.ask("How do I create an invoice from an order?", mode="developer")
    answer = rag.ask("TypeError: ...", mode="debugger", extra_context=traceback)
"""
import logging

from .ollama_client import OllamaClient
from .prompt_templates import wrap_query, get_available_modes
from .vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

# Maximum context size to send to the LLM (in characters)
MAX_CONTEXT_CHARS = 8000
# Similarity threshold — ignore chunks with distance above this
MAX_DISTANCE = 1.2


class RAGService:
    """Orchestrates retrieval-augmented generation."""

    def __init__(
        self,
        vector_store: VectorStoreManager | None = None,
        llm_client: OllamaClient | None = None,
    ):
        self.vector_store = vector_store or VectorStoreManager()
        self.llm_client = llm_client or OllamaClient()

    def _retrieve_context(self, query: str, n_results: int = 6) -> tuple[str, list[dict]]:
        """
        Search the vector store and build a context string.
        Returns (context_text, source_documents).
        """
        results = self.vector_store.search(query, n_results=n_results)

        # Filter by relevance
        relevant = [r for r in results if r["distance"] is None or r["distance"] < MAX_DISTANCE]

        if not relevant:
            return "", []

        context_parts = []
        sources = []
        total_chars = 0

        for r in relevant:
            content = r["content"]
            if total_chars + len(content) > MAX_CONTEXT_CHARS:
                break
            meta = r["metadata"]
            source_label = meta.get("doc_id", meta.get("source", "unknown"))
            context_parts.append(f"--- Source: {source_label} ---\n{content}")
            sources.append({
                "source": source_label,
                "type": meta.get("type", "unknown"),
                "distance": r["distance"],
            })
            total_chars += len(content)

        return "\n\n".join(context_parts), sources

    def ask(
        self,
        question: str,
        history: list[dict] | None = None,
        n_results: int = 6,
        mode: str = "general",
        extra_context: str = "",
    ) -> dict:
        """
        Answer a question using RAG.
        Returns {"answer": str, "sources": list[dict], "model": str, "mode": str}.
        """
        context, sources = self._retrieve_context(question, n_results=n_results)

        if not context:
            logger.info("No relevant context found for: %s", question[:100])

        # Wrap query with mode-specific framing
        wrapped_question = wrap_query(mode, question, extra_context=extra_context)

        answer = self.llm_client.generate(
            prompt=wrapped_question,
            context=context,
            history=history,
            mode=mode,
        )

        return {
            "answer": answer,
            "sources": sources,
            "model": self.llm_client.model,
            "mode": mode,
            "context_chunks": len(sources),
        }

    def ask_stream(
        self,
        question: str,
        history: list[dict] | None = None,
        n_results: int = 6,
        mode: str = "general",
        extra_context: str = "",
    ):
        """
        Streaming variant — yields content chunks.
        Call _retrieve_context first, then stream from LLM.
        Returns a generator and the sources list.
        """
        context, sources = self._retrieve_context(question, n_results=n_results)

        wrapped_question = wrap_query(mode, question, extra_context=extra_context)

        stream = self.llm_client.stream(
            prompt=wrapped_question,
            context=context,
            history=history,
            mode=mode,
        )

        return stream, sources

    @staticmethod
    def available_modes() -> list[dict]:
        """Return the list of available AI modes."""
        return get_available_modes()

    def health_check(self) -> dict:
        """Check if all components are operational."""
        ollama_ok = self.llm_client.is_available()
        vs_stats = self.vector_store.stats()

        return {
            "ollama_available": ollama_ok,
            "ollama_model": self.llm_client.model,
            "ollama_url": self.llm_client.base_url,
            "available_models": self.llm_client.list_models() if ollama_ok else [],
            "vector_store": vs_stats,
            "status": "ok" if ollama_ok and vs_stats["count"] > 0 else "degraded",
        }
