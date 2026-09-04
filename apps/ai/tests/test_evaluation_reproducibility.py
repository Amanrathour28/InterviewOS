"""
Reproducibility & Order-Independence Tests — Phase 15.1.

Tests that:
1. Evidence list order does not alter grounding validation results.
2. Multiple runs on the same input produce 100% identical grounding states.
"""

import pytest
from app.agents.evaluation_agents import QuoteVerificationEngine, SemanticGroundingEngine


def test_evidence_order_independence():
    """
    Shuffling evidence order must produce identical grounding status.
    """
    ev_a = {
        "id": "ev-1",
        "content": "Candidate implemented merge sort algorithm with O(N log N) runtime complexity.",
        "is_candidate_evidence": True,
    }
    ev_b = {
        "id": "ev-2",
        "content": "Candidate explained trade-offs between QuickSort and MergeSort.",
        "is_candidate_evidence": True,
    }

    claim = "Candidate implemented MergeSort and discussed complexity trade-offs."

    lookup_order_1 = {"ev-1": ev_a, "ev-2": ev_b}
    res_1 = SemanticGroundingEngine.validate_claim_grounding(claim, ["ev-1", "ev-2"], lookup_order_1)

    lookup_order_2 = {"ev-2": ev_b, "ev-1": ev_a}
    res_2 = SemanticGroundingEngine.validate_claim_grounding(claim, ["ev-2", "ev-1"], lookup_order_2)

    assert res_1.grounding_status == res_2.grounding_status
    assert res_1.grounding_status.value == "SUPPORTED"


def test_quote_verification_order_independence():
    """
    Quote verification order independence across candidate speech records.
    """
    items_order_1 = [
        {"id": "ev-1", "content": "I like building resilient backends.", "is_candidate_evidence": True},
        {"id": "ev-2", "content": "We had 500 requests per second sustained load.", "is_candidate_evidence": True},
    ]
    items_order_2 = [
        {"id": "ev-2", "content": "We had 500 requests per second sustained load.", "is_candidate_evidence": True},
        {"id": "ev-1", "content": "I like building resilient backends.", "is_candidate_evidence": True},
    ]

    q = "500 requests per second sustained load"
    v1 = QuoteVerificationEngine.verify_quote(q, items_order_1)
    v2 = QuoteVerificationEngine.verify_quote(q, items_order_2)

    assert v1.is_verified == v2.is_verified == True
    assert v1.matching_evidence_id == v2.matching_evidence_id == "ev-2"
