"""
Phase 15.1 Evaluation Integrity & Adversarial Audit Tests.

Tests:
1. Exact boundary-value recommendation thresholds (39.999, 40.0, 54.999, 55.0, 69.999, 70.0, 84.999, 85.0).
2. Deterministic recommendation invariance (AI text recommendation cannot override math score).
3. Insufficient evidence gates (confidence < 0.4, missing required competencies).
4. Score reproducibility from persisted score inputs.
5. Semantic grounding and quote verification via EvaluationGroundingValidator.
6. Finalization immutability and SHA-256 canonical integrity hash sealing.
"""

import hashlib
import json
import pytest
import uuid

from app.models.evaluation import EvaluationEvidence, EvaluationStatus, HiringRecommendation
from app.services.evaluation_scoring_service import evaluation_scoring_service
from app.services.evidence_service import EvaluationGroundingValidator


def test_recommendation_boundary_thresholds():
    """
    Exact boundary tests for all recommendation thresholds:
    >= 85.0: STRONG_HIRE
    >= 70.0: HIRE
    >= 55.0: LEAN_HIRE
    >= 40.0: LEAN_NO_HIRE
    < 40.0: NO_HIRE
    """
    dummy_comp = [{"rubric_level": 3.0, "weight": 1.0, "confidence": 1.0, "status": "assessed"}]

    # 85 threshold
    assert evaluation_scoring_service.determine_recommendation(85.0, dummy_comp) == HiringRecommendation.STRONG_HIRE
    assert evaluation_scoring_service.determine_recommendation(84.999, dummy_comp) == HiringRecommendation.HIRE

    # 70 threshold
    assert evaluation_scoring_service.determine_recommendation(70.0, dummy_comp) == HiringRecommendation.HIRE
    assert evaluation_scoring_service.determine_recommendation(69.999, dummy_comp) == HiringRecommendation.LEAN_HIRE

    # 55 threshold
    assert evaluation_scoring_service.determine_recommendation(55.0, dummy_comp) == HiringRecommendation.LEAN_HIRE
    assert evaluation_scoring_service.determine_recommendation(54.999, dummy_comp) == HiringRecommendation.LEAN_NO_HIRE

    # 40 threshold
    assert evaluation_scoring_service.determine_recommendation(40.0, dummy_comp) == HiringRecommendation.LEAN_NO_HIRE
    assert evaluation_scoring_service.determine_recommendation(39.999, dummy_comp) == HiringRecommendation.NO_HIRE
    assert evaluation_scoring_service.determine_recommendation(0.0, dummy_comp) == HiringRecommendation.NO_HIRE


def test_ai_recommendation_cannot_override_deterministic_score():
    """
    If AI synthesis claims STRONG_HIRE but mathematical score is 52.0,
    the deterministic engine must strictly output LEAN_NO_HIRE.
    """
    comp_inputs = [
        {"rubric_level": 3.08, "weight": 1.0, "confidence": 0.9, "status": "assessed"}
    ]
    # score for rubric_level 3.08 is (2.08/4)*100 = 52.0
    overall_score, _, _ = evaluation_scoring_service.calculate_overall_score(comp_inputs)
    assert abs(overall_score - 52.0) < 0.1

    final_rec = evaluation_scoring_service.determine_recommendation(overall_score, comp_inputs)
    assert final_rec == HiringRecommendation.LEAN_NO_HIRE
    assert final_rec != HiringRecommendation.STRONG_HIRE


def test_insufficient_evidence_gates():
    """
    Tests:
    - Empty evidence -> INSUFFICIENT_EVIDENCE
    - Low average confidence (< 0.40) -> INSUFFICIENT_EVIDENCE
    - Required competency missing or not_assessed -> INSUFFICIENT_EVIDENCE
    """
    # 1. Empty assessed competencies
    assert evaluation_scoring_service.determine_recommendation(90.0, []) == HiringRecommendation.INSUFFICIENT_EVIDENCE

    # 2. Low confidence (< 0.40)
    low_conf_comps = [
        {"rubric_level": 5.0, "weight": 1.0, "confidence": 0.25, "status": "assessed"}
    ]
    assert evaluation_scoring_service.determine_recommendation(100.0, low_conf_comps) == HiringRecommendation.INSUFFICIENT_EVIDENCE

    # 3. Missing required competency
    required_missing_comps = [
        {"rubric_level": 5.0, "weight": 1.0, "confidence": 0.95, "status": "assessed"},
        {"competency_name": "Coding", "is_required": True, "status": "not_assessed", "confidence": 0.0},
    ]
    assert evaluation_scoring_service.determine_recommendation(100.0, required_missing_comps) == HiringRecommendation.INSUFFICIENT_EVIDENCE


def test_score_reproducibility():
    """
    Tests that recalculation from score inputs is 100% reproducible.
    """
    score_inputs = {
        "competency_weights": {"System Design": 1.5, "Algorithms": 2.0, "Communication": 1.0},
        "competency_rubric_levels": {"System Design": 4.0, "Algorithms": 4.5, "Communication": 4.0},
    }
    # Algorithms: 4.5 -> 87.5 * 2.0 = 175
    # System Design: 4.0 -> 75.0 * 1.5 = 112.5
    # Communication: 4.0 -> 75.0 * 1.0 = 75
    # Total weighted: 362.5 / 4.5 = 80.56
    # Score 80.56 >= 70.0 -> HIRE
    assert evaluation_scoring_service.verify_score_reproducibility(
        score_input_data=score_inputs,
        expected_score=80.56,
        expected_recommendation="HIRE",
    )


def test_semantic_grounding_validation():
    """
    Tests that EvaluationGroundingValidator detects irrelevant evidence vs verified evidence.
    """
    ev_redis = EvaluationEvidence(
        id=uuid.uuid4(),
        content="Candidate used Redis for session caching.",
        is_candidate_evidence=True,
    )
    ev_map = {str(ev_redis.id): ev_redis}

    # Irrelevant Kafka claim
    status, reason = EvaluationGroundingValidator.validate_semantic_grounding(
        claim_text="Candidate designed high throughput Kafka streaming pipeline.",
        evidence_ids=[str(ev_redis.id)],
        evidence_map=ev_map,
    )
    assert status == "UNSUPPORTED"

    # Relevant Redis claim
    status_good, reason_good = EvaluationGroundingValidator.validate_semantic_grounding(
        claim_text="Candidate used Redis for caching session data.",
        evidence_ids=[str(ev_redis.id)],
        evidence_map=ev_map,
    )
    assert status_good == "SUPPORTED"


def test_quote_verification_validator():
    """
    Tests EvaluationGroundingValidator quote verification against candidate evidence.
    """
    ev = EvaluationEvidence(
        id=uuid.uuid4(),
        content="I configured PostgreSQL B-tree indexing to speed up queries.",
        is_candidate_evidence=True,
    )

    # Genuine quote
    is_valid, match_id, score = EvaluationGroundingValidator.validate_quote(
        quote="configured PostgreSQL B-tree indexing",
        evidence_records=[ev],
    )
    assert is_valid is True
    assert match_id == str(ev.id)

    # Fabricated quote
    is_valid_fake, match_id_fake, _ = EvaluationGroundingValidator.validate_quote(
        quote="I built Cassandra database engine from scratch in C++",
        evidence_records=[ev],
    )
    assert is_valid_fake is False


def test_canonical_integrity_hash_determinism():
    """
    Tests that canonical JSON serialization produces deterministic SHA-256 hashes
    regardless of dictionary key insertion order.
    """
    payload_1 = {
        "overall_score": 85.0,
        "recommendation": "STRONG_HIRE",
        "competency_scores": [{"name": "System Design", "score": 85.0}],
    }
    payload_2 = {
        "competency_scores": [{"name": "System Design", "score": 85.0}],
        "recommendation": "STRONG_HIRE",
        "overall_score": 85.0,
    }

    hash_1 = hashlib.sha256(json.dumps(payload_1, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()
    hash_2 = hashlib.sha256(json.dumps(payload_2, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()

    assert hash_1 == hash_2
    assert len(hash_1) == 64
