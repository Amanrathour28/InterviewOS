import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.endpoints.sessions import check_session_permission
from app.models.user import User
from app.schemas.coding import (
    CodingExecutionJobResponse,
    CodingExecutionRequest,
    CodingExecutionResultResponse,
    CodingFileCreateRequest,
    CodingFileResponse,
    CodingFileUpdateRequest,
    CodingSessionResponse,
    CodingSnapshotCreateRequest,
    CodingSnapshotResponse,
    EditorLockRequest,
)
from app.services.coding_service import coding_service
from app.services.session_service import session_service

router = APIRouter()


@router.get("/sessions/{session_id}/coding", response_model=CodingSessionResponse)
async def get_or_create_session_coding(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves or initializes the collaborative coding session attached to an interview session."""
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    coding_session = await coding_service.get_or_create_coding_session(
        interview_session=session,
        user_id=current_user.id,
        db=db,
    )

    return CodingSessionResponse(
        id=coding_session.id,
        interview_session_id=coding_session.interview_session_id,
        workspace_id=coding_session.workspace_id,
        problem_id=coding_session.problem_id,
        language=coding_session.language,
        active_file_id=coding_session.active_file_id,
        status=coding_session.status.value,
        is_editor_locked=coding_session.is_editor_locked,
        settings=coding_session.settings_json or {},
        files=[
            CodingFileResponse(
                id=f.id,
                coding_session_id=f.coding_session_id,
                path=f.path,
                name=f.name,
                language=f.language,
                content=f.content,
                is_active=f.is_active,
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
            for f in coding_session.files
        ],
        created_at=coding_session.created_at,
        updated_at=coding_session.updated_at,
    )


@router.get("/coding/sessions/{coding_session_id}", response_model=CodingSessionResponse)
async def get_coding_session_detail(
    coding_session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches full coding session metadata, files, and settings."""
    coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    return CodingSessionResponse(
        id=coding_session.id,
        interview_session_id=coding_session.interview_session_id,
        workspace_id=coding_session.workspace_id,
        problem_id=coding_session.problem_id,
        language=coding_session.language,
        active_file_id=coding_session.active_file_id,
        status=coding_session.status.value,
        is_editor_locked=coding_session.is_editor_locked,
        settings=coding_session.settings_json or {},
        files=[
            CodingFileResponse(
                id=f.id,
                coding_session_id=f.coding_session_id,
                path=f.path,
                name=f.name,
                language=f.language,
                content=f.content,
                is_active=f.is_active,
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
            for f in coding_session.files
        ],
        created_at=coding_session.created_at,
        updated_at=coding_session.updated_at,
    )


@router.post("/coding/sessions/{coding_session_id}/lock", response_model=CodingSessionResponse)
async def set_coding_editor_lock(
    coding_session_id: uuid.UUID,
    request: EditorLockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sets editor lock state. (Interviewer only)."""
    coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    updated = await coding_service.set_editor_lock(
        coding_session_id=coding_session_id,
        is_locked=request.is_locked,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        db=db,
    )

    return CodingSessionResponse(
        id=updated.id,
        interview_session_id=updated.interview_session_id,
        workspace_id=updated.workspace_id,
        problem_id=updated.problem_id,
        language=updated.language,
        active_file_id=updated.active_file_id,
        status=updated.status.value,
        is_editor_locked=updated.is_editor_locked,
        settings=updated.settings_json or {},
        files=[
            CodingFileResponse(
                id=f.id,
                coding_session_id=f.coding_session_id,
                path=f.path,
                name=f.name,
                language=f.language,
                content=f.content,
                is_active=f.is_active,
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
            for f in updated.files
        ],
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.post("/coding/sessions/{coding_session_id}/files", response_model=CodingFileResponse)
async def create_workspace_file(
    coding_session_id: uuid.UUID,
    request: CodingFileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new file in the workspace."""
    coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    file = await coding_service.create_file(
        coding_session_id=coding_session_id,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        request=request,
        db=db,
    )

    return CodingFileResponse(
        id=file.id,
        coding_session_id=file.coding_session_id,
        path=file.path,
        name=file.name,
        language=file.language,
        content=file.content,
        is_active=file.is_active,
        created_at=file.created_at,
        updated_at=file.updated_at,
    )


@router.patch("/coding/files/{file_id}", response_model=CodingFileResponse)
async def update_workspace_file(
    file_id: uuid.UUID,
    request: CodingFileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates file content, path, or active tab state."""
    from sqlalchemy import select
    from app.models.coding import CodingFile
    res = await db.execute(select(CodingFile).where(CodingFile.id == file_id))
    file = res.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    coding_session = await coding_service.get_coding_session_or_404(file.coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    updated = await coding_service.update_file(
        file_id=file_id,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        request=request,
        db=db,
    )

    return CodingFileResponse(
        id=updated.id,
        coding_session_id=updated.coding_session_id,
        path=updated.path,
        name=updated.name,
        language=updated.language,
        content=updated.content,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/coding/files/{file_id}")
async def delete_workspace_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a file from the workspace."""
    from sqlalchemy import select
    from app.models.coding import CodingFile
    res = await db.execute(select(CodingFile).where(CodingFile.id == file_id))
    file = res.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    coding_session = await coding_service.get_coding_session_or_404(file.coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    await coding_service.delete_file(
        file_id=file_id,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        db=db,
    )
    return {"message": "File deleted successfully"}


@router.post("/coding/sessions/{coding_session_id}/snapshots", response_model=CodingSnapshotResponse)
async def create_workspace_snapshot(
    coding_session_id: uuid.UUID,
    request: CodingSnapshotCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Takes an immutable snapshot of all files in the workspace."""
    coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    snapshot = await coding_service.create_snapshot(
        coding_session=coding_session,
        user_id=current_user.id,
        reason=request.reason,
        files_data=request.files,
        db=db,
    )

    return CodingSnapshotResponse(
        id=snapshot.id,
        coding_session_id=snapshot.coding_session_id,
        created_by=snapshot.created_by,
        reason=snapshot.reason.value,
        files=snapshot.files_json or [],
        created_at=snapshot.created_at,
    )


@router.get("/coding/sessions/{coding_session_id}/snapshots", response_model=List[CodingSnapshotResponse])
async def list_workspace_snapshots(
    coding_session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists past immutable snapshots in the workspace."""
    coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    return [
        CodingSnapshotResponse(
            id=s.id,
            coding_session_id=s.coding_session_id,
            created_by=s.created_by,
            reason=s.reason.value,
            files=s.files_json or [],
            created_at=s.created_at,
        )
        for s in coding_session.snapshots
    ]


@router.post("/coding/sessions/{coding_session_id}/execute", response_model=CodingExecutionJobResponse)
async def execute_workspace_code(
    coding_session_id: uuid.UUID,
    request: CodingExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Runs untrusted code inside the isolated Docker sandbox."""
    coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    job = await coding_service.create_execution_job(
        coding_session_id=coding_session_id,
        user_id=current_user.id,
        is_interviewer=is_interviewer,
        request=request,
        db=db,
    )

    result_res = None
    if job.result:
        sanitized_tests = coding_service.sanitize_execution_result_for_candidate(job.result, is_interviewer)
        result_res = CodingExecutionResultResponse(
            id=job.result.id,
            execution_job_id=job.result.execution_job_id,
            status=job.result.status.value,
            exit_code=job.result.exit_code,
            stdout=job.result.stdout,
            stderr=job.result.stderr,
            compile_output=job.result.compile_output,
            duration_ms=job.result.duration_ms,
            memory_bytes=job.result.memory_bytes,
            tests_passed=job.result.tests_passed,
            tests_failed=job.result.tests_failed,
            test_results=sanitized_tests,
            created_at=job.result.created_at,
        )

    return CodingExecutionJobResponse(
        id=job.id,
        coding_session_id=job.coding_session_id,
        requested_by=job.requested_by,
        snapshot_id=job.snapshot_id,
        status=job.status.value,
        language=job.language,
        is_submission=job.is_submission,
        custom_input=job.custom_input,
        result=result_res,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/coding/executions/{job_id}", response_model=CodingExecutionJobResponse)
async def get_execution_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves execution status and sanitized test results."""
    from sqlalchemy import select
    from app.models.coding import CodingExecutionJob
    job_res = await db.execute(
        select(CodingExecutionJob)
        .options(selectinload(CodingExecutionJob.result))
        .where(CodingExecutionJob.id == job_id)
    )
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution job not found")

    coding_session = await coding_service.get_coding_session_or_404(job.coding_session_id, db)
    session = await session_service.get_session(coding_session.interview_session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    result_res = None
    if job.result:
        sanitized_tests = coding_service.sanitize_execution_result_for_candidate(job.result, is_interviewer)
        result_res = CodingExecutionResultResponse(
            id=job.result.id,
            execution_job_id=job.result.execution_job_id,
            status=job.result.status.value,
            exit_code=job.result.exit_code,
            stdout=job.result.stdout,
            stderr=job.result.stderr,
            compile_output=job.result.compile_output,
            duration_ms=job.result.duration_ms,
            memory_bytes=job.result.memory_bytes,
            tests_passed=job.result.tests_passed,
            tests_failed=job.result.tests_failed,
            test_results=sanitized_tests,
            created_at=job.result.created_at,
        )

    return CodingExecutionJobResponse(
        id=job.id,
        coding_session_id=job.coding_session_id,
        requested_by=job.requested_by,
        snapshot_id=job.snapshot_id,
        status=job.status.value,
        language=job.language,
        is_submission=job.is_submission,
        custom_input=job.custom_input,
        result=result_res,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
