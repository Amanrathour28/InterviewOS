"""
Question Planning & Coverage Matrix Service — Phase 13.

Builds evidence-grounded question plans with difficulty progression:
  Warm-up -> Fundamental -> Practical -> Deep Dive -> Verification
Integrates with the existing Question Bank and computes the Coverage Matrix.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import (
    JobRequirement,
    QuestionPlan,
    QuestionPlanItem,
    QuestionPlanStatus,
    ResumeClaim,
)
from app.models.interview import (
    Interview,
    InterviewRound,
    InterviewRoundQuestion,
    Question,
    QuestionDifficulty,
)
from app.services.skill_taxonomy import normalize_skill

logger = logging.getLogger("interviewos.question_planning_service")


class QuestionPlanningService:
    """Manages question plans, difficulty progression, and requirement coverage matrices."""

    async def compute_coverage_matrix(
        self,
        job_requirements: List[Dict[str, Any]],
        candidate_skills: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        plan_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculates the requirement coverage matrix:
        [Job Requirement] | [Candidate Evidence] | [Interview Question Coverage] | [Status]
        """
        matrix: List[Dict[str, Any]] = []
        covered_count = 0
        needs_verification_count = 0

        # Build candidate skill and claim lookup
        cand_skill_map = {}
        for s in candidate_skills:
            name = s.get("name") or s.get("skill") or ""
            canon, _ = normalize_skill(name)
            cand_skill_map[canon] = s

        claim_map = {}
        for c in claims:
            txt = c.get("claim", "")
            for s_name in cand_skill_map.keys():
                if s_name.lower() in txt.lower():
                    claim_map[s_name] = c

        # Build question coverage map by competency / skill
        plan_cov_map = {}
        for idx, item in enumerate(plan_items):
            comp = item.get("competency", "")
            canon, _ = normalize_skill(comp)
            q_ref = f"Q{item.get('sequence', idx + 1)}: {item.get('title')}"
            if canon not in plan_cov_map:
                plan_cov_map[canon] = []
            plan_cov_map[canon].append(q_ref)

        for req in job_requirements:
            r_skill = req.get("canonical_skill") or req.get("skill") or ""
            r_canon, _ = normalize_skill(r_skill)
            r_type = req.get("requirement_type", "required")

            # Determine Candidate Evidence Level
            if r_canon in claim_map:
                evidence_level = "Claim Grounded"
                evidence_desc = claim_map[r_canon].get("claim")
            elif r_canon in cand_skill_map:
                evidence_level = "Strong" if cand_skill_map[r_canon].get("proficiency") == "expert" else "Moderate"
                evidence_desc = f"Listed in skills ({cand_skill_map[r_canon].get('proficiency', 'proficient')})"
            else:
                evidence_level = "None / Gap"
                evidence_desc = "Not stated in resume"

            # Determine Question Coverage
            questions_covering = plan_cov_map.get(r_canon, [])
            if questions_covering:
                coverage_str = ", ".join(questions_covering)
                if evidence_level in ("Claim Grounded", "None / Gap"):
                    status_str = "Needs Verification"
                    needs_verification_count += 1
                else:
                    status_str = "Covered"
                    covered_count += 1
            else:
                coverage_str = "Not in plan"
                status_str = "Uncovered" if r_type == "required" else "Optional"

            matrix.append({
                "job_requirement": r_skill,
                "canonical_skill": r_canon,
                "requirement_type": r_type,
                "candidate_evidence_level": evidence_level,
                "evidence_description": evidence_desc,
                "interview_coverage": coverage_str,
                "status": status_str,
            })

        total_reqs = len(job_requirements)
        return {
            "total_requirements": total_reqs,
            "covered_count": covered_count,
            "needs_verification_count": needs_verification_count,
            "coverage_percentage": round((covered_count / max(1, total_reqs)) * 100, 1),
            "matrix": matrix,
        }

    async def match_existing_questions(
        self,
        workspace_id: uuid.UUID,
        competency: str,
        difficulty: str,
        db: AsyncSession,
    ) -> List[Question]:
        """Finds relevant questions from the Question Bank matching the target competency."""
        canon, _ = normalize_skill(competency)
        stmt = (
            select(Question)
            .where(
                (Question.workspace_id == workspace_id) | (Question.workspace_id.is_(None)),
                Question.is_deleted.is_(False),
            )
            .limit(10)
        )
        res = await db.execute(stmt)
        all_q = res.scalars().all()

        matched = []
        for q in all_q:
            skills = [normalize_skill(s)[0] for s in (q.skills or [])]
            if canon in skills or canon.lower() in q.title.lower() or canon.lower() in q.prompt.lower():
                matched.append(q)

        return matched


question_planning_service = QuestionPlanningService()
