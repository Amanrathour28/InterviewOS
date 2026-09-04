"""
Evidence Service & Grounding Validator — Phase 15.

Aggregates, normalizes, and validates interview evidence from:
1. Transcript segments (candidate speech vs interviewer context)
2. Coding submissions & Docker sandbox test results (authoritative)
3. Whiteboard diagrams & component states
4. Resume claims & verification notes
5. Interviewer private notes

Grounding Validator ensures no hallucinated evidence references exist in evaluation claims.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive_interview import TranscriptSegment
from app.models.coding import CodingExecutionResult, CodingSession, CodingSubmission
from app.models.evaluation import EvaluationEvidence, EvidenceSourceType
from app.models.intelligence import ResumeClaim, ResumeProfile
from app.models.session import InterviewerNote
from app.models.whiteboard import Whiteboard, WhiteboardSnapshot

logger = logging.getLogger("interviewos.api.evidence_service")


import re

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "in", "on", "at", "to",
    "for", "with", "by", "about", "against", "between", "into", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "can", "could", "should", "would", "will", "shall", "may", "might",
    "must", "candidate", "demonstrated", "showed", "explained", "stated", "used", "built"
}


class EvaluationGroundingValidator:
    """
    Validates that every claim and citation references an existing, persisted
    EvaluationEvidence record belonging to the interview and workspace,
    and semantically supports the substantive claim.
    """

    @classmethod
    def validate_citations(
        cls,
        evidence_ids: List[str],
        valid_evidence_ids: Set[str],
    ) -> Tuple[bool, List[str]]:
        """
        Verifies that all cited evidence IDs exist within the validated workspace and interview.
        """
        invalid_ids = [eid for eid in evidence_ids if eid not in valid_evidence_ids]
        return len(invalid_ids) == 0, invalid_ids

    @classmethod
    def extract_keywords(cls, text: str) -> Set[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = cleaned.split()
        return {t for t in tokens if len(t) > 2 and t not in STOPWORDS}

    @classmethod
    def validate_semantic_grounding(
        cls,
        claim_text: str,
        evidence_ids: List[str],
        evidence_map: Dict[str, EvaluationEvidence],
    ) -> Tuple[str, str]:
        """
        Validates substantive semantic alignment between claim text and cited evidence content.
        Returns Tuple[status, reason] where status is 'SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED'.
        """
        if not evidence_ids:
            return "UNSUPPORTED", "No evidence cited."

        valid_evs = [evidence_map[eid] for eid in evidence_ids if eid in evidence_map]
        if not valid_evs:
            return "UNSUPPORTED", "Cited evidence IDs do not exist in session evidence."

        claim_kw = cls.extract_keywords(claim_text)
        if not claim_kw:
            return "SUPPORTED", "Generic statement with valid citations."

        combined_content = " ".join([ev.content for ev in valid_evs if ev.content])
        ev_kw = cls.extract_keywords(combined_content)

        matching = claim_kw.intersection(ev_kw)
        overlap = len(matching) / len(claim_kw)

        if overlap >= 0.40:
            return "SUPPORTED", f"Substantive support confirmed ({len(matching)} matching key terms)."
        elif overlap > 0.15:
            return "PARTIALLY_SUPPORTED", f"Partial support confirmed ({len(matching)} matching key terms)."
        else:
            return "UNSUPPORTED", f"Cited evidence does not substantively support claim topics (overlap: {overlap:.1%})."

    @classmethod
    def validate_quote(
        cls,
        quote: str,
        evidence_records: List[EvaluationEvidence],
        min_token_overlap: float = 0.75,
    ) -> Tuple[bool, Optional[str], float]:
        """
        Validates that a quoted candidate statement exists in verified candidate speech evidence.
        Returns: Tuple[is_verified, matching_evidence_id, similarity_score]
        """
        cleaned_quote = " ".join(re.sub(r"[^\w\s]", " ", quote.lower()).split())
        quote_tokens = set(cleaned_quote.split())
        if not quote_tokens:
            return False, None, 0.0

        best_score = 0.0
        best_id = None

        for ev in evidence_records:
            if not ev.is_candidate_evidence:
                continue
            ev_cleaned = " ".join(re.sub(r"[^\w\s]", " ", (ev.content or "").lower()).split())
            if cleaned_quote in ev_cleaned:
                return True, str(ev.id), 1.0

            ev_tokens = set(ev_cleaned.split())
            if ev_tokens:
                common = quote_tokens.intersection(ev_tokens)
                score = len(common) / len(quote_tokens)
                if score > best_score:
                    best_score = score
                    best_id = str(ev.id)

        if best_score >= min_token_overlap and best_id:
            return True, best_id, round(best_score, 3)

        return False, best_id, round(best_score, 3)


class EvidenceService:
    """Collects, persists, and organizes unified interview evidence."""

    async def aggregate_interview_evidence(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        db: AsyncSession,
    ) -> List[EvaluationEvidence]:
        """
        Scans all interview artifacts and creates durable EvaluationEvidence records.
        """
        evidence_records: List[EvaluationEvidence] = []

        # 1. Transcript Segments (Candidate speech = evidence; Interviewer = observation/context)
        stmt_transcripts = (
            select(TranscriptSegment)
            .where(
                TranscriptSegment.interview_id == interview_id,
                TranscriptSegment.workspace_id == workspace_id,
            )
            .order_by(TranscriptSegment.start_time_seconds.asc())
        )
        res_transcripts = await db.execute(stmt_transcripts)
        transcripts = res_transcripts.scalars().all()

        for seg in transcripts:
            is_cand = seg.speaker_role == "candidate"
            ev = EvaluationEvidence(
                workspace_id=workspace_id,
                interview_id=interview_id,
                session_id=session_id,
                candidate_id=candidate_id,
                source_type=EvidenceSourceType.TRANSCRIPT.value,
                source_id=seg.id,
                competency_name=seg.detected_topics[0] if seg.detected_topics else None,
                content=seg.text,
                structured_payload={
                    "speaker_role": seg.speaker_role,
                    "confidence": seg.confidence,
                    "start_time": seg.start_time_seconds,
                    "end_time": seg.end_time_seconds,
                },
                evidence_timestamp_seconds=seg.start_time_seconds,
                quality_score=0.95 if is_cand else 0.8,
                confidence=seg.confidence,
                is_candidate_evidence=is_cand,
                is_interviewer_observation=not is_cand,
            )
            db.add(ev)
            evidence_records.append(ev)

        # 2. Coding Submissions & Test Execution Results (Authoritative sandbox)
        if session_id:
            stmt_cs = select(CodingSession).where(CodingSession.interview_session_id == session_id)
            res_cs = await db.execute(stmt_cs)
            coding_session = res_cs.scalars().first()
            if coding_session:
                stmt_submissions = (
                    select(CodingSubmission)
                    .where(CodingSubmission.coding_session_id == coding_session.id)
                    .order_by(desc(CodingSubmission.created_at))
                    .limit(5)
                )
                res_submissions = await db.execute(stmt_submissions)
                submissions = res_submissions.scalars().all()
                for sub in submissions:
                    content_desc = f"Coding Submission in {sub.language}: {sub.passed_test_cases}/{sub.total_test_cases} tests passed. Status: {sub.status}"
                    ev_code = EvaluationEvidence(
                        workspace_id=workspace_id,
                        interview_id=interview_id,
                        session_id=session_id,
                        candidate_id=candidate_id,
                        source_type=EvidenceSourceType.CODE_EXECUTION.value,
                        source_id=sub.id,
                        competency_name="Coding & Problem Solving",
                        content=content_desc,
                        structured_payload={
                            "language": sub.language,
                            "status": sub.status if isinstance(sub.status, str) else getattr(sub.status, "value", str(sub.status)),
                            "passed_tests": sub.passed_test_cases,
                            "total_tests": sub.total_test_cases,
                            "runtime_ms": sub.runtime_ms,
                            "memory_kb": sub.memory_kb,
                        },
                        evidence_timestamp_seconds=0.0,
                        quality_score=1.0,
                        confidence=1.0,
                        is_candidate_evidence=True,
                        is_interviewer_observation=False,
                    )
                    db.add(ev_code)
                    evidence_records.append(ev_code)

        # 3. Whiteboard Snapshots
        if session_id:
            stmt_wb_s = select(Whiteboard).where(Whiteboard.interview_session_id == session_id)
            res_wb_s = await db.execute(stmt_wb_s)
            whiteboard = res_wb_s.scalars().first()
            if whiteboard:
                stmt_wb = (
                    select(WhiteboardSnapshot)
                    .where(WhiteboardSnapshot.whiteboard_id == whiteboard.id)
                    .order_by(desc(WhiteboardSnapshot.created_at))
                    .limit(3)
                )
                res_wb = await db.execute(stmt_wb)
                snapshots = res_wb.scalars().all()
                for snap in snapshots:
                    ev_wb = EvaluationEvidence(
                        workspace_id=workspace_id,
                        interview_id=interview_id,
                        session_id=session_id,
                        candidate_id=candidate_id,
                        source_type=EvidenceSourceType.WHITEBOARD.value,
                        source_id=snap.id,
                        competency_name="System Design & Architecture",
                        content=f"Whiteboard Architecture Snapshot {snap.snapshot_number}: {snap.label}",
                        structured_payload=snap.document_json if isinstance(snap.document_json, dict) else {},
                        evidence_timestamp_seconds=0.0,
                        quality_score=0.9,
                        confidence=0.95,
                        is_candidate_evidence=True,
                        is_interviewer_observation=False,
                    )
                    db.add(ev_wb)
                    evidence_records.append(ev_wb)

        # 4. Resume Claims
        stmt_claims = (
            select(ResumeClaim)
            .where(
                ResumeClaim.candidate_id == candidate_id,
                ResumeClaim.workspace_id == workspace_id,
            )
            .limit(10)
        )
        res_claims = await db.execute(stmt_claims)
        claims = res_claims.scalars().all()
        for clm in claims:
            ev_clm = EvaluationEvidence(
                workspace_id=workspace_id,
                interview_id=interview_id,
                session_id=session_id,
                candidate_id=candidate_id,
                source_type=EvidenceSourceType.RESUME_CLAIM.value,
                source_id=clm.id,
                competency_name=clm.category,
                content=f"Resume Claim ({clm.category}): {clm.claim}",
                structured_payload={
                    "claim_status": clm.status,
                    "confidence": clm.confidence,
                    "verification_priority": clm.verification_priority,
                },
                evidence_timestamp_seconds=0.0,
                quality_score=0.85,
                confidence=clm.confidence,
                is_candidate_evidence=True,
                is_interviewer_observation=False,
            )
            db.add(ev_clm)
            evidence_records.append(ev_clm)

        # 5. Interviewer Notes (Observations)
        stmt_notes = (
            select(InterviewerNote)
            .where(InterviewerNote.session_id == session_id)
            .limit(10)
        )
        if session_id:
            res_notes = await db.execute(stmt_notes)
            notes = res_notes.scalars().all()
            for note in notes:
                ev_note = EvaluationEvidence(
                    workspace_id=workspace_id,
                    interview_id=interview_id,
                    session_id=session_id,
                    candidate_id=candidate_id,
                    source_type=EvidenceSourceType.INTERVIEWER_NOTE.value,
                    source_id=note.id,
                    competency_name=note.category,
                    content=f"Interviewer Note ({note.category}): {note.content}",
                    structured_payload={"category": note.category, "rating": note.rating},
                    evidence_timestamp_seconds=0.0,
                    quality_score=0.9,
                    confidence=0.9,
                    is_candidate_evidence=False,
                    is_interviewer_observation=True,
                )
                db.add(ev_note)
                evidence_records.append(ev_note)

        await db.flush()
        return evidence_records

    async def get_interview_evidence(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
    ) -> List[EvaluationEvidence]:
        """Retrieves all persisted evidence items for an interview."""
        stmt = (
            select(EvaluationEvidence)
            .where(
                EvaluationEvidence.interview_id == interview_id,
                EvaluationEvidence.workspace_id == workspace_id,
            )
            .order_by(EvaluationEvidence.created_at.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


evidence_service = EvidenceService()
