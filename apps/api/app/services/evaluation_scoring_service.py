"""
Evaluation Scoring Service — Phase 15.

Provides 100% deterministic, mathematically reproducible score calculations.
The AI may determine qualitative rubric levels (1 to 5), but the final numerical
score and hiring recommendation are strictly computed by deterministic formulas.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models.evaluation import HiringRecommendation

logger = logging.getLogger("interviewos.api.evaluation_scoring")


class EvaluationScoringService:
    """
    Deterministic scoring engine calculating:
    - Competency scores (0.0 to 100.0) from rubric levels (1.0 to 5.0)
    - Weighted overall interview score (0.0 to 100.0)
    - Overall rubric level average (1.0 to 5.0)
    - Hiring recommendations based on policy thresholds & missing evidence gates
    """

    # Standard Recommendation Policy Thresholds
    STRONG_HIRE_THRESHOLD = 85.0
    HIRE_THRESHOLD = 70.0
    LEAN_HIRE_THRESHOLD = 55.0
    LEAN_NO_HIRE_THRESHOLD = 40.0

    @classmethod
    def rubric_level_to_score(cls, rubric_level: float) -> float:
        """
        Converts a 1.0–5.0 rubric level into a 0.0–100.0 numerical score.
        Formula: ((level - 1.0) / 4.0) * 100.0
        1.0 -> 0.0
        2.0 -> 25.0
        3.0 -> 50.0
        4.0 -> 75.0
        5.0 -> 100.0
        """
        clamped_level = max(1.0, min(5.0, float(rubric_level)))
        return round(((clamped_level - 1.0) / 4.0) * 100.0, 2)

    @classmethod
    def score_to_rubric_level(cls, score: float) -> float:
        """
        Converts a 0.0–100.0 score back to 1.0–5.0 rubric level.
        Formula: 1.0 + (score / 100.0) * 4.0
        """
        clamped_score = max(0.0, min(100.0, float(score)))
        return round(1.0 + (clamped_score / 100.0) * 4.0, 2)

    @classmethod
    def calculate_overall_score(
        cls,
        competency_scores: List[Dict[str, Any]],
    ) -> Tuple[float, float, float]:
        """
        Calculates overall weighted score, overall rubric level, and average confidence.
        
        Args:
            competency_scores: List of dicts with:
                - rubric_level: float (1.0 to 5.0)
                - weight: float (e.g. 1.0, 1.5, 2.0)
                - confidence: float (0.0 to 1.0)
                - status: str ('assessed', 'not_assessed', 'insufficient_evidence')
        
        Returns:
            Tuple[overall_score_0_100, overall_rubric_1_5, average_confidence_0_1]
        """
        assessed = [c for c in competency_scores if c.get("status") == "assessed"]
        
        if not assessed:
            return 0.0, 0.0, 0.0

        total_weighted_score = 0.0
        total_weighted_rubric = 0.0
        total_weight = 0.0
        total_confidence = 0.0

        for comp in assessed:
            level = float(comp.get("rubric_level", 1.0))
            weight = max(0.1, float(comp.get("weight", 1.0)))
            conf = float(comp.get("confidence", 1.0))

            comp_score = cls.rubric_level_to_score(level)
            total_weighted_score += comp_score * weight
            total_weighted_rubric += level * weight
            total_weight += weight
            total_confidence += conf

        if total_weight <= 0:
            return 0.0, 0.0, 0.0

        overall_score = round(total_weighted_score / total_weight, 2)
        overall_rubric = round(total_weighted_rubric / total_weight, 2)
        avg_confidence = round(total_confidence / len(assessed), 2)

        return overall_score, overall_rubric, avg_confidence

    @classmethod
    def determine_recommendation(
        cls,
        overall_score: float,
        competency_scores: List[Dict[str, Any]],
        has_critical_contradiction: bool = False,
    ) -> HiringRecommendation:
        """
        Evaluates hiring recommendation using policy thresholds and safety gates.
        
        Safety Gates:
        1. If required competencies are 'not_assessed' or 'insufficient_evidence' -> INSUFFICIENT_EVIDENCE
        2. If critical contradiction exists -> downgraded
        3. Standard score threshold evaluation
        """
        # Gate 1: Check required competencies or overall assessment validity
        assessed = [c for c in competency_scores if c.get("status") == "assessed"]
        if not assessed or len(assessed) < max(1, len(competency_scores) // 2):
            return HiringRecommendation.INSUFFICIENT_EVIDENCE

        # Check average confidence
        total_conf = sum(float(c.get("confidence", 1.0)) for c in assessed)
        avg_conf = total_conf / len(assessed)
        if avg_conf < 0.40:
            return HiringRecommendation.INSUFFICIENT_EVIDENCE

        # Check for required competencies that failed to be assessed
        for comp in competency_scores:
            if comp.get("is_required", False) and comp.get("status") != "assessed":
                return HiringRecommendation.INSUFFICIENT_EVIDENCE

        # Gate 2: Critical contradictions gate
        if has_critical_contradiction:
            if overall_score >= cls.STRONG_HIRE_THRESHOLD:
                return HiringRecommendation.LEAN_HIRE
            return HiringRecommendation.NO_HIRE

        # Gate 3: Policy Thresholds
        if overall_score >= cls.STRONG_HIRE_THRESHOLD:
            return HiringRecommendation.STRONG_HIRE
        elif overall_score >= cls.HIRE_THRESHOLD:
            return HiringRecommendation.HIRE
        elif overall_score >= cls.LEAN_HIRE_THRESHOLD:
            return HiringRecommendation.LEAN_HIRE
        elif overall_score >= cls.LEAN_NO_HIRE_THRESHOLD:
            return HiringRecommendation.LEAN_NO_HIRE
        else:
            return HiringRecommendation.NO_HIRE

    @classmethod
    def verify_score_reproducibility(
        cls,
        score_input_data: Dict[str, Any],
        expected_score: float,
        expected_recommendation: str,
    ) -> bool:
        """
        Recalculates scores solely from persisted inputs and compares with recorded evaluation.
        Returns True if perfectly matches.
        """
        weights = score_input_data.get("competency_weights", {})
        levels = score_input_data.get("competency_rubric_levels", {})

        items = []
        for name, level in levels.items():
            w = weights.get(name, 1.0)
            items.append({
                "rubric_level": level,
                "weight": w,
                "confidence": 1.0,
                "status": "assessed",
            })

        recalc_score, _, _ = cls.calculate_overall_score(items)
        recalc_rec = cls.determine_recommendation(recalc_score, items)

        score_match = abs(recalc_score - expected_score) < 0.05
        rec_match = (
            str(recalc_rec.value).lower() == str(expected_recommendation).lower()
            or (hasattr(expected_recommendation, "value") and recalc_rec.value == expected_recommendation.value)
        )

        return score_match and rec_match


evaluation_scoring_service = EvaluationScoringService()
