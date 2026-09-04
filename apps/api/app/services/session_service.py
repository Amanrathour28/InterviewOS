import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
import jwt
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import JWT_ALGORITHM
from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewParticipant, InterviewStatus
from app.models.session import (
    InterviewEvent,
    InterviewSession,
    InterviewerNote,
    NoteCategory,
    SessionStage,
    SessionStatus,
)
from app.models.user import User

logger = logging.getLogger(__name__)


class InterviewSessionService:
    """Manages the live execution lifecycle, state transitions, event logs, and join tokens."""

    async def get_or_create_session(
        self,
        interview: Interview,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> InterviewSession:
        """Retrieves an existing active/waiting session or atomically initializes a new one."""

        # 1. Check workspace match
        if interview.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Interview does not belong to the target workspace",
            )

        # 2. Check parent interview state
        if interview.status == InterviewStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start a session for a cancelled interview",
            )
        if interview.status == InterviewStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview has already been completed",
            )

        # 3. Search for existing active or waiting session
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.interview_id == interview.id,
                InterviewSession.status.in_([
                    SessionStatus.WAITING,
                    SessionStatus.ACTIVE,
                    SessionStatus.PAUSED,
                ]),
                InterviewSession.is_deleted.is_(False),
            )
            .order_by(InterviewSession.created_at.desc())
        )
        existing_session = (await db.execute(stmt)).scalar_one_or_none()
        if existing_session:
            return existing_session

        # 4. Create new waiting session
        new_session = InterviewSession(
            interview_id=interview.id,
            workspace_id=interview.workspace_id,
            status=SessionStatus.WAITING,
            current_stage=SessionStage.INTRODUCTION.value,
            stage_started_at=datetime.now(timezone.utc),
            last_event_sequence=0,
            created_by=user_id,
        )
        db.add(new_session)
        await db.flush()

        # 5. Log initial SESSION_CREATED event
        await self.log_event(
            session=new_session,
            event_type="SESSION_CREATED",
            actor_id=user_id,
            actor_role="organizer",
            payload={"stage": new_session.current_stage},
            db=db,
        )

        await db.commit()
        await db.refresh(new_session)
        return new_session

    async def get_session(
        self,
        session_id: uuid.UUID,
        db: AsyncSession,
    ) -> InterviewSession:
        """Retrieves an existing session with eager loaded relationships."""
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id, InterviewSession.is_deleted.is_(False))
            .options(
                selectinload(InterviewSession.workspace),
                selectinload(InterviewSession.interview).selectinload(Interview.candidate),
                selectinload(InterviewSession.interview).selectinload(Interview.job),
                selectinload(InterviewSession.interview).selectinload(Interview.participants).selectinload(
                    InterviewParticipant.user
                ),
            )
        )
        session = (await db.execute(stmt)).scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
        return session

    async def start_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> InterviewSession:
        """Transitions session from WAITING (or PAUSED) to ACTIVE."""
        session = await self.get_session(session_id, db)

        if session.status == SessionStatus.ACTIVE:
            return session

        if session.status == SessionStatus.PAUSED:
            return await self.resume_session(session_id, user_id, db)

        if session.status != SessionStatus.WAITING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start session in status '{session.status.value}'",
            )

        now_utc = datetime.now(timezone.utc)
        session.status = SessionStatus.ACTIVE
        session.started_at = now_utc
        session.stage_started_at = now_utc

        # Update parent interview status
        if session.interview:
            session.interview.status = InterviewStatus.IN_PROGRESS

        await self.log_event(
            session=session,
            event_type="SESSION_STARTED",
            actor_id=user_id,
            actor_role="interviewer",
            payload={"started_at": now_utc.isoformat(), "current_stage": session.current_stage},
            db=db,
        )

        await db.commit()
        await db.refresh(session)
        return session

    async def pause_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
        reason: Optional[str] = None,
    ) -> InterviewSession:
        """Transitions session from ACTIVE to PAUSED."""
        session = await self.get_session(session_id, db)

        if session.status == SessionStatus.PAUSED:
            return session

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause session in status '{session.status.value}'",
            )

        now_utc = datetime.now(timezone.utc)
        session.status = SessionStatus.PAUSED
        session.paused_at = now_utc

        await self.log_event(
            session=session,
            event_type="SESSION_PAUSED",
            actor_id=user_id,
            actor_role="interviewer",
            payload={"paused_at": now_utc.isoformat(), "reason": reason},
            db=db,
        )

        await db.commit()
        await db.refresh(session)
        return session

    async def resume_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> InterviewSession:
        """Transitions session from PAUSED to ACTIVE."""
        session = await self.get_session(session_id, db)

        if session.status == SessionStatus.ACTIVE:
            return session

        if session.status != SessionStatus.PAUSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume session in status '{session.status.value}'",
            )

        now_utc = datetime.now(timezone.utc)
        if session.paused_at:
            paused_at = session.paused_at if session.paused_at.tzinfo else session.paused_at.replace(tzinfo=timezone.utc)
            paused_seconds = (now_utc - paused_at).total_seconds()
            session.total_paused_seconds += int(max(0, paused_seconds))

        session.status = SessionStatus.ACTIVE
        session.paused_at = None

        await self.log_event(
            session=session,
            event_type="SESSION_RESUMED",
            actor_id=user_id,
            actor_role="interviewer",
            payload={"resumed_at": now_utc.isoformat(), "total_paused_seconds": session.total_paused_seconds},
            db=db,
        )

        await db.commit()
        await db.refresh(session)
        return session

    async def end_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
        reason: Optional[str] = None,
    ) -> InterviewSession:
        """Transitions session from ACTIVE or PAUSED to COMPLETED."""
        session = await self.get_session(session_id, db)

        if session.status == SessionStatus.COMPLETED:
            return session

        if session.status not in [SessionStatus.ACTIVE, SessionStatus.PAUSED, SessionStatus.WAITING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot end session in status '{session.status.value}'",
            )

        now_utc = datetime.now(timezone.utc)
        session.status = SessionStatus.COMPLETED
        session.ended_at = now_utc
        session.current_stage = SessionStage.COMPLETED.value

        # Update parent interview status
        if session.interview:
            session.interview.status = InterviewStatus.COMPLETED

        await self.log_event(
            session=session,
            event_type="SESSION_ENDED",
            actor_id=user_id,
            actor_role="interviewer",
            payload={
                "ended_at": now_utc.isoformat(),
                "reason": reason,
                "elapsed_seconds": self.calculate_elapsed_seconds(session),
            },
            db=db,
        )

        await db.commit()
        await db.refresh(session)
        return session

    async def change_stage(
        self,
        session_id: uuid.UUID,
        new_stage: str,
        user_id: uuid.UUID,
        db: AsyncSession,
        reason: Optional[str] = None,
    ) -> InterviewSession:
        """Changes the current stage of the interview session."""
        session = await self.get_session(session_id, db)

        if session.status not in [SessionStatus.ACTIVE, SessionStatus.WAITING, SessionStatus.PAUSED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change stage for session in status '{session.status.value}'",
            )

        previous_stage = session.current_stage
        now_utc = datetime.now(timezone.utc)
        session.current_stage = new_stage
        session.stage_started_at = now_utc

        await self.log_event(
            session=session,
            event_type="STAGE_CHANGED",
            actor_id=user_id,
            actor_role="interviewer",
            payload={
                "previous_stage": previous_stage,
                "new_stage": new_stage,
                "stage_started_at": now_utc.isoformat(),
                "reason": reason,
            },
            db=db,
        )

        await db.commit()
        await db.refresh(session)
        return session

    async def log_event(
        self,
        session: InterviewSession,
        event_type: str,
        actor_id: Optional[uuid.UUID],
        actor_role: str,
        payload: Dict[str, Any],
        db: AsyncSession,
    ) -> InterviewEvent:
        """Monotonically increments session sequence and persists a durable event."""
        session.last_event_sequence += 1
        sequence_num = session.last_event_sequence

        event = InterviewEvent(
            session_id=session.id,
            event_type=event_type,
            actor_id=actor_id,
            actor_role=actor_role,
            sequence=sequence_num,
            payload=payload or {},
        )
        db.add(event)
        return event

    def calculate_elapsed_seconds(self, session: InterviewSession) -> int:
        """Server-authoritative elapsed seconds calculation."""
        if not session.started_at:
            return 0

        now_utc = datetime.now(timezone.utc)
        start = session.started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        if session.status == SessionStatus.COMPLETED and session.ended_at:
            end = session.ended_at
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            duration = (end - start).total_seconds()
        elif session.status == SessionStatus.PAUSED and session.paused_at:
            paused = session.paused_at
            if paused.tzinfo is None:
                paused = paused.replace(tzinfo=timezone.utc)
            duration = (paused - start).total_seconds()
        else:
            duration = (now_utc - start).total_seconds()

        elapsed = max(0, int(duration) - session.total_paused_seconds)
        return elapsed

    def calculate_remaining_seconds(self, session: InterviewSession, duration_minutes: int) -> int:
        """Calculates server-authoritative remaining time in seconds."""
        total_allocated = duration_minutes * 60
        elapsed = self.calculate_elapsed_seconds(session)
        return max(0, total_allocated - elapsed)

    def calculate_stage_elapsed_seconds(self, session: InterviewSession) -> int:
        """Calculates seconds elapsed since the current stage began."""
        if not session.stage_started_at:
            return 0

        now_utc = datetime.now(timezone.utc)
        start = session.stage_started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        if session.status == SessionStatus.COMPLETED and session.ended_at:
            end = session.ended_at
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            return max(0, int((end - start).total_seconds()))
        elif session.status == SessionStatus.PAUSED and session.paused_at:
            paused = session.paused_at
            if paused.tzinfo is None:
                paused = paused.replace(tzinfo=timezone.utc)
            return max(0, int((paused - start).total_seconds()))
        else:
            return max(0, int((now_utc - start).total_seconds()))

    async def create_note(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        category: NoteCategory,
        content: str,
        stage: Optional[str],
        rating: Optional[int],
        tags: List[str],
        db: AsyncSession,
    ) -> InterviewerNote:
        """Creates a structured private note for the session."""
        session = await self.get_session(session_id, db)
        note = InterviewerNote(
            session_id=session.id,
            user_id=user_id,
            category=category,
            stage=stage or session.current_stage,
            content=content,
            rating=rating,
            tags=tags or [],
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    async def list_notes(
        self,
        session_id: uuid.UUID,
        category: Optional[NoteCategory],
        stage: Optional[str],
        db: AsyncSession,
    ) -> List[InterviewerNote]:
        """Lists private interviewer notes with optional category/stage filtering."""
        query = (
            select(InterviewerNote)
            .where(
                InterviewerNote.session_id == session_id,
                InterviewerNote.is_deleted.is_(False),
            )
            .order_by(InterviewerNote.created_at.desc())
            .options(selectinload(InterviewerNote.user))
        )
        if category:
            query = query.where(InterviewerNote.category == category)
        if stage:
            query = query.where(InterviewerNote.stage == stage)

        res = await db.execute(query)
        return res.scalars().all()

    async def delete_note(
        self,
        session_id: uuid.UUID,
        note_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        """Soft-deletes a private note."""
        stmt = select(InterviewerNote).where(
            InterviewerNote.id == note_id,
            InterviewerNote.session_id == session_id,
            InterviewerNote.is_deleted.is_(False),
        )
        note = (await db.execute(stmt)).scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
        note.is_deleted = True
        await db.commit()

    async def get_timeline(
        self,
        session_id: uuid.UUID,
        category: Optional[str],
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Retrieves structured session activity events with category mapping."""
        stmt = (
            select(InterviewEvent)
            .where(InterviewEvent.session_id == session_id)
            .order_by(InterviewEvent.sequence.desc())
        )
        res = await db.execute(stmt)
        events = res.scalars().all()

        timeline = []
        for e in events:
            # Map event_type to human readable category and title
            event_cat = "lifecycle"
            title = e.event_type.replace("_", " ").title()

            if "STAGE" in e.event_type:
                event_cat = "stages"
                stage_name = (e.payload or {}).get("new_stage", "stage")
                title = f"Moved to {stage_name.replace('_', ' ').title()}"
            elif "CODING" in e.event_type or "SUBMISSION" in e.event_type:
                event_cat = "coding"
                if "SUBMISSION" in e.event_type:
                    title = f"Candidate Code Submission (Status: {(e.payload or {}).get('status', 'submitted')})"
                elif "LOCKED" in e.event_type:
                    title = "Code Editor Locked by Interviewer"
            elif "WHITEBOARD" in e.event_type:
                event_cat = "whiteboard"
                if "SNAPSHOT" in e.event_type:
                    title = f"Whiteboard Snapshot Captured: {(e.payload or {}).get('label', 'Checkpoint')}"
                elif "LOCKED" in e.event_type:
                    title = "Whiteboard Locked by Interviewer"
            elif "CHAT" in e.event_type:
                event_cat = "chat"
            elif "PARTICIPANT" in e.event_type:
                event_cat = "participants"
                if "JOINED" in e.event_type:
                    title = f"Participant Joined ({e.actor_role})"
                elif "LEFT" in e.event_type:
                    title = f"Participant Left ({e.actor_role})"

            if category and category != "all" and event_cat != category:
                continue

            timeline.append({
                "id": str(e.id),
                "event_type": e.event_type,
                "category": event_cat,
                "title": title,
                "actor_name": f"{e.actor_role.title()}",
                "actor_role": e.actor_role,
                "timestamp": e.created_at,
                "sequence": e.sequence,
                "payload": e.payload or {},
            })
        return timeline

    def generate_join_token(
        self,
        session: InterviewSession,
        user: User,
        role: str,
        is_interviewer: bool,
    ) -> Tuple[str, int]:
        """Generates a secure, short-lived JWT token for the WebSocket gateway handshake."""
        expires_seconds = 3600  # 1 hour
        expire_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)

        payload = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "user_name": f"{user.first_name} {user.last_name}".strip(),
            "user_email": user.email,
            "session_id": str(session.id),
            "interview_id": str(session.interview_id),
            "workspace_id": str(session.workspace_id),
            "role": role,
            "is_interviewer": is_interviewer,
            "exp": expire_at,
            "iat": datetime.now(timezone.utc),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, expires_seconds

    def get_ice_servers(self) -> List[Dict[str, Any]]:
        """Returns standard WebRTC STUN/TURN ICE server configuration."""
        servers = []
        if getattr(settings, "STUN_SERVER_URL", None):
            servers.append({"urls": settings.STUN_SERVER_URL})
        if getattr(settings, "TURN_SERVER_URL", None):
            turn_entry: Dict[str, Any] = {"urls": settings.TURN_SERVER_URL}
            if getattr(settings, "TURN_USERNAME", None):
                turn_entry["username"] = settings.TURN_USERNAME
            if getattr(settings, "TURN_CREDENTIAL", None):
                turn_entry["credential"] = settings.TURN_CREDENTIAL
            servers.append(turn_entry)
        return servers


session_service = InterviewSessionService()

