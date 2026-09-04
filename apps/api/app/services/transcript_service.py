"""
Transcript Service & Response Boundary Detector — Phase 14.

Manages speech-to-text transcript segments, speaker attribution, and real-time response boundary detection.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive_interview import (
    ResponseBoundaryStatus,
    TranscriptSegment,
)

logger = logging.getLogger("interviewos.api.transcript_service")


class ResponseBoundaryDetector:
    """
    Evaluates transcript segments and timing heuristics to determine if a candidate
    has finished speaking, is continuing, or was interrupted.
    """

    SILENCE_THRESHOLD_SECONDS = 2.5
    MIN_ANSWER_LENGTH_WORDS = 6

    @classmethod
    def detect_boundary(
        cls,
        segments: List[TranscriptSegment],
        latest_segment: TranscriptSegment,
        current_time_seconds: Optional[float] = None,
    ) -> Tuple[ResponseBoundaryStatus, str]:
        """
        Calculates the response boundary status based on transcript finality,
        speaker transitions, and punctuation cues.
        """
        if not latest_segment:
            return ResponseBoundaryStatus.RESPONSE_STARTED, "Initial state"

        text = latest_segment.text.strip()
        words = text.split()

        # If interviewer just spoke, previous candidate response was complete/interrupted
        if latest_segment.speaker_role in ["interviewer", "system"]:
            return ResponseBoundaryStatus.RESPONSE_COMPLETE, "Interviewer turn transition"

        # Check finality and punctuation signals
        ends_with_terminal_punct = text.endswith((".", "?", "!"))
        has_sufficient_words = len(words) >= cls.MIN_ANSWER_LENGTH_WORDS

        if latest_segment.is_final and ends_with_terminal_punct and has_sufficient_words:
            return ResponseBoundaryStatus.RESPONSE_COMPLETE, "Terminal punctuation and final segment confirmed"

        if not latest_segment.is_final:
            return ResponseBoundaryStatus.RESPONSE_CONTINUING, "Interim transcript streaming"

        if has_sufficient_words:
            return ResponseBoundaryStatus.RESPONSE_COMPLETE, "Complete thought segment reached"

        return ResponseBoundaryStatus.RESPONSE_STARTED, "Response in progress"


class TranscriptService:
    """Service handling transcript persistence, retrieval, and response boundary analysis."""

    async def add_segment(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        speaker_role: str,
        text: str,
        session_id: Optional[uuid.UUID] = None,
        speaker_id: Optional[uuid.UUID] = None,
        speaker_name: Optional[str] = None,
        start_time_seconds: float = 0.0,
        end_time_seconds: float = 0.0,
        confidence: float = 1.0,
        is_final: bool = True,
        detected_topics: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[TranscriptSegment, ResponseBoundaryStatus, str]:
        """Persists a new transcript segment and evaluates response boundary."""
        segment = TranscriptSegment(
            interview_id=interview_id,
            session_id=session_id,
            workspace_id=workspace_id,
            speaker_id=speaker_id,
            speaker_role=speaker_role,
            speaker_name=speaker_name,
            start_time_seconds=start_time_seconds,
            end_time_seconds=end_time_seconds,
            text=text.strip(),
            confidence=confidence,
            is_final=is_final,
            detected_topics=detected_topics or [],
        )

        if db is not None:
            db.add(segment)
            await db.flush()
            await db.refresh(segment)

        # Retrieve recent context for boundary analysis
        recent_segments: List[TranscriptSegment] = [segment]
        if db is not None:
            stmt = (
                select(TranscriptSegment)
                .where(TranscriptSegment.interview_id == interview_id)
                .order_by(desc(TranscriptSegment.created_at))
                .limit(10)
            )
            res = await db.execute(stmt)
            recent_segments = list(res.scalars().all())

        boundary_status, reason = ResponseBoundaryDetector.detect_boundary(
            segments=recent_segments,
            latest_segment=segment,
        )

        return segment, boundary_status, reason

    async def get_interview_transcripts(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 100,
    ) -> List[TranscriptSegment]:
        """Retrieves ordered transcript segments for an interview."""
        stmt = (
            select(TranscriptSegment)
            .where(
                TranscriptSegment.interview_id == interview_id,
                TranscriptSegment.workspace_id == workspace_id,
            )
            .order_by(TranscriptSegment.created_at.asc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


transcript_service = TranscriptService()
