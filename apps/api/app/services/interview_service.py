import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.interview import (
    Interview,
    InterviewParticipant,
    InterviewRound,
    InterviewRoundQuestion,
    InterviewStatus,
    InterviewTemplate,
    InterviewTemplateRound,
    ParticipantRole,
    Question,
)
from app.models.job import Job
from app.models.workspace import WorkspaceMembership


VALID_TRANSITIONS = {
    InterviewStatus.DRAFT: {InterviewStatus.READY, InterviewStatus.CANCELLED},
    InterviewStatus.READY: {InterviewStatus.DRAFT, InterviewStatus.SCHEDULED, InterviewStatus.CANCELLED},
    InterviewStatus.SCHEDULED: {InterviewStatus.READY, InterviewStatus.IN_PROGRESS, InterviewStatus.CANCELLED},
    InterviewStatus.IN_PROGRESS: {InterviewStatus.COMPLETED, InterviewStatus.CANCELLED},
    InterviewStatus.COMPLETED: set(),
    InterviewStatus.CANCELLED: set(),
    InterviewStatus.EXPIRED: set(),
}


class InterviewService:
    """Business logic and validation engine for interview lifecycle, rounds, and templates."""

    async def validate_interview_readiness(
        self,
        interview: Interview,
        db: AsyncSession,
    ) -> Tuple[bool, List[str]]:
        """Validates all prerequisites before an interview can transition to READY status."""
        issues: List[str] = []

        # 1. Candidate validation
        cand_stmt = select(Candidate).where(
            Candidate.id == interview.candidate_id,
            Candidate.workspace_id == interview.workspace_id,
            Candidate.is_deleted.is_(False),
        )
        cand_res = await db.execute(cand_stmt)
        if not cand_res.scalar_one_or_none():
            issues.append("Assigned candidate does not exist or does not belong to this workspace.")

        # 2. Job validation (if set)
        if interview.job_id:
            job_stmt = select(Job).where(
                Job.id == interview.job_id,
                Job.workspace_id == interview.workspace_id,
                Job.is_deleted.is_(False),
            )
            job_res = await db.execute(job_stmt)
            if not job_res.scalar_one_or_none():
                issues.append("Assigned job does not exist or does not belong to this workspace.")

        # 3. Duration validation
        if not interview.duration_minutes or interview.duration_minutes <= 0:
            issues.append("Interview duration must be greater than 0 minutes.")

        # 4. Rounds validation
        rounds_stmt = (
            select(InterviewRound)
            .where(
                InterviewRound.interview_id == interview.id,
                InterviewRound.is_deleted.is_(False),
            )
            .order_by(InterviewRound.sequence.asc())
            .options(selectinload(InterviewRound.round_questions))
        )
        rounds_res = await db.execute(rounds_stmt)
        rounds = rounds_res.scalars().all()

        if not rounds:
            issues.append("Interview must have at least one round configured.")
        else:
            total_round_duration = 0
            sequences_seen = set()

            for r in rounds:
                if r.sequence in sequences_seen:
                    issues.append(f"Duplicate sequence number {r.sequence} found in rounds.")
                sequences_seen.add(r.sequence)

                if r.duration_minutes <= 0:
                    issues.append(f"Round '{r.name}' duration must be greater than 0.")
                total_round_duration += r.duration_minutes

                # Check assigned questions belong to workspace or system
                for rq in r.round_questions:
                    q_stmt = select(Question).where(
                        Question.id == rq.question_id,
                        (Question.workspace_id == interview.workspace_id) | (Question.workspace_id.is_(None)),
                        Question.is_deleted.is_(False),
                    )
                    if not (await db.execute(q_stmt)).scalar_one_or_none():
                        issues.append(f"Question in round '{r.name}' does not belong to this workspace.")

            if total_round_duration > interview.duration_minutes:
                issues.append(
                    f"Sum of round durations ({total_round_duration} mins) exceeds total interview duration ({interview.duration_minutes} mins)."
                )

        # 5. Participants validation
        parts_stmt = select(InterviewParticipant).where(InterviewParticipant.interview_id == interview.id)
        parts_res = await db.execute(parts_stmt)
        participants = parts_res.scalars().all()

        for p in participants:
            ws_mem_stmt = select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == interview.workspace_id,
                WorkspaceMembership.user_id == p.user_id,
            )
            if not (await db.execute(ws_mem_stmt)).scalar_one_or_none():
                issues.append(f"Participant user {p.user_id} is not an authorized member of this workspace.")

        is_ready = len(issues) == 0
        return is_ready, issues

    def validate_state_transition(
        self,
        current_status: InterviewStatus,
        target_status: InterviewStatus,
        is_ready: bool,
        issues: List[str],
    ) -> None:
        """Enforces state machine rules and blocks invalid transitions."""
        if target_status == current_status:
            return

        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interview state transition from '{current_status.value}' to '{target_status.value}'.",
            )

        if target_status == InterviewStatus.READY and not is_ready:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot mark interview as READY: {'; '.join(issues)}",
            )

    async def instantiate_interview_from_template(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: Optional[uuid.UUID],
        title: Optional[str],
        created_by: uuid.UUID,
        db: AsyncSession,
    ) -> Interview:
        """Clones a template into an independent Interview configuration."""
        # 1. Fetch template
        tpl_stmt = (
            select(InterviewTemplate)
            .where(
                InterviewTemplate.id == template_id,
                (InterviewTemplate.workspace_id == workspace_id) | (InterviewTemplate.is_system.is_(True)),
                InterviewTemplate.is_deleted.is_(False),
            )
            .options(
                selectinload(InterviewTemplate.template_rounds).selectinload(
                    InterviewTemplateRound.template_questions
                )
            )
        )
        tpl_res = await db.execute(tpl_stmt)
        template = tpl_res.scalar_one_or_none()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview template not found or unauthorized",
            )

        # 2. Verify candidate belongs to workspace
        cand_stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.workspace_id == workspace_id,
            Candidate.is_deleted.is_(False),
        )
        if not (await db.execute(cand_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found in this workspace",
            )

        # 3. Verify job if provided
        if job_id:
            job_stmt = select(Job).where(
                Job.id == job_id,
                Job.workspace_id == workspace_id,
                Job.is_deleted.is_(False),
            )
            if not (await db.execute(job_stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found in this workspace",
                )

        # 4. Create interview
        interview_title = title.strip() if title else f"{template.name} - Interview"
        new_interview = Interview(
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            job_id=job_id,
            created_by=created_by,
            template_id=template.id,
            title=interview_title,
            description=template.description or "",
            interview_type=template.interview_type,
            difficulty=template.difficulty,
            duration_minutes=template.total_duration_minutes,
            status=InterviewStatus.DRAFT,
        )
        db.add(new_interview)
        await db.flush()

        # 5. Copy rounds and questions
        for tpl_round in template.template_rounds:
            new_round = InterviewRound(
                interview_id=new_interview.id,
                name=tpl_round.name,
                description=tpl_round.description,
                round_type=tpl_round.round_type,
                sequence=tpl_round.sequence,
                duration_minutes=tpl_round.duration_minutes,
                difficulty=tpl_round.difficulty,
                instructions=tpl_round.instructions,
                configuration=tpl_round.configuration or {},
                is_required=True,
            )
            db.add(new_round)
            await db.flush()

            for tpl_q in tpl_round.template_questions:
                round_q = InterviewRoundQuestion(
                    round_id=new_round.id,
                    question_id=tpl_q.question_id,
                    sequence=tpl_q.sequence,
                    is_required=True,
                )
                db.add(round_q)

        await db.commit()
        await db.refresh(new_interview)
        return new_interview


interview_service = InterviewService()
