"""
Unit and algorithmic tests for deterministic Evaluation Scoring Service.
Ensures Phase 15 mathematical rigor, weight normalization, recommendation thresholds,
and 100% reproducible score calculations.
"""

import pytest
from app.models.evaluation import HiringRecommendation
from app.services.evaluation_scoring_service import EvaluationScoringService


def test_rubric_level_to_score_mapping():
    assert EvaluationScoringService.rubric_level_to_score(1.0) == 0.0
    assert EvaluationScoringService.rubric_level_to_score(2.0) == 25.0
    assert EvaluationScoringService.rubric_level_to_score(3.0) == 50.0
    assert EvaluationScoringService.rubric_level_to_score(4.0) == 75.0
    assert EvaluationScoringService.rubric_level_to_score(5.0) == 100.0
    # Clamping tests
    assert EvaluationScoringService.rubric_level_to_score(0.5) == 0.0
    assert EvaluationScoringService.rubric_level_to_score(5.5) == 100.0


def test_score_to_rubric_level_mapping():
    assert EvaluationScoringService.score_to_rubric_level(100.0) == 5.0
    assert EvaluationScoringService.score_to_rubric_level(75.0) == 4.0
    assert EvaluationScoringService.score_to_rubric_level(50.0) == 3.0
    assert EvaluationScoringService.score_to_rubric_level(25.0) == 2.0
    assert EvaluationScoringService.score_to_rubric_level(0.0) == 1.0


def test_calculate_overall_score_weighted():
    competency_scores = [
        {"name": "Python & Algorithms", "rubric_level": 4.0, "weight": 2.0, "confidence": 0.9, "status": "assessed"}, # score 75.0 * 2 = 150
        {"name": "System Design", "rubric_level": 5.0, "weight": 1.0, "confidence": 0.95, "status": "assessed"},       # score 100.0 * 1 = 100
        {"name": "Communication", "rubric_level": 3.0, "weight": 1.0, "confidence": 0.85, "status": "assessed"},       # score 50.0 * 1 = 50
    ]
    # Sum weights = 4.0. Weighted = (150 + 100 + 50) / 4 = 300 / 4 = 75.0
    # Weighted rubric = (4*2 + 5*1 + 3*1) / 4 = 16 / 4 = 4.0
    # Avg confidence = (0.9 + 0.95 + 0.85) / 3 = 0.90
    score, rubric, conf = EvaluationScoringService.calculate_overall_score(competency_scores)
    assert score == 75.0
    assert rubric == 4.0
    assert conf == 0.90


def test_calculate_overall_score_default_weights():
    competency_scores = [
        {"name": "Comp A", "rubric_level": 3.0, "weight": 1.0, "confidence": 1.0, "status": "assessed"}, # 50.0
        {"name": "Comp B", "rubric_level": 5.0, "weight": 1.0, "confidence": 1.0, "status": "assessed"}, # 100.0
    ]
    # Default weight is 1.0 each -> (50 + 100) / 2 = 75.0
    score, rubric, conf = EvaluationScoringService.calculate_overall_score(competency_scores)
    assert score == 75.0
    assert rubric == 4.0
    assert conf == 1.0


def test_calculate_overall_score_empty():
    score, rubric, conf = EvaluationScoringService.calculate_overall_score([])
    assert score == 0.0
    assert rubric == 0.0
    assert conf == 0.0


def test_determine_recommendation_thresholds():
    assessed_comps = [{"name": "C1", "status": "assessed", "rubric_level": 4.5}]

    # STRONG_HIRE >= 85
    rec_strong = EvaluationScoringService.determine_recommendation(
        overall_score=90.0,
        competency_scores=assessed_comps,
    )
    assert rec_strong == HiringRecommendation.STRONG_HIRE

    # HIRE 70 - 84.9
    rec_hire = EvaluationScoringService.determine_recommendation(
        overall_score=78.0,
        competency_scores=assessed_comps,
    )
    assert rec_hire == HiringRecommendation.HIRE

    # LEAN_HIRE 55 - 69.9
    rec_lean_hire = EvaluationScoringService.determine_recommendation(
        overall_score=60.0,
        competency_scores=assessed_comps,
    )
    assert rec_lean_hire == HiringRecommendation.LEAN_HIRE

    # LEAN_NO_HIRE 40 - 54.9
    rec_lean_no = EvaluationScoringService.determine_recommendation(
        overall_score=45.0,
        competency_scores=assessed_comps,
    )
    assert rec_lean_no == HiringRecommendation.LEAN_NO_HIRE

    # NO_HIRE < 40
    rec_no = EvaluationScoringService.determine_recommendation(
        overall_score=35.0,
        competency_scores=assessed_comps,
    )
    assert rec_no == HiringRecommendation.NO_HIRE


def test_determine_recommendation_insufficient_evidence():
    rec_empty = EvaluationScoringService.determine_recommendation(
        overall_score=0.0,
        competency_scores=[],
    )
    assert rec_empty == HiringRecommendation.INSUFFICIENT_EVIDENCE

    # Required competency not assessed
    rec_req = EvaluationScoringService.determine_recommendation(
        overall_score=85.0,
        competency_scores=[
            {"name": "Core Coding", "is_required": True, "status": "insufficient_evidence", "rubric_level": 1.0}
        ],
    )
    assert rec_req == HiringRecommendation.INSUFFICIENT_EVIDENCE


def test_critical_contradiction_downgrade():
    assessed_comps = [{"name": "C1", "status": "assessed", "rubric_level": 5.0}]
    rec_downgraded = EvaluationScoringService.determine_recommendation(
        overall_score=95.0,
        competency_scores=assessed_comps,
        has_critical_contradiction=True,
    )
    assert rec_downgraded == HiringRecommendation.LEAN_HIRE


def test_verify_score_reproducibility():
    score_inputs = {
        "competency_rubric_levels": {
            "Algorithms": 5.0, # 100.0 * 2 = 200
            "Design": 3.0,     # 50.0 * 1 = 50
        },
        "competency_weights": {
            "Algorithms": 2.0,
            "Design": 1.0,
        },
    }
    # Expected overall = (200 + 50) / 3 = 83.33
    is_valid = EvaluationScoringService.verify_score_reproducibility(
        score_input_data=score_inputs,
        expected_score=83.33,
        expected_recommendation="HIRE",
    )
    assert is_valid is True

    # Tampered score test
    is_tampered = EvaluationScoringService.verify_score_reproducibility(
        score_input_data=score_inputs,
        expected_score=99.0,
        expected_recommendation="STRONG_HIRE",
    )
    assert is_tampered is False
