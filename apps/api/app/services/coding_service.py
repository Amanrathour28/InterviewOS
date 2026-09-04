import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coding import (
    CodingExecutionJob,
    CodingExecutionResult,
    CodingFile,
    CodingSession,
    CodingSessionStatus,
    CodingSnapshot,
    CodingSnapshotReason,
    CodingTestCase,
    ExecutionJobStatus,
    ExecutionResultStatus,
)
from app.models.session import InterviewSession, SessionStatus
from app.schemas.coding import (
    CodingExecutionRequest,
    CodingFileCreateRequest,
    CodingFileUpdateRequest,
    TestResultItem,
)
from app.services.session_service import session_service

# Add code-runner to path for local sandbox execution
runner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../code-runner"))
if runner_path not in sys.path:
    sys.path.insert(0, runner_path)

try:
    from sandbox_executor import sandbox_executor
    from languages import get_language_config
except ImportError:
    sandbox_executor = None
    get_language_config = None


DEFAULT_PYTHON_STARTER = """def solve():
    # Write your solution here
    print("Hello, InterviewOS!")

if __name__ == "__main__":
    solve()
"""


class CodingService:
    @staticmethod
    def validate_safe_path(file_path: str) -> str:
        """Validates relative path to strictly forbid path traversal attacks."""
        if not file_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File path cannot be empty")

        cleaned = file_path.strip().replace("\\", "/")

        # Disallow absolute paths, drive letters, leading slashes, and parent traversal
        if cleaned.startswith("/") or re.match(r"^[a-zA-Z]:", cleaned) or ".." in cleaned.split("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file path. Path traversal and absolute paths are strictly forbidden: '{file_path}'",
            )

        norm = os.path.normpath(cleaned).replace("\\", "/")
        if norm.startswith("..") or os.path.isabs(norm) or norm.startswith("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file path: '{file_path}'",
            )
        return norm

    async def get_or_create_coding_session(
        self, interview_session: InterviewSession, user_id: uuid.UUID, db: AsyncSession
    ) -> CodingSession:
        """Idempotently gets or creates the coding session attached to an interview session."""
        result = await db.execute(
            select(CodingSession)
            .options(
                selectinload(CodingSession.files),
                selectinload(CodingSession.snapshots),
                selectinload(CodingSession.test_cases),
                selectinload(CodingSession.execution_jobs).selectinload(CodingExecutionJob.result),
            )
            .where(CodingSession.interview_session_id == interview_session.id)
        )
        coding_session = result.scalar_one_or_none()
        if coding_session:
            return coding_session

        # Create new coding session
        coding_session = CodingSession(
            id=uuid.uuid4(),
            interview_session_id=interview_session.id,
            workspace_id=interview_session.workspace_id,
            language="python",
            status=CodingSessionStatus.ACTIVE,
            is_editor_locked=False,
            settings_json={"fontSize": 14, "tabSize": 4, "wordWrap": "on"},
        )
        db.add(coding_session)
        await db.flush()

        # Create default main.py file
        initial_file = CodingFile(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            workspace_id=interview_session.workspace_id,
            path="main.py",
            name="main.py",
            language="python",
            content=DEFAULT_PYTHON_STARTER,
            is_active=True,
        )
        db.add(initial_file)
        await db.flush()

        coding_session.active_file_id = initial_file.id

        # Create initial snapshot
        initial_snapshot = CodingSnapshot(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            created_by=user_id,
            reason=CodingSnapshotReason.SESSION_START,
            files_json=[{
                "path": initial_file.path,
                "name": initial_file.name,
                "language": initial_file.language,
                "content": initial_file.content,
            }],
        )
        db.add(initial_snapshot)

        # Log monotonic event
        await session_service.log_event(
            session=interview_session,
            event_type="CODE_SESSION_CREATED",
            actor_id=user_id,
            actor_role="organizer",
            payload={
                "coding_session_id": str(coding_session.id),
                "language": coding_session.language,
                "active_file": initial_file.name,
            },
            db=db,
        )

        await db.commit()
        await db.refresh(coding_session)
        return coding_session

    async def get_coding_session_or_404(
        self, coding_session_id: uuid.UUID, db: AsyncSession
    ) -> CodingSession:
        result = await db.execute(
            select(CodingSession)
            .options(
                selectinload(CodingSession.files),
                selectinload(CodingSession.snapshots),
                selectinload(CodingSession.test_cases),
                selectinload(CodingSession.execution_jobs).selectinload(CodingExecutionJob.result),
            )
            .where(CodingSession.id == coding_session_id)
        )
        coding_session = result.scalar_one_or_none()
        if not coding_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coding session not found")
        return coding_session

    async def set_editor_lock(
        self,
        coding_session_id: uuid.UUID,
        is_locked: bool,
        user_id: uuid.UUID,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> CodingSession:
        """Sets the editor lock state. Only interviewer/admin can toggle lock."""
        if not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only interviewers and panelists can lock or unlock the coding workspace",
            )

        coding_session = await self.get_coding_session_or_404(coding_session_id, db)
        coding_session.is_editor_locked = is_locked
        coding_session.updated_at = datetime.now(timezone.utc)

        # Log monotonic event
        sess = await session_service.get_session(coding_session.interview_session_id, db)
        event_type = "CODE_EDITOR_LOCKED" if is_locked else "CODE_EDITOR_UNLOCKED"
        await session_service.log_event(
            session=sess,
            event_type=event_type,
            actor_id=user_id,
            actor_role="interviewer",
            payload={"coding_session_id": str(coding_session.id), "is_locked": is_locked},
            db=db,
        )

        await db.commit()
        await db.refresh(coding_session)
        return coding_session

    async def create_file(
        self,
        coding_session_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        request: CodingFileCreateRequest,
        db: AsyncSession,
    ) -> CodingFile:
        """Creates a new file in the coding session."""
        coding_session = await self.get_coding_session_or_404(coding_session_id, db)

        if coding_session.is_editor_locked and not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editor is currently locked by the interviewer",
            )

        safe_path = self.validate_safe_path(request.path)

        # Check existing file with same path
        existing_res = await db.execute(
            select(CodingFile).where(
                and_(
                    CodingFile.coding_session_id == coding_session.id,
                    CodingFile.path == safe_path,
                )
            )
        )
        if existing_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A file with path '{safe_path}' already exists in this workspace",
            )

        file = CodingFile(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            workspace_id=coding_session.workspace_id,
            path=safe_path,
            name=request.name or os.path.basename(safe_path),
            language=request.language or "python",
            content=request.content or "",
            is_active=False,
        )
        db.add(file)

        sess = await session_service.get_session(coding_session.interview_session_id, db)
        await session_service.log_event(
            session=sess,
            event_type="CODE_FILE_CREATED",
            actor_id=user_id,
            actor_role="interviewer" if is_interviewer else "candidate",
            payload={"file_id": str(file.id), "path": file.path, "name": file.name},
            db=db,
        )

        await db.commit()
        await db.refresh(file)
        return file

    async def update_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        request: CodingFileUpdateRequest,
        db: AsyncSession,
    ) -> CodingFile:
        """Updates file content, path, or active state."""
        result = await db.execute(select(CodingFile).where(CodingFile.id == file_id))
        file = result.scalar_one_or_none()
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        coding_session = await self.get_coding_session_or_404(file.coding_session_id, db)
        if coding_session.is_editor_locked and not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editor is currently locked by the interviewer",
            )

        if request.path is not None:
            file.path = self.validate_safe_path(request.path)
        if request.name is not None:
            file.name = request.name
        if request.content is not None:
            file.content = request.content
        if request.is_active is not None:
            file.is_active = request.is_active
        file.updated_at = datetime.now(timezone.utc)

        sess = await session_service.get_session(coding_session.interview_session_id, db)
        await session_service.log_event(
            session=sess,
            event_type="CODE_FILE_UPDATED",
            actor_id=user_id,
            actor_role="interviewer" if is_interviewer else "candidate",
            payload={"file_id": str(file.id), "path": file.path},
            db=db,
        )

        await db.commit()
        await db.refresh(file)
        return file

    async def delete_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> None:
        """Deletes a file from the workspace."""
        result = await db.execute(select(CodingFile).where(CodingFile.id == file_id))
        file = result.scalar_one_or_none()
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        coding_session = await self.get_coding_session_or_404(file.coding_session_id, db)
        if coding_session.is_editor_locked and not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editor is currently locked by the interviewer",
            )

        sess = await session_service.get_session(coding_session.interview_session_id, db)
        await session_service.log_event(
            session=sess,
            event_type="CODE_FILE_DELETED",
            actor_id=user_id,
            actor_role="interviewer" if is_interviewer else "candidate",
            payload={"file_id": str(file.id), "path": file.path},
            db=db,
        )

        await db.delete(file)
        await db.commit()

    async def create_snapshot(
        self,
        coding_session: CodingSession,
        user_id: Optional[uuid.UUID],
        reason: str,
        files_data: List[Dict[str, Any]],
        db: AsyncSession,
    ) -> CodingSnapshot:
        """Persists an immutable snapshot of all files in the coding workspace."""
        snapshot = CodingSnapshot(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            created_by=user_id,
            reason=CodingSnapshotReason(reason),
            files_json=files_data,
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        return snapshot

    async def create_execution_job(
        self,
        coding_session_id: uuid.UUID,
        user_id: uuid.UUID,
        is_interviewer: bool,
        request: CodingExecutionRequest,
        db: AsyncSession,
    ) -> CodingExecutionJob:
        """Creates an execution job, creates an immutable snapshot, and runs the sandbox."""
        coding_session = await self.get_coding_session_or_404(coding_session_id, db)
        sess = await session_service.get_session(coding_session.interview_session_id, db)

        if sess.status in (SessionStatus.COMPLETED, SessionStatus.CANCELLED, SessionStatus.EXPIRED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code execution is disabled because session is {sess.status.value}",
            )

        # 1. Resolve files to execute
        if request.files and len(request.files) > 0:
            files_to_run = request.files
        else:
            files_to_run = [
                {"path": f.path, "name": f.name, "language": f.language, "content": f.content}
                for f in coding_session.files
            ]

        if not files_to_run:
            files_to_run = [{"path": "main.py", "name": "main.py", "language": request.language, "content": DEFAULT_PYTHON_STARTER}]

        # 2. Create immutable snapshot before execution
        snapshot_reason = "submission" if request.is_submission else "before_execution"
        snapshot = await self.create_snapshot(
            coding_session=coding_session,
            user_id=user_id,
            reason=snapshot_reason,
            files_data=files_to_run,
            db=db,
        )

        # 3. Create execution job
        job = CodingExecutionJob(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            requested_by=user_id,
            snapshot_id=snapshot.id,
            status=ExecutionJobStatus.QUEUED,
            language=request.language or coding_session.language,
            is_submission=request.is_submission,
            custom_input=request.custom_input,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        # 4. Resolve test cases
        test_cases_data = []
        if not request.custom_input and coding_session.test_cases:
            test_cases_data = [
                {
                    "id": str(tc.id),
                    "title": tc.title,
                    "input_data": tc.input_data,
                    "expected_output": tc.expected_output,
                    "is_hidden": tc.is_hidden,
                    "timeout_seconds": tc.timeout_seconds,
                }
                for tc in coding_session.test_cases
            ]

        # 5. Run sandbox executor
        exec_status = "passed"
        raw_res = None
        if sandbox_executor is not None:
            raw_res = sandbox_executor.execute(
                execution_id=str(job.id),
                session_id=str(coding_session.id),
                language_id=job.language,
                files=files_to_run,
                test_cases=test_cases_data if test_cases_data else None,
                custom_input=request.custom_input,
            )
            exec_status = raw_res.status

        # 6. Persist execution result
        result = CodingExecutionResult(
            id=uuid.uuid4(),
            execution_job_id=job.id,
            status=ExecutionResultStatus(exec_status),
            exit_code=raw_res.exit_code if raw_res else 0,
            stdout=raw_res.stdout if raw_res else "Execution simulated",
            stderr=raw_res.stderr if raw_res else "",
            compile_output=raw_res.compile_output if raw_res else None,
            duration_ms=raw_res.duration_ms if raw_res else 100,
            memory_bytes=raw_res.memory_bytes if raw_res else 0,
            tests_passed=raw_res.tests_passed if raw_res else (1 if exec_status == "passed" else 0),
            tests_failed=raw_res.tests_failed if raw_res else (0 if exec_status == "passed" else 1),
            test_results_json=raw_res.test_results if raw_res else [],
        )
        db.add(result)

        job.status = ExecutionJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)

        # 7. Log monotonic event
        event_type = "CODE_EXECUTION_COMPLETED" if exec_status == "passed" else "CODE_EXECUTION_FAILED"
        await session_service.log_event(
            session=sess,
            event_type=event_type,
            actor_id=user_id,
            actor_role="interviewer" if is_interviewer else "candidate",
            payload={
                "job_id": str(job.id),
                "status": exec_status,
                "is_submission": job.is_submission,
                "tests_passed": result.tests_passed,
                "tests_failed": result.tests_failed,
            },
            db=db,
        )

        await db.commit()

        # Re-fetch job with result
        job_res = await db.execute(
            select(CodingExecutionJob)
            .options(selectinload(CodingExecutionJob.result))
            .where(CodingExecutionJob.id == job.id)
        )
        return job_res.scalar_one()

    def sanitize_execution_result_for_candidate(
        self, result: CodingExecutionResult, is_interviewer: bool
    ) -> List[TestResultItem]:
        """Ensures hidden test case inputs and expected outputs are NEVER leaked to candidates."""
        sanitized = []
        for item in result.test_results_json:
            is_hidden = item.get("is_hidden", False)
            if is_hidden and not is_interviewer:
                # Mask hidden test details
                sanitized.append(
                    TestResultItem(
                        test_id=item.get("test_id"),
                        title="Hidden Test Case",
                        passed=item.get("passed", False),
                        duration_ms=item.get("duration_ms"),
                        error="Test failed" if not item.get("passed", False) else None,
                        stdout="[Hidden Test Output]" if not item.get("passed", False) else None,
                        is_hidden=True,
                    )
                )
            else:
                sanitized.append(
                    TestResultItem(
                        test_id=item.get("test_id"),
                        title=item.get("title", "Test"),
                        passed=item.get("passed", False),
                        duration_ms=item.get("duration_ms"),
                        error=item.get("error"),
                        stdout=item.get("stdout"),
                        is_hidden=is_hidden,
                    )
                )
        return sanitized


coding_service = CodingService()
