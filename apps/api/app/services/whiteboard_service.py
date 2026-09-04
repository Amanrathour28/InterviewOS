import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.whiteboard import Whiteboard, WhiteboardSnapshot
from app.models.session import InterviewSession
from app.models.interview import Interview, InterviewParticipant, ParticipantRole
from app.models.user import User
from app.services.session_service import session_service
from app.schemas.whiteboard import (
    WhiteboardResponse,
    WhiteboardSnapshotResponse,
    WhiteboardUpdateRequest,
)

logger = logging.getLogger(__name__)


class WhiteboardService:
    async def get_or_create_whiteboard(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        is_candidate: bool = False,
    ) -> WhiteboardResponse:
        """Retrieves or creates the single primary Whiteboard for an interview session."""
        session_res = await db.execute(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        session = session_res.scalars().first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview session not found",
            )

        # Look up existing whiteboard
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.interview_session_id == session_id)
        )
        whiteboard = wb_res.scalars().first()

        if not whiteboard:
            # Create default empty whiteboard
            whiteboard = Whiteboard(
                interview_session_id=session_id,
                workspace_id=session.workspace_id,
                name="System Design Whiteboard",
                is_locked=False,
                document_json={},
                private_layer_json={},
                created_by=user_id,
            )
            db.add(whiteboard)
            await db.commit()
            await db.refresh(whiteboard)

            # Log durable event
            await session_service.log_event(
                session=session,
                event_type="WHITEBOARD_INITIALIZED",
                actor_id=user_id,
                actor_role="candidate" if is_candidate else "interviewer",
                payload={"whiteboard_id": str(whiteboard.id), "name": whiteboard.name},
                db=db,
            )
            await db.commit()

        return self._format_response(whiteboard, is_candidate=is_candidate)

    async def get_whiteboard_by_id(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        is_candidate: bool = False,
    ) -> WhiteboardResponse:
        """Fetch whiteboard by ID with candidate sanitization."""
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.id == whiteboard_id)
        )
        whiteboard = wb_res.scalars().first()
        if not whiteboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whiteboard not found",
            )
        return self._format_response(whiteboard, is_candidate=is_candidate)

    async def update_whiteboard(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        req: WhiteboardUpdateRequest,
        user_id: Optional[uuid.UUID] = None,
        is_candidate: bool = False,
    ) -> WhiteboardResponse:
        """Updates whiteboard document, private layer, or name with lock verification."""
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.id == whiteboard_id)
        )
        whiteboard = wb_res.scalars().first()
        if not whiteboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whiteboard not found",
            )

        # Enforce lock: if locked, candidate cannot mutate document or name
        if whiteboard.is_locked and is_candidate:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Whiteboard is currently locked by the interviewer",
            )

        # Candidate cannot mutate private_layer
        if is_candidate and req.private_layer is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates cannot access or mutate private interviewer layers",
            )

        if req.name is not None and not is_candidate:
            whiteboard.name = req.name
        if req.document is not None:
            whiteboard.document_json = req.document
        if req.private_layer is not None and not is_candidate:
            whiteboard.private_layer_json = req.private_layer

        whiteboard.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(whiteboard)

        return self._format_response(whiteboard, is_candidate=is_candidate)

    async def set_lock_status(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        is_locked: bool,
        user_id: Optional[uuid.UUID] = None,
    ) -> WhiteboardResponse:
        """Locks or unlocks the whiteboard for candidates."""
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.id == whiteboard_id)
        )
        whiteboard = wb_res.scalars().first()
        if not whiteboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whiteboard not found",
            )

        whiteboard.is_locked = is_locked
        whiteboard.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(whiteboard)

        # Log durable event
        session_res = await db.execute(
            select(InterviewSession).where(InterviewSession.id == whiteboard.interview_session_id)
        )
        session = session_res.scalars().first()
        if session:
            await session_service.log_event(
                session=session,
                event_type="WHITEBOARD_LOCKED" if is_locked else "WHITEBOARD_UNLOCKED",
                actor_id=user_id,
                actor_role="interviewer",
                payload={"whiteboard_id": str(whiteboard.id), "is_locked": is_locked},
                db=db,
            )
            await db.commit()

        return self._format_response(whiteboard, is_candidate=False)

    async def clear_whiteboard(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> WhiteboardResponse:
        """Clears the shared whiteboard document (Interviewer only)."""
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.id == whiteboard_id)
        )
        whiteboard = wb_res.scalars().first()
        if not whiteboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whiteboard not found",
            )

        whiteboard.document_json = {}
        whiteboard.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(whiteboard)

        # Log durable event
        session_res = await db.execute(
            select(InterviewSession).where(InterviewSession.id == whiteboard.interview_session_id)
        )
        session = session_res.scalars().first()
        if session:
            await session_service.log_event(
                session=session,
                event_type="WHITEBOARD_CLEARED",
                actor_id=user_id,
                actor_role="interviewer",
                payload={"whiteboard_id": str(whiteboard.id)},
                db=db,
            )
            await db.commit()

        return self._format_response(whiteboard, is_candidate=False)

    async def create_snapshot(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        label: str = "Milestone Checkpoint",
        source: str = "manual",
        user_id: Optional[uuid.UUID] = None,
    ) -> WhiteboardSnapshotResponse:
        """Creates an immutable snapshot of the whiteboard state."""
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.id == whiteboard_id)
        )
        whiteboard = wb_res.scalars().first()
        if not whiteboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whiteboard not found",
            )

        count_res = await db.execute(
            select(func.count(WhiteboardSnapshot.id)).where(
                WhiteboardSnapshot.whiteboard_id == whiteboard_id
            )
        )
        snapshot_count = count_res.scalar() or 0

        snapshot = WhiteboardSnapshot(
            whiteboard_id=whiteboard_id,
            created_by=user_id,
            snapshot_number=snapshot_count + 1,
            label=label,
            source=source,
            document_json=whiteboard.document_json or {},
            private_layer_json=whiteboard.private_layer_json or {},
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)

        # Log durable event
        session_res = await db.execute(
            select(InterviewSession).where(InterviewSession.id == whiteboard.interview_session_id)
        )
        session = session_res.scalars().first()
        if session:
            await session_service.log_event(
                session=session,
                event_type="WHITEBOARD_SNAPSHOT_CREATED",
                actor_id=user_id,
                actor_role="interviewer",
                payload={
                    "whiteboard_id": str(whiteboard.id),
                    "snapshot_id": str(snapshot.id),
                    "snapshot_number": snapshot.snapshot_number,
                    "label": snapshot.label,
                },
                db=db,
            )
            await db.commit()

        return self._format_snapshot(snapshot, is_candidate=False)

    async def list_snapshots(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        is_candidate: bool = False,
    ) -> List[WhiteboardSnapshotResponse]:
        """Lists all snapshots for a whiteboard with candidate privacy sanitization."""
        snaps_res = await db.execute(
            select(WhiteboardSnapshot)
            .where(WhiteboardSnapshot.whiteboard_id == whiteboard_id)
            .order_by(WhiteboardSnapshot.snapshot_number.desc())
        )
        snapshots = snaps_res.scalars().all()
        return [self._format_snapshot(s, is_candidate=is_candidate) for s in snapshots]

    async def restore_snapshot(
        self,
        db: AsyncSession,
        whiteboard_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> WhiteboardResponse:
        """Restores a whiteboard to the exact state captured in a snapshot."""
        wb_res = await db.execute(
            select(Whiteboard).where(Whiteboard.id == whiteboard_id)
        )
        whiteboard = wb_res.scalars().first()
        if not whiteboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whiteboard not found",
            )

        snap_res = await db.execute(
            select(WhiteboardSnapshot).where(
                WhiteboardSnapshot.id == snapshot_id,
                WhiteboardSnapshot.whiteboard_id == whiteboard_id,
            )
        )
        snapshot = snap_res.scalars().first()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found",
            )

        whiteboard.document_json = snapshot.document_json or {}
        whiteboard.private_layer_json = snapshot.private_layer_json or {}
        whiteboard.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(whiteboard)

        # Log durable event
        session_res = await db.execute(
            select(InterviewSession).where(InterviewSession.id == whiteboard.interview_session_id)
        )
        session = session_res.scalars().first()
        if session:
            await session_service.log_event(
                session=session,
                event_type="WHITEBOARD_RESTORED",
                actor_id=user_id,
                actor_role="interviewer",
                payload={
                    "whiteboard_id": str(whiteboard.id),
                    "snapshot_id": str(snapshot.id),
                    "snapshot_number": snapshot.snapshot_number,
                },
                db=db,
            )
            await db.commit()

        return self._format_response(whiteboard, is_candidate=False)

    def _format_response(self, wb: Whiteboard, is_candidate: bool = False) -> WhiteboardResponse:
        snaps = [
            self._format_snapshot(s, is_candidate=is_candidate)
            for s in (wb.snapshots or [])
        ]
        return WhiteboardResponse(
            id=wb.id,
            interview_session_id=wb.interview_session_id,
            workspace_id=wb.workspace_id,
            name=wb.name,
            is_locked=wb.is_locked,
            document=wb.document_json or {},
            private_layer=None if is_candidate else (wb.private_layer_json or {}),
            created_by=wb.created_by,
            snapshots=snaps,
            created_at=wb.created_at,
            updated_at=wb.updated_at,
        )

    def _format_snapshot(
        self, s: WhiteboardSnapshot, is_candidate: bool = False
    ) -> WhiteboardSnapshotResponse:
        return WhiteboardSnapshotResponse(
            id=s.id,
            whiteboard_id=s.whiteboard_id,
            created_by=s.created_by,
            snapshot_number=s.snapshot_number,
            label=s.label,
            source=s.source,
            document=s.document_json or {},
            private_layer=None if is_candidate else (s.private_layer_json or {}),
            created_at=s.created_at,
        )


whiteboard_service = WhiteboardService()
