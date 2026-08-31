"""
RAG (Retrieval-Augmented Generation) service — ties the vector store and LLM together.

This is the main entry point for the AI assistant. It:
1. Takes a user question + optional mode
2. Retrieves relevant context from the vector store
3. Optionally wraps the query with mode-specific framing
4. Sends both to Ollama for generation
5. Scores confidence on the answer
6. If low confidence, escalates to Claude API
7. If cross-instance data needed, queries WCHQ
8. Returns the answer with source references and escalation metadata

Modes: general, developer, debugger, user_support, code_review, test_writer

Usage:
    from apps.ai_assistant.services.rag import RAGService

    rag = RAGService()
    answer = rag.ask("How do I create an invoice from an order?", mode="developer")
    answer = rag.ask("TypeError: ...", mode="debugger", extra_context=traceback)
    # answer now includes: confidence, tier_used, escalation_log
"""
import logging

from .ollama_client import OllamaClient
from .prompt_templates import wrap_query, get_available_modes
from .vector_store import VectorStoreManager
from .escalation import (
    score_confidence,
    escalate_to_claude,
    query_wchq_data,
    log_escalation,
    CONFIDENCE_ESCALATE_THRESHOLD,
)

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
        escalate: bool = True,
    ) -> dict:
        """
        Answer a question using RAG with escalation chain.

        Flow:
            1. Alice answers locally (Ollama RAG)
            2. Score confidence on the answer
            3. If low confidence → escalate to Claude API
            4. If cross-instance data needed → query WCHQ
            5. Log escalations as AliceObservation

        Set escalate=False to skip the escalation chain (local-only).

        Returns {"answer": str, "sources": list[dict], "model": str,
                 "mode": str, "confidence": dict, "tier_used": str}.
        """
        context, sources = self._retrieve_context(question, n_results=n_results)

        if not context:
            logger.info("No relevant context found for: %s", question[:100])

        # Wrap query with mode-specific framing
        wrapped_question = wrap_query(mode, question, extra_context=extra_context)

        # --- Tier 1: Alice local (Ollama RAG) ---
        answer = self.llm_client.generate(
            prompt=wrapped_question,
            context=context,
            history=history,
            mode=mode,
        )

        confidence = score_confidence(answer, sources, question)
        tier_used = "alice_local"
        escalation_log = []

        if not escalate:
            return {
                "answer": answer,
                "sources": sources,
                "model": self.llm_client.model,
                "mode": mode,
                "context_chunks": len(sources),
                "confidence": {
                    "score": confidence.score,
                    "context_score": confidence.context_score,
                    "answer_score": confidence.answer_score,
                    "chunk_count": confidence.chunk_count,
                    "best_distance": confidence.best_distance,
                },
                "tier_used": tier_used,
            }

        # --- Tier 2: Claude API (low confidence) ---
        if confidence.score < CONFIDENCE_ESCALATE_THRESHOLD:
            try:
                claude_result = escalate_to_claude(
                    question=question,
                    local_answer=answer,
                    context=context,
                    history=history,
                    mode=mode,
                )
                answer = claude_result["answer"]
                tier_used = "claude_api"
                escalation_log.append({
                    "from": "alice_local",
                    "to": "claude_api",
                    "reason": "low_confidence",
                    "local_confidence": confidence.score,
                    "model": claude_result["model"],
                })
                log_escalation(
                    question=question,
                    local_confidence=confidence.score,
                    tier_used="claude_api",
                    reason=f"Confidence {confidence.score:.1%} below threshold "
                           f"{CONFIDENCE_ESCALATE_THRESHOLD:.0%}",
                )
                logger.info(
                    "Escalated to Claude API: confidence=%.1f%%, question=%s",
                    confidence.score * 100, question[:80],
                )
            except ConnectionError as e:
                logger.warning("Claude API escalation failed: %s", e)
                escalation_log.append({
                    "from": "alice_local",
                    "to": "claude_api",
                    "reason": "low_confidence",
                    "error": str(e),
                })

        # --- Tier 3: WCHQ data query (cross-instance) ---
        if confidence.needs_wchq:
            try:
                wchq_result = query_wchq_data(question=question)
                wchq_data = wchq_result["data"]
                # Re-ask with WCHQ data as additional context
                wchq_context = f"Cross-instance data from WCHQ:\n{wchq_data}\n\n{context}"
                answer = self.llm_client.generate(
                    prompt=wrapped_question,
                    context=wchq_context,
                    history=history,
                    mode=mode,
                )
                tier_used = "wchq_data"
                escalation_log.append({
                    "from": tier_used,
                    "to": "wchq",
                    "reason": "cross_instance_data",
                })
                log_escalation(
                    question=question,
                    local_confidence=confidence.score,
                    tier_used="wchq",
                    reason="Question references cross-instance data",
                )
            except ConnectionError as e:
                logger.warning("WCHQ data query failed: %s", e)
                escalation_log.append({
                    "from": tier_used,
                    "to": "wchq",
                    "reason": "cross_instance_data",
                    "error": str(e),
                })

        return {
            "answer": answer,
            "sources": sources,
            "model": self.llm_client.model,
            "mode": mode,
            "context_chunks": len(sources),
            "confidence": {
                "score": confidence.score,
                "context_score": confidence.context_score,
                "answer_score": confidence.answer_score,
                "chunk_count": confidence.chunk_count,
                "best_distance": confidence.best_distance,
                "needs_wchq": confidence.needs_wchq,
            },
            "tier_used": tier_used,
            "escalation_log": escalation_log,
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
