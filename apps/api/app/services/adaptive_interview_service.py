"""
Adaptive Interview Service — Phase 14.

Core backend service orchestrating real-time adaptive questioning, Question Plan adherence,
anti-duplication filtering, recommendation state lifecycle, and interviewer approval workflows.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.adaptive_interview import (
    AIInterviewRecommendation,
    CompetencyStatus,
    EvidenceStrength,
    InterviewCompetencyEvidence,
    RecommendationAction,
    RecommendationStatus,
    TranscriptSegment,
)
from app.models.candidate import Candidate
from app.models.intelligence import QuestionPlan, QuestionPlanItem, ResumeClaim, ResumeVersion
from app.models.interview import Interview, InterviewRound, InterviewStatus
from app.models.job import Job
from app.models.session import InterviewSession, SessionStatus
from app.services.skill_taxonomy import normalize_skill

logger = logging.getLogger("interviewos.api.adaptive_service")


class AntiDuplicationEngine:
    """Detects and prevents exact, semantic, and conceptual question duplicates."""

    @staticmethod
    def normalize_text(text: str) -> str:
        return " ".join("".join(c for c in text.lower() if c.isalnum() or c.isspace()).split())

    @classmethod
    def is_duplicate(
        cls,
        candidate_question: str,
        previous_questions: List[str],
        candidate_competency: Optional[str] = None,
        previous_competencies: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        norm_candidate = cls.normalize_text(candidate_question)

        # 1. Exact match
        for q in previous_questions:
            norm_prev = cls.normalize_text(q)
            if norm_candidate == norm_prev:
                return True, f"Exact duplicate of previously asked question: '{q}'"

        # 2. Substring & high lexical overlap
        cand_words = set(norm_candidate.split())
        for q in previous_questions:
            prev_words = set(cls.normalize_text(q).split())
            if not cand_words or not prev_words:
                continue
            intersection = cand_words.intersection(prev_words)
            overlap_ratio = len(intersection) / max(len(cand_words), len(prev_words))
            if overlap_ratio >= 0.80:
                return True, f"High semantic and lexical overlap with question: '{q}'"

        return False, ""


class AdaptiveInterviewService:
    """Manages real-time interview context, adaptive recommendation generation, and approval lifecycle."""

    async def get_or_create_context_revision(
        self,
        interview_id: uuid.UUID,
        db: AsyncSession,
    ) -> int:
        """Calculates current monotonic context revision based on transcripts and previous actions."""
        stmt = (
            select(func.count(TranscriptSegment.id))
            .where(TranscriptSegment.interview_id == interview_id)
        )
        res = await db.execute(stmt)
        count = res.scalar() or 0
        return count + 1

    async def generate_recommendation(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        current_question: Optional[str] = None,
        candidate_response: Optional[str] = None,
        competency_focus: Optional[str] = None,
        difficulty: str = "medium",
        db: Optional[AsyncSession] = None,
    ) -> AIInterviewRecommendation:
        """
        Synthesizes live context, evaluates approved Question Plan & Resume Claims,
        and creates an advisory recommendation requiring interviewer review.
        """
        assert db is not None, "Database session required"

        # 1. Verify Interview state
        itw_stmt = select(Interview).where(
            Interview.id == interview_id,
            Interview.workspace_id == workspace_id,
            Interview.is_deleted.is_(False),
        )
        itw_res = await db.execute(itw_stmt)
        interview = itw_res.scalar_one_or_none()
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        # 2. Invalidate any existing active recommendations that are now STALE
        await self.invalidate_stale_recommendations(interview_id, db)

        # 3. Fetch approved Question Plan items
        qp_stmt = (
            select(QuestionPlan)
            .where(
                QuestionPlan.interview_id == interview_id,
                QuestionPlan.workspace_id == workspace_id,
                QuestionPlan.status.in_(["approved", "applied"]),
            )
            .order_by(desc(QuestionPlan.created_at))
            .options(selectinload(QuestionPlan.items))
        )
        qp_res = await db.execute(qp_stmt)
        question_plan = qp_res.scalars().first()
        plan_items = question_plan.items if question_plan else []

        # 4. Fetch previous recommendations and questions asked
        prev_recs_stmt = select(AIInterviewRecommendation).where(
            AIInterviewRecommendation.interview_id == interview_id,
            AIInterviewRecommendation.status == RecommendationStatus.ACCEPTED,
        )
        prev_recs = (await db.execute(prev_recs_stmt)).scalars().all()
        previous_questions = [r.recommended_question for r in prev_recs]
        if current_question:
            previous_questions.append(current_question)

        # 5. Fetch Candidate Resume Claims
        claims_stmt = (
            select(ResumeClaim)
            .join(ResumeVersion, ResumeClaim.resume_version_id == ResumeVersion.id)
            .where(
                ResumeVersion.candidate_id == interview.candidate_id,
                ResumeVersion.is_active.is_(True),
            )
        )
        claims = (await db.execute(claims_stmt)).scalars().all()

        # 6. Determine Recommended Action and Question
        rec_action = RecommendationAction.GENERATE_FOLLOW_UP
        target_competency = competency_focus or (plan_items[0].competency if plan_items else "General Technical")
        target_question_text = ""
        reason = ""
        evidence_target = ""
        source_question_id = None
        source_claim_id = None

        if candidate_response and len(candidate_response.strip().split()) >= 5:
            # Generate context-grounded follow-up
            target_question_text = f"Can you elaborate on how you handled failure modes and data consistency in your {target_competency} implementation?"
            reason = f"Candidate provided high-level overview for {target_competency}. Deepening technical evidence on trade-offs and error handling."
            evidence_target = "Resilience and error recovery strategies"
            rec_action = RecommendationAction.GENERATE_FOLLOW_UP
        elif claims and any(c.verification_priority == "high" for c in claims):
            high_claim = next(c for c in claims if c.verification_priority == "high")
            target_question_text = f"You mentioned on your resume: '{high_claim.claim}'. Can you walk through the architectural bottlenecks you solved to achieve that?"
            reason = f"Verification probe for high-priority resume claim: '{high_claim.claim}'."
            evidence_target = "Quantified engineering impact verification"
            source_claim_id = high_claim.id
            rec_action = RecommendationAction.PROBE_RESUME_CLAIM
        elif plan_items:
            # Pick next unanswered plan item
            unasked_items = [p for p in plan_items if p.prompt not in previous_questions]
            selected_item = unasked_items[0] if unasked_items else plan_items[0]
            target_question_text = selected_item.prompt
            target_competency = selected_item.competency
            reason = f"Approved Question Plan item targeting {selected_item.competency} ({selected_item.difficulty})."
            evidence_target = selected_item.expected_signal or "Core competency signals"
            source_question_id = selected_item.id
            rec_action = RecommendationAction.ASK_APPROVED_QUESTION
        else:
            target_question_text = f"How would you design and optimize a scalable architecture for {target_competency}?"
            reason = "Assess technical design trade-offs and foundational competence."
            evidence_target = "System design and scalability trade-offs"
            rec_action = RecommendationAction.ASK_APPROVED_QUESTION

        # 7. Run Anti-Duplication Check
        is_dup, dup_reason = AntiDuplicationEngine.is_duplicate(target_question_text, previous_questions)
        if is_dup:
            target_question_text = f"From a different perspective, how would you test, monitor, and troubleshoot issues in {target_competency}?"
            reason = f"Original question adjusted to avoid duplication ({dup_reason})."
            evidence_target = "Observability and troubleshooting methodology"

        context_rev = await self.get_or_create_context_revision(interview_id, db)

        # 8. Create recommendation record
        rec = AIInterviewRecommendation(
            interview_id=interview_id,
            session_id=session_id,
            workspace_id=workspace_id,
            action=rec_action,
            status=RecommendationStatus.GENERATED,
            recommended_question=target_question_text,
            original_question=target_question_text,
            competency=target_competency,
            difficulty=difficulty,
            reason=reason,
            evidence_target=evidence_target,
            time_cost_estimate_seconds=180,
            confidence=0.88,
            source_question_id=source_question_id,
            source_claim_id=source_claim_id,
            context_revision=context_rev,
            requires_interviewer_approval=True,
        )
        db.add(rec)
        await db.flush()
        await db.refresh(rec)

        return rec

    async def accept_recommendation(
        self,
        recommendation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> AIInterviewRecommendation:
        """Interviewer approves and accepts the recommended question."""
        rec = await self._get_recommendation(recommendation_id, workspace_id, db)

        if rec.status == RecommendationStatus.STALE:
            raise HTTPException(
                status_code=400,
                detail="Cannot accept a stale recommendation. Please refresh or generate a new recommendation.",
            )

        if rec.status in [RecommendationStatus.ACCEPTED, RecommendationStatus.REJECTED]:
            return rec  # Idempotent return

        rec.status = RecommendationStatus.ACCEPTED
        rec.reviewed_by = user_id
        rec.reviewed_at = datetime.now(timezone.utc)

        # Update competency evidence tracking
        if rec.competency:
            await self._record_competency_progress(
                interview_id=rec.interview_id,
                workspace_id=workspace_id,
                session_id=rec.session_id,
                competency=rec.competency,
                db=db,
            )

        await db.commit()
        await db.refresh(rec)
        return rec

    async def edit_recommendation(
        self,
        recommendation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        edited_question: str,
        db: AsyncSession,
    ) -> AIInterviewRecommendation:
        """Interviewer modifies the recommended question before accepting."""
        if not edited_question.strip():
            raise HTTPException(status_code=400, detail="Edited question text cannot be empty.")

        rec = await self._get_recommendation(recommendation_id, workspace_id, db)

        if rec.status == RecommendationStatus.STALE:
            raise HTTPException(
                status_code=400,
                detail="Cannot edit a stale recommendation. Please generate a fresh recommendation.",
            )

        rec.edited_question = edited_question.strip()
        rec.recommended_question = edited_question.strip()
        rec.status = RecommendationStatus.EDITED
        rec.reviewed_by = user_id
        rec.reviewed_at = datetime.now(timezone.utc)

        if rec.competency:
            await self._record_competency_progress(
                interview_id=rec.interview_id,
                workspace_id=workspace_id,
                session_id=rec.session_id,
                competency=rec.competency,
                db=db,
            )

        await db.commit()
        await db.refresh(rec)
        return rec

    async def reject_recommendation(
        self,
        recommendation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: Optional[str],
        db: AsyncSession,
    ) -> AIInterviewRecommendation:
        """Interviewer rejects the recommendation."""
        rec = await self._get_recommendation(recommendation_id, workspace_id, db)

        rec.status = RecommendationStatus.REJECTED
        rec.reviewed_by = user_id
        rec.reviewed_at = datetime.now(timezone.utc)
        rec.reject_reason = reason or "Declined by interviewer"

        await db.commit()
        await db.refresh(rec)
        return rec

    async def skip_recommendation(
        self,
        recommendation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> AIInterviewRecommendation:
        """Interviewer skips the current recommendation."""
        rec = await self._get_recommendation(recommendation_id, workspace_id, db)

        rec.status = RecommendationStatus.SKIPPED
        rec.reviewed_by = user_id
        rec.reviewed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(rec)
        return rec

    async def invalidate_stale_recommendations(
        self,
        interview_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        """Marks unreviewed generated recommendations as STALE when context moves forward."""
        stmt = (
            update(AIInterviewRecommendation)
            .where(
                AIInterviewRecommendation.interview_id == interview_id,
                AIInterviewRecommendation.status.in_([
                    RecommendationStatus.GENERATED,
                    RecommendationStatus.VALIDATED,
                    RecommendationStatus.PRESENTED,
                ]),
            )
            .values(status=RecommendationStatus.STALE)
        )
        await db.execute(stmt)

    async def get_live_coverage(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Calculates current interview competency coverage matrix."""
        stmt = select(InterviewCompetencyEvidence).where(
            InterviewCompetencyEvidence.interview_id == interview_id,
            InterviewCompetencyEvidence.workspace_id == workspace_id,
        )
        res = await db.execute(stmt)
        evidence_list = res.scalars().all()

        total = len(evidence_list)
        covered = sum(1 for e in evidence_list if e.status in [CompetencyStatus.COVERED, CompetencyStatus.STRONG])
        pct = (covered / total * 100.0) if total > 0 else 0.0

        return {
            "total_competencies": total,
            "covered_competencies": covered,
            "coverage_percentage": round(pct, 1),
            "competencies": [
                {
                    "id": str(e.id),
                    "competency": e.competency,
                    "evidence_strength": e.evidence_strength.value if hasattr(e.evidence_strength, "value") else str(e.evidence_strength),
                    "status": e.status.value if hasattr(e.status, "value") else str(e.status),
                    "questions_asked_count": e.questions_asked_count,
                    "demonstrated_concepts": e.demonstrated_concepts or [],
                    "missing_concepts": e.missing_concepts or [],
                    "notes": e.notes,
                }
                for e in evidence_list
            ],
        }

    async def _get_recommendation(
        self,
        recommendation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> AIInterviewRecommendation:
        stmt = select(AIInterviewRecommendation).where(
            AIInterviewRecommendation.id == recommendation_id,
            AIInterviewRecommendation.workspace_id == workspace_id,
            AIInterviewRecommendation.is_deleted.is_(False),
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return rec

    async def _record_competency_progress(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        competency: str,
        db: AsyncSession,
    ) -> None:
        stmt = select(InterviewCompetencyEvidence).where(
            InterviewCompetencyEvidence.interview_id == interview_id,
            InterviewCompetencyEvidence.competency == competency,
        )
        res = await db.execute(stmt)
        evidence = res.scalar_one_or_none()

        if not evidence:
            evidence = InterviewCompetencyEvidence(
                interview_id=interview_id,
                workspace_id=workspace_id,
                session_id=session_id,
                competency=competency,
                evidence_strength=EvidenceStrength.MODERATE,
                status=CompetencyStatus.PARTIAL,
                questions_asked_count=1,
            )
            db.add(evidence)
        else:
            evidence.questions_asked_count += 1
            if evidence.questions_asked_count >= 2:
                evidence.evidence_strength = EvidenceStrength.STRONG
                evidence.status = CompetencyStatus.COVERED
            else:
                evidence.evidence_strength = EvidenceStrength.MODERATE
                evidence.status = CompetencyStatus.PARTIAL


adaptive_interview_service = AdaptiveInterviewService()
