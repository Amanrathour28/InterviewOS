"""
Adversarial Tests for Semantic Evidence Grounding & Fabricated Quote Defense — Phase 15.1.

Tests that:
1. A valid evidence ID citing irrelevant evidence is marked UNSUPPORTED.
2. Fabricated quotes are detected, rejected, and flagged.
3. Partial support is correctly distinguished from full support.
4. Genuine candidate evidence produces verified quotes and SUPPORTED claims.
"""

import pytest
from app.agents.evaluation_agents import (
    QuoteVerificationEngine,
    SemanticGroundingEngine,
)
from app.schemas.evaluation import GroundingStatus


def test_valid_id_with_irrelevant_evidence_rejected_as_unsupported():
    """
    Attack: AI generates a claim "Candidate demonstrated strong Kafka expertise"
    and cites evidence_1, but evidence_1 only discusses Redis caching.
    """
    evidence_lookup = {
        "ev-redis-1": {
            "id": "ev-redis-1",
            "content": "Candidate explained using Redis with LRU cache eviction policy for HTTP sessions.",
            "is_candidate_evidence": True,
        }
    }

    claim = "Candidate demonstrated deep production expertise in Apache Kafka partition rebalancing."
    grounded = SemanticGroundingEngine.validate_claim_grounding(
        claim_text=claim,
        cited_evidence_ids=["ev-redis-1"],
        evidence_lookup=evidence_lookup,
    )

    assert grounded.grounding_status == GroundingStatus.UNSUPPORTED
    assert "mismatch" in grounded.grounding_reason.lower() or "not support" in grounded.grounding_reason.lower()


def test_fabricated_quote_detection_and_rejection():
    """
    Attack: AI attributes a quote 'We processed 10 million Kafka messages per second' to candidate,
    when candidate never made that statement.
    """
    evidence_items = [
        {
            "id": "ev-cand-1",
            "content": "We had about ten thousand active users on the platform.",
            "is_candidate_evidence": True,
        },
        {
            "id": "ev-cand-2",
            "content": "I primarily worked on Python backend APIs and relational database indexing.",
            "is_candidate_evidence": True,
        },
    ]

    fabricated_quote = "We processed 10 million Kafka messages per second in real time."
    verification = QuoteVerificationEngine.verify_quote(
        quote=fabricated_quote,
        evidence_items=evidence_items,
    )

    assert verification.is_verified is False
    assert verification.matching_evidence_id is None or verification.similarity_score < 0.75
    assert "not found" in (verification.rejection_reason or "").lower()


def test_genuine_quote_verification():
    """
    Candidate genuine statement in transcript segment is accurately verified.
    """
    evidence_items = [
        {
            "id": "ev-cand-1",
            "content": "I implemented a consistent hashing ring to distribute shard keys evenly.",
            "is_candidate_evidence": True,
        }
    ]

    genuine_quote = "implemented a consistent hashing ring to distribute shard keys"
    verification = QuoteVerificationEngine.verify_quote(
        quote=genuine_quote,
        evidence_items=evidence_items,
    )

    assert verification.is_verified is True
    assert verification.matching_evidence_id == "ev-cand-1"
    assert verification.similarity_score >= 0.75


def test_partial_vs_full_support_distinction():
    """
    Tests distinction between full substantive support and partial support.
    """
    evidence_lookup = {
        "ev-arch-1": {
            "id": "ev-arch-1",
            "content": "Candidate drew a high level design diagram with API gateway and microservices.",
            "is_candidate_evidence": True,
        }
    }

    full_claim = "Candidate drew high level architecture design with API gateway."
    res_full = SemanticGroundingEngine.validate_claim_grounding(
        claim_text=full_claim,
        cited_evidence_ids=["ev-arch-1"],
        evidence_lookup=evidence_lookup,
    )
    assert res_full.grounding_status == GroundingStatus.SUPPORTED

    overextended_claim = "Candidate drew high level architecture and configured Kubernetes multi-region failover cluster."
    res_partial = SemanticGroundingEngine.validate_claim_grounding(
        claim_text=overextended_claim,
        cited_evidence_ids=["ev-arch-1"],
        evidence_lookup=evidence_lookup,
    )
    assert res_partial.grounding_status in [GroundingStatus.PARTIALLY_SUPPORTED, GroundingStatus.UNSUPPORTED]


def test_nonexistent_evidence_id_rejected():
    """
    Tests that citing a completely fabricated evidence UUID is rejected.
    """
    evidence_lookup = {
        "ev-real-1": {"id": "ev-real-1", "content": "Some real evidence.", "is_candidate_evidence": True}
    }

    res = SemanticGroundingEngine.validate_claim_grounding(
        claim_text="Candidate is an expert in algorithms.",
        cited_evidence_ids=["ev-fake-uuid-999"],
        evidence_lookup=evidence_lookup,
    )
    assert res.grounding_status == GroundingStatus.UNSUPPORTED
    assert "exist in persisted evidence" in res.grounding_reason.lower() or "not found" in res.grounding_reason.lower()
