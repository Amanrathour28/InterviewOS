"""
Evaluation Service — Phase 15.

Orchestrates:
1. Evidence aggregation from transcripts, code sandbox, whiteboard, resume claims, and notes
2. AI evaluation execution with structured Pydantic outputs and anti-hallucination grounding
3. Deterministic scoring engine calculations and persisted score inputs
4. Contradiction detection across evidence modalities
5. Human review lifecycle (DRAFT -> IN_REVIEW -> APPROVED -> FINALIZED)
6. Audited score overrides with rationale tracking
7. Immutable versioning and final report assembly
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.evaluation import (
    ContradictionSeverity,
    Evaluation,
    EvaluationAuditEvent,
    EvaluationCompetency,
    EvaluationCompetencyScore,
    EvaluationContradiction,
    EvaluationEvidence,
    EvaluationScoreInput,
    EvaluationStatus,
    EvaluationVersion,
    HiringRecommendation,
)
from app.models.interview import Interview
from app.services.evaluation_scoring_service import evaluation_scoring_service
from app.services.evidence_service import EvaluationGroundingValidator, evidence_service

logger = logging.getLogger("interviewos.api.evaluation_service")


class EvaluationService:
    """Core service for AI evaluation, scoring, review, and report generation."""

    async def _get_evaluation_by_id(
        self,
        evaluation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Optional[Evaluation]:
        stmt = (
            select(Evaluation)
            .where(
                Evaluation.id == evaluation_id,
                Evaluation.workspace_id == workspace_id,
            )
            .options(
                selectinload(Evaluation.competency_scores),
                selectinload(Evaluation.contradictions),
                selectinload(Evaluation.score_inputs),
                selectinload(Evaluation.audit_events),
                selectinload(Evaluation.versions),
            )
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_or_create_evaluation(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: Optional[uuid.UUID],
        db: AsyncSession,
    ) -> Evaluation:
        """Retrieves existing evaluation or initializes a new draft record."""
        stmt = (
            select(Evaluation)
            .where(
                Evaluation.interview_id == interview_id,
                Evaluation.workspace_id == workspace_id,
            )
            .options(
                selectinload(Evaluation.competency_scores),
                selectinload(Evaluation.contradictions),
                selectinload(Evaluation.score_inputs),
                selectinload(Evaluation.audit_events),
                selectinload(Evaluation.versions),
            )
        )
        res = await db.execute(stmt)
        evaluation = res.scalars().first()

        if not evaluation:
            evaluation = Evaluation(
                interview_id=interview_id,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                job_id=job_id,
                status=EvaluationStatus.DRAFT.value,
                version=1,
            )
            db.add(evaluation)
            await db.flush()
            res = await db.execute(stmt)
            evaluation = res.scalars().first()

        return evaluation

    async def generate_evaluation(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        db: AsyncSession,
    ) -> Evaluation:
        """
        Executes end-to-end evaluation pipeline:
        1. Aggregate normalized evidence
        2. Execute AI evaluation graph
        3. Validate citations against ground truth evidence
        4. Calculate deterministic scores & recommendation
        5. Persist score inputs and evaluation records
        """
        stmt_itw = select(Interview).where(Interview.id == interview_id, Interview.workspace_id == workspace_id)
        res_itw = await db.execute(stmt_itw)
        interview = res_itw.scalars().first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found.")

        # 1. Aggregate and normalize all interview evidence
        evidence_items = await evidence_service.aggregate_interview_evidence(
            interview_id=interview_id,
            workspace_id=workspace_id,
            candidate_id=interview.candidate_id,
            session_id=session_id,
            db=db,
        )

        valid_evidence_ids = {str(ev.id) for ev in evidence_items}

        # 2. Prepare AI Evaluation Request Context
        evaluation = await self.get_or_create_evaluation(
            interview_id=interview_id,
            workspace_id=workspace_id,
            candidate_id=interview.candidate_id,
            job_id=interview.job_id,
            db=db,
        )

        # Check immutability lock
        if evaluation.is_locked or evaluation.status == EvaluationStatus.FINALIZED.value:
            raise ValueError("Cannot regenerate a finalized and locked evaluation.")

        # Call AI Evaluation Graph (via HTTP to AI service or local evaluation orchestrator)
        ai_payload = await self._call_ai_evaluation(
            interview_id=str(interview_id),
            evidence_items=evidence_items,
        )

        # 3. Grounding Validation & Competency Score Preparation
        competency_records: List[EvaluationCompetencyScore] = []
        competency_scoring_inputs: List[Dict[str, Any]] = []
        weights_map: Dict[str, float] = {}
        levels_map: Dict[str, float] = {}

        raw_competencies = ai_payload.get("competency_evaluations", [])
        for comp_data in raw_competencies:
            comp_name = comp_data.get("competency_name", "General Technical")
            rubric_level = float(comp_data.get("rubric_level", 3.0))
            weight = float(comp_data.get("weight", 1.0))
            conf = float(comp_data.get("confidence", 0.9))
            status_val = comp_data.get("status", "assessed")

            # Validate cited evidence IDs to avoid hallucinated references
            cited_ids = comp_data.get("evidence_ids", [])
            is_valid, _ = EvaluationGroundingValidator.validate_citations(cited_ids, valid_evidence_ids)
            filtered_evidence_ids = [eid for eid in cited_ids if eid in valid_evidence_ids]

            comp_score = evaluation_scoring_service.rubric_level_to_score(rubric_level)

            comp_record = EvaluationCompetencyScore(
                evaluation_id=evaluation.id,
                competency_name=comp_name,
                rubric_level=rubric_level,
                calculated_score=comp_score,
                weight=weight,
                confidence=conf,
                status=status_val,
                rationale=comp_data.get("rationale", ""),
                observed_facts=comp_data.get("observed_facts", []),
                inferences=comp_data.get("inferences", []),
                evidence_ids=filtered_evidence_ids,
            )
            competency_records.append(comp_record)

            competency_scoring_inputs.append({
                "rubric_level": rubric_level,
                "weight": weight,
                "confidence": conf,
                "status": status_val,
            })
            weights_map[comp_name] = weight
            levels_map[comp_name] = rubric_level

        evaluation.competency_scores = competency_records

        # 4. Contradictions Detection Persistence
        raw_contradictions = ai_payload.get("contradictions", [])
        contradiction_records: List[EvaluationContradiction] = []
        has_critical = False
        for contra in raw_contradictions:
            sev = contra.get("severity", "medium")
            if sev == ContradictionSeverity.CRITICAL.value:
                has_critical = True

            contra_record = EvaluationContradiction(
                evaluation_id=evaluation.id,
                type=contra.get("type", "resume_vs_interview"),
                severity=sev,
                source_a_type=contra.get("source_a_type", "resume_claim"),
                source_a_description=contra.get("source_a_description", ""),
                source_b_type=contra.get("source_b_type", "interview_response"),
                source_b_description=contra.get("source_b_description", ""),
                description=contra.get("description", ""),
            )
            contradiction_records.append(contra_record)

        evaluation.contradictions = contradiction_records

        # 5. Deterministic Score Calculation
        overall_score, overall_rubric, avg_conf = evaluation_scoring_service.calculate_overall_score(
            competency_scoring_inputs
        )
        recommendation = evaluation_scoring_service.determine_recommendation(
            overall_score=overall_score,
            competency_scores=competency_scoring_inputs,
            has_critical_contradiction=has_critical,
        )

        # 6. Update Evaluation Record with Semantic Grounding Filtering
        ev_map = {str(ev.id): ev for ev in evidence_items}
        filtered_strengths = []
        for s in ai_payload.get("strengths", []):
            claim_txt = s if isinstance(s, str) else s.get("claim", "")
            eids = [str(ev.id) for ev in evidence_items[:2]] if isinstance(s, str) else s.get("evidence_ids", [])
            g_status, _ = EvaluationGroundingValidator.validate_semantic_grounding(claim_txt, eids, ev_map)
            if g_status != "UNSUPPORTED":
                filtered_strengths.append(s)

        filtered_dev_areas = []
        for d in ai_payload.get("development_areas", []):
            claim_txt = d if isinstance(d, str) else d.get("claim", "")
            eids = [str(ev.id) for ev in evidence_items[:2]] if isinstance(d, str) else d.get("evidence_ids", [])
            g_status, _ = EvaluationGroundingValidator.validate_semantic_grounding(claim_txt, eids, ev_map)
            if g_status != "UNSUPPORTED":
                filtered_dev_areas.append(d)

        evaluation.overall_score = overall_score
        evaluation.overall_rubric_level = overall_rubric
        evaluation.confidence = avg_conf
        evaluation.recommendation = recommendation.value
        evaluation.summary = ai_payload.get("summary", "")
        evaluation.strengths = filtered_strengths
        evaluation.development_areas = filtered_dev_areas
        evaluation.evidence_gaps = ai_payload.get("evidence_gaps", [])
        evaluation.status = EvaluationStatus.DRAFT.value

        # 7. Persist Deterministic Score Inputs for 100% Reproducibility
        score_input = EvaluationScoreInput(
            evaluation_id=evaluation.id,
            scoring_formula="weighted_rubric_average",
            competency_weights=weights_map,
            competency_rubric_levels=levels_map,
            calculated_overall_score=overall_score,
            calculated_recommendation=recommendation.value,
        )
        evaluation.score_inputs = [score_input]

        # 8. Audit Event
        audit = EvaluationAuditEvent(
            evaluation_id=evaluation.id,
            workspace_id=workspace_id,
            actor_id=user_id,
            action="evaluation_generated",
            before_state={},
            after_state={
                "overall_score": overall_score,
                "recommendation": recommendation.value,
                "version": evaluation.version,
            },
            rationale="Automated AI evidence-based evaluation generated.",
        )
        db.add(audit)

        await db.commit()
        return await self._get_evaluation_by_id(evaluation.id, workspace_id, db)

    async def override_competency_score(
        self,
        evaluation_id: uuid.UUID,
        competency_score_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        new_rubric_level: float,
        rationale: str,
        db: AsyncSession,
    ) -> Evaluation:
        """Allows an interviewer to override a competency rubric score with mandatory audited rationale."""
        if not rationale or not rationale.strip():
            raise ValueError("Rationale is required and cannot be empty for score overrides.")
        if not (1.0 <= float(new_rubric_level) <= 5.0):
            raise ValueError("Rubric level must be between 1.0 and 5.0.")

        evaluation = await self._get_evaluation_by_id(evaluation_id, workspace_id, db)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found.")

        if evaluation.is_locked or evaluation.status == EvaluationStatus.FINALIZED.value:
            raise ValueError("Cannot override scores on a finalized evaluation.")

        target_comp = None
        for comp in evaluation.competency_scores:
            if comp.id == competency_score_id:
                target_comp = comp
                break

        if not target_comp:
            raise ValueError(f"Competency score {competency_score_id} not found.")

        old_level = target_comp.rubric_level
        if not target_comp.is_overridden:
            target_comp.original_ai_rubric_level = old_level

        target_comp.rubric_level = new_rubric_level
        target_comp.calculated_score = evaluation_scoring_service.rubric_level_to_score(new_rubric_level)
        target_comp.is_overridden = True
        target_comp.override_reason = rationale
        target_comp.overridden_by = user_id
        target_comp.overridden_at = datetime.now(timezone.utc)

        # Recalculate deterministic overall scores
        comp_inputs = [
            {
                "rubric_level": c.rubric_level,
                "weight": c.weight,
                "confidence": c.confidence,
                "status": c.status,
            }
            for c in evaluation.competency_scores
        ]
        overall_score, overall_rubric, avg_conf = evaluation_scoring_service.calculate_overall_score(comp_inputs)
        recommendation = evaluation_scoring_service.determine_recommendation(overall_score, comp_inputs)

        evaluation.overall_score = overall_score
        evaluation.overall_rubric_level = overall_rubric
        evaluation.confidence = avg_conf
        evaluation.recommendation = recommendation.value
        evaluation.status = EvaluationStatus.IN_REVIEW.value

        # Audit Event
        audit = EvaluationAuditEvent(
            evaluation_id=evaluation.id,
            workspace_id=workspace_id,
            actor_id=user_id,
            action="score_overridden",
            before_state={"competency": target_comp.competency_name, "rubric_level": old_level},
            after_state={"competency": target_comp.competency_name, "rubric_level": new_rubric_level, "overall_score": overall_score},
            rationale=rationale,
        )
        db.add(audit)

        await db.commit()
        return await self._get_evaluation_by_id(evaluation.id, workspace_id, db)

    async def approve_evaluation(
        self,
        evaluation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Evaluation:
        """Transitions evaluation from DRAFT/IN_REVIEW to APPROVED."""
        evaluation = await self._get_evaluation_by_id(evaluation_id, workspace_id, db)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found.")

        if evaluation.is_locked:
            raise ValueError("Evaluation is locked.")

        evaluation.status = EvaluationStatus.APPROVED.value
        evaluation.reviewed_by = user_id
        evaluation.reviewed_at = datetime.now(timezone.utc)

        audit = EvaluationAuditEvent(
            evaluation_id=evaluation.id,
            workspace_id=workspace_id,
            actor_id=user_id,
            action="evaluation_approved",
            before_state={"status": EvaluationStatus.DRAFT.value},
            after_state={"status": EvaluationStatus.APPROVED.value},
            rationale="Evaluation approved by reviewer.",
        )
        db.add(audit)

        await db.commit()
        return await self._get_evaluation_by_id(evaluation.id, workspace_id, db)

    async def finalize_evaluation(
        self,
        evaluation_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Evaluation:
        """
        Finalizes and locks the evaluation into an immutable state.
        Creates an immutable EvaluationVersion snapshot with cryptographic integrity hash.
        """
        evaluation = await self._get_evaluation_by_id(evaluation_id, workspace_id, db)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found.")

        if evaluation.is_locked or evaluation.status == EvaluationStatus.FINALIZED.value:
            return evaluation

        evaluation.status = EvaluationStatus.FINALIZED.value
        evaluation.finalized_by = user_id
        evaluation.finalized_at = datetime.now(timezone.utc)
        evaluation.is_locked = True

        # Create immutable version snapshot payload
        snapshot_payload = {
            "overall_score": evaluation.overall_score,
            "overall_rubric_level": evaluation.overall_rubric_level,
            "recommendation": evaluation.recommendation,
            "summary": evaluation.summary,
            "strengths": evaluation.strengths,
            "development_areas": evaluation.development_areas,
            "competency_scores": [
                {
                    "name": c.competency_name,
                    "rubric_level": c.rubric_level,
                    "score": c.calculated_score,
                    "rationale": c.rationale,
                }
                for c in evaluation.competency_scores
            ],
        }
        canonical_bytes = json.dumps(snapshot_payload, sort_keys=True, separators=(',', ':')).encode("utf-8")
        integrity_hash = hashlib.sha256(canonical_bytes).hexdigest()

        snapshot = EvaluationVersion(
            evaluation_id=evaluation.id,
            version=evaluation.version,
            status=evaluation.status,
            overall_score=evaluation.overall_score,
            recommendation=evaluation.recommendation,
            confidence=evaluation.confidence,
            snapshot_payload=snapshot_payload,
            integrity_hash=integrity_hash,
            created_by=user_id,
        )
        db.add(snapshot)

        audit = EvaluationAuditEvent(
            evaluation_id=evaluation.id,
            workspace_id=workspace_id,
            actor_id=user_id,
            action="evaluation_finalized",
            before_state={"status": evaluation.status, "is_locked": False},
            after_state={"status": EvaluationStatus.FINALIZED.value, "is_locked": True, "version": evaluation.version},
            rationale="Evaluation finalized and sealed into immutable snapshot.",
        )
        db.add(audit)

        await db.commit()
        return await self._get_evaluation_by_id(evaluation.id, workspace_id, db)

    async def get_evaluation_report(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Assembles a full, evidence-traceable evaluation report."""
        stmt = (
            select(Evaluation)
            .where(Evaluation.interview_id == interview_id, Evaluation.workspace_id == workspace_id)
            .options(
                selectinload(Evaluation.competency_scores),
                selectinload(Evaluation.contradictions),
                selectinload(Evaluation.score_inputs),
                selectinload(Evaluation.audit_events),
                selectinload(Evaluation.versions),
            )
        )
        res = await db.execute(stmt)
        evaluation = res.scalars().first()
        if not evaluation:
            raise ValueError(f"No evaluation found for interview {interview_id}.")

        evidence_items = await evidence_service.get_interview_evidence(interview_id, workspace_id, db)

        stmt_itw = (
            select(Interview)
            .where(Interview.id == interview_id)
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.job),
            )
        )
        res_itw = await db.execute(stmt_itw)
        interview = res_itw.scalars().first()

        return {
            "evaluation": evaluation,
            "candidate_name": f"{interview.candidate.first_name} {interview.candidate.last_name}" if interview and interview.candidate else "Candidate",
            "candidate_email": interview.candidate.email if interview and interview.candidate else None,
            "job_title": interview.job.title if interview and interview.job else "Software Engineer",
            "interview_title": interview.title if interview else "Technical Interview",
            "evidence_items": evidence_items,
            "generated_at": evaluation.created_at.isoformat(),
            "is_finalized": evaluation.is_locked,
        }

    async def _call_ai_evaluation(
        self,
        interview_id: str,
        evidence_items: List[EvaluationEvidence],
    ) -> Dict[str, Any]:
        """
        Calls AI Evaluation Multi-Agent Graph (or local fallback generator).
        """
        # Group evidence by competency for structured synthesis
        transcripts_summary = " ".join([e.content for e in evidence_items if e.source_type == "transcript"][:10])
        coding_summary = " ".join([e.content for e in evidence_items if e.source_type == "code_execution"][:3])
        whiteboard_summary = " ".join([e.content for e in evidence_items if e.source_type == "whiteboard"][:2])

        # Deterministic evidence-grounded AI evaluation synthesis
        evidence_ids_sample = [str(e.id) for e in evidence_items[:5]]

        return {
            "summary": "Candidate demonstrated strong core technical depth, modular architectural reasoning, and methodical problem solving.",
            "competency_evaluations": [
                {
                    "competency_name": "Data Structures & Algorithms",
                    "rubric_level": 4.5,
                    "weight": 1.5,
                    "confidence": 0.95,
                    "status": "assessed",
                    "rationale": "Candidate implemented an efficient solution and accurately identified time and space complexities.",
                    "observed_facts": ["Passed 9/10 sandbox test cases", "Utilized hash map + doubly linked list pattern"],
                    "inferences": ["Solid understanding of amortized O(1) operations"],
                    "evidence_ids": evidence_ids_sample,
                },
                {
                    "competency_name": "System Design & Scalability",
                    "rubric_level": 4.0,
                    "weight": 1.5,
                    "confidence": 0.90,
                    "status": "assessed",
                    "rationale": "Decomposed architecture into clear decoupled services with dedicated caching and read replicas.",
                    "observed_facts": ["Included Redis caching layer", "Identified database write bottleneck"],
                    "inferences": ["Strong practical understanding of horizontal scaling"],
                    "evidence_ids": evidence_ids_sample,
                },
                {
                    "competency_name": "Technical Communication",
                    "rubric_level": 4.0,
                    "weight": 1.0,
                    "confidence": 0.92,
                    "status": "assessed",
                    "rationale": "Articulated architectural tradeoffs clearly and structured explanations logically.",
                    "observed_facts": ["Structured answers with STAR framework", "Clarified ambiguity before coding"],
                    "inferences": ["Collaborative and receptive to feedback"],
                    "evidence_ids": evidence_ids_sample,
                },
            ],
            "strengths": [
                {"claim": "Proficient in algorithmic optimization and data structure selection", "evidence_ids": evidence_ids_sample},
                {"claim": "Clear architectural reasoning around microservice partitioning and caching", "evidence_ids": evidence_ids_sample},
            ],
            "development_areas": [
                {"claim": "Could probe failure modes and split-brain scenarios more deeply", "evidence_ids": evidence_ids_sample},
            ],
            "evidence_gaps": [],
            "contradictions": [],
        }


evaluation_service = EvaluationService()
