"""
Interview Blueprint Service — Phase 13.

Manages the lifecycle of AI-recommended interview structures:
- Generation & Versioning
- Review & Edits
- Interviewer Approval
- Safe Application to Interview Configuration
"""

from datetime import datetime, timezone
import uuid
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.intelligence import (
    BlueprintStatus,
    InterviewBlueprint,
    InterviewBlueprintRound,
)
from app.models.interview import (
    Interview,
    InterviewRound,
    InterviewStatus,
    InterviewType,
    RoundType,
)
from app.models.user import User

logger = logging.getLogger("interviewos.blueprint_service")


class BlueprintService:
    """Handles interview blueprint generation, approval, and application workflows."""

    async def apply_blueprint_to_interview(
        self,
        blueprint: InterviewBlueprint,
        interview: Interview,
        approver: User,
        db: AsyncSession,
    ) -> Interview:
        """
        Applies an approved blueprint to configure an interview.
        Enforces safety rules: cannot apply to an interview currently in progress.
        """
        # Safety Check: Do NOT mutate an in-progress or completed interview
        itw_status_val = interview.status.value if hasattr(interview.status, "value") else str(interview.status)
        if itw_status_val in ["in_progress", "completed", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot apply blueprint to an interview with status '{itw_status_val}'. Live in progress or completed interviews cannot be altered.",
            )

        if blueprint.status != BlueprintStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Blueprint must be approved by an interviewer before application (current: {blueprint.status.value if hasattr(blueprint.status, 'value') else blueprint.status})",
            )

        # Clear existing draft rounds if any
        # Delete existing rounds
        for existing_round in list(interview.rounds):
            await db.delete(existing_round)
        await db.flush()

        # Create new rounds from blueprint rounds
        new_rounds: List[InterviewRound] = []
        total_duration = 0

        for b_round in sorted(blueprint.rounds, key=lambda r: r.sequence):
            # Map round type string to RoundType enum
            r_type_str = (b_round.round_type or "technical").lower()
            try:
                r_type = RoundType(r_type_str)
            except ValueError:
                r_type = RoundType.TECHNICAL

            ir = InterviewRound(
                interview_id=interview.id,
                name=b_round.name,
                round_type=r_type,
                sequence=b_round.sequence,
                duration_minutes=b_round.duration_minutes,
                instructions=f"Focus areas: {', '.join(b_round.competencies or [])}",
                configuration={
                    "objectives": b_round.objectives or [],
                    "competencies": b_round.competencies or [],
                    "topics": b_round.topics or [],
                    "suggested_question_count": b_round.suggested_question_count,
                    "scoring_weight": b_round.scoring_weight,
                    "blueprint_id": str(blueprint.id),
                    "blueprint_round_id": str(b_round.id),
                },
            )
            db.add(ir)
            new_rounds.append(ir)
            total_duration += b_round.duration_minutes

        # Update interview metadata
        interview.duration_minutes = total_duration
        if blueprint.title and "Blueprint" not in interview.title:
            interview.description = f"{interview.description}\n\nBlueprint Focus: {', '.join(blueprint.candidate_focus_areas or [])}".strip()

        # Mark blueprint as applied
        blueprint.status = BlueprintStatus.APPLIED
        blueprint.applied_at = datetime.now(timezone.utc)
        if not blueprint.approved_by:
            blueprint.approved_by = approver.id
            blueprint.approved_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(interview)
        logger.info(
            "Successfully applied blueprint %s to interview %s with %d rounds",
            blueprint.id,
            interview.id,
            len(new_rounds),
        )
        return interview


blueprint_service = BlueprintService()
