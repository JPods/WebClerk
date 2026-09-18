"""Tests for the AI escalation chain — confidence scoring and PII scrubbing."""
import pytest
from apps.ai_assistant.services.escalation import score_confidence, CONFIDENCE_ESCALATE_THRESHOLD
from apps.ai_assistant.services.pii_scrub import scrub_pii


# ── Confidence Scoring ───────────────────────────────────────────────

class TestScoreConfidence:
    """Test score_confidence() — the gate that decides whether to escalate."""

    def test_high_confidence_stays_local(self):
        """Good context + substantive answer → above threshold."""
        cs = score_confidence(
            answer="The order_to_invoice function handles this. It copies all line fields via _copy_common_line_fields and creates an Invoice record.",
            sources=[
                {'distance': 0.3, 'source': 'transaction_flow.py'},
                {'distance': 0.5, 'source': 'views.py'},
                {'distance': 0.7, 'source': 'models.py'},
            ],
            question="How do I convert an order to an invoice?",
        )
        assert cs.score >= CONFIDENCE_ESCALATE_THRESHOLD
        assert cs.chunk_count == 3
        assert cs.hedging_count == 0
        assert cs.best_distance == 0.3

    def test_no_context_low_confidence(self):
        """No context chunks → low context score → likely below threshold."""
        cs = score_confidence(
            answer="I'm not sure about that.",
            sources=[],
            question="What is the discount tier?",
        )
        assert cs.score < CONFIDENCE_ESCALATE_THRESHOLD
        assert cs.chunk_count == 0
        assert cs.best_distance == 99.0

    def test_hedging_reduces_confidence(self):
        """Hedging phrases in the answer reduce the answer score."""
        cs_no_hedge = score_confidence(
            answer="The function is in transaction_flow.py line 42.",
            sources=[{'distance': 0.4, 'source': 'flow.py'}],
            question="Where is proposal_to_order?",
        )
        cs_hedge = score_confidence(
            answer="I'm not sure, but I think the function might be somewhere. I don't have enough information.",
            sources=[{'distance': 0.4, 'source': 'flow.py'}],
            question="Where is proposal_to_order?",
        )
        assert cs_hedge.score < cs_no_hedge.score
        assert cs_hedge.hedging_count >= 2

    def test_short_answer_suspicious(self):
        """Very short answers get lower answer scores."""
        cs_short = score_confidence(
            answer="Yes.",
            sources=[{'distance': 0.3, 'source': 'doc.md'}],
            question="Can I do X?",
        )
        cs_long = score_confidence(
            answer="Yes, you can do X by calling the proposal_to_order function. It copies all line fields and creates a new Order record.",
            sources=[{'distance': 0.3, 'source': 'doc.md'}],
            question="Can I do X?",
        )
        assert cs_short.answer_score < cs_long.answer_score

    def test_distant_matches_lower_context_score(self):
        """Sources with high distance scores reduce context quality."""
        cs_close = score_confidence(
            answer="The answer is in the docs.",
            sources=[{'distance': 0.3, 'source': 'a.md'}],
            question="How?",
        )
        cs_far = score_confidence(
            answer="The answer is in the docs.",
            sources=[{'distance': 1.1, 'source': 'a.md'}],
            question="How?",
        )
        assert cs_close.context_score > cs_far.context_score

    def test_more_chunks_higher_context(self):
        """More relevant chunks = higher context score."""
        cs_one = score_confidence(
            answer="A" * 200,
            sources=[{'distance': 0.5, 'source': 'a.md'}],
            question="Q",
        )
        cs_four = score_confidence(
            answer="A" * 200,
            sources=[
                {'distance': 0.5, 'source': 'a.md'},
                {'distance': 0.6, 'source': 'b.md'},
                {'distance': 0.7, 'source': 'c.md'},
                {'distance': 0.8, 'source': 'd.md'},
            ],
            question="Q",
        )
        assert cs_four.context_score > cs_one.context_score

    def test_score_bounds(self):
        """Score is always between 0 and 1."""
        for answer, sources in [
            ("", []),
            ("x", [{'distance': 99}]),
            ("A" * 1000, [{'distance': 0.01}] * 10),
            ("I don't know. I'm not sure. I cannot find it. Based on limited info.", []),
        ]:
            cs = score_confidence(answer, sources, "Q")
            assert 0.0 <= cs.score <= 1.0
            assert 0.0 <= cs.context_score <= 1.0
            assert 0.0 <= cs.answer_score <= 1.0


# ── PII Scrubbing ────────────────────────────────────────────────────

class TestPIIScrub:
    """Test scrub_pii() — the filter before data leaves the installation."""

    def test_scrubs_email(self):
        text, count = scrub_pii("Contact john.doe@example.com for details")
        assert '<email>' in text
        assert 'john.doe@example.com' not in text
        assert count >= 1

    def test_scrubs_phone(self):
        text, count = scrub_pii("Call 555-123-4567 or (555) 987-6543")
        assert '<phone>' in text
        assert '555-123-4567' not in text
        assert count >= 1

    def test_scrubs_ssn(self):
        text, count = scrub_pii("SSN is 123-45-6789")
        assert '<ssn>' in text
        assert '123-45-6789' not in text
        assert count >= 1

    def test_scrubs_name_after_prefix(self):
        text, count = scrub_pii("Customer John Smith placed an order")
        assert '<name>' in text
        assert 'John Smith' not in text

    def test_no_scrub_on_clean_text(self):
        clean = "How do I create an invoice from an order?"
        text, count = scrub_pii(clean)
        assert text == clean
        assert count == 0

    def test_multiple_pii_types(self):
        text, count = scrub_pii(
            "Mr. James at james@co.com, phone 555-111-2222, SSN 999-88-7777"
        )
        assert '<email>' in text
        assert '<phone>' in text
        assert '<ssn>' in text
        assert count >= 3

    def test_preserves_non_pii_content(self):
        text, _ = scrub_pii("How many orders did we ship last month?")
        assert text == "How many orders did we ship last month?"
