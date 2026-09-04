import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_current_user, get_db
from app.models.coding import CodingProblem, CodingProblemVersion, CodingTestCase
from app.models.user import User, UserRole
from app.schemas.problem import (
    AssessmentSummaryResponse,
    PaginatedProblemsResponse,
    ProblemAssignRequest,
    ProblemCloneRequest,
    ProblemCreateRequest,
    ProblemDetailResponse,
    ProblemSubmitRequest,
    ProblemSummaryResponse,
    ProblemUpdateRequest,
    ProblemVersionResponse,
    SessionProblemResponse,
    SubmissionResponse,
    TestCaseCreateRequest,
    TestCaseResponse,
    TestCaseUpdateRequest,
)
from app.services.assessment_service import assessment_service
from app.services.problem_service import problem_service

router = APIRouter(tags=["coding-problems"])


# ---------------------------------------------------------------------------
# 1. Problem Library CRUD
# ---------------------------------------------------------------------------

@router.get("/coding/problems", response_model=PaginatedProblemsResponse)
async def list_problems(
    workspace_id: Optional[uuid.UUID] = None,
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    scope: Optional[str] = Query(None, description="'system', 'workspace', or None"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists coding problems in library with search and tenant isolation filtering."""
    items, total = await problem_service.list_problems(
        workspace_id=workspace_id,
        difficulty=difficulty,
        category=category,
        tag=tag,
        scope=scope,
        search=search,
        page=page,
        page_size=page_size,
        user=current_user,
        db=db,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedProblemsResponse(
        items=[
            ProblemSummaryResponse(
                id=p.id,
                workspace_id=p.workspace_id,
                created_by=p.created_by,
                title=p.title,
                slug=p.slug,
                short_description=p.short_description,
                difficulty=p.difficulty.value,
                category=p.category,
                status=p.status.value,
                estimated_duration_minutes=p.estimated_duration_minutes,
                default_time_limit_seconds=p.default_time_limit_seconds,
                default_memory_limit_mb=p.default_memory_limit_mb,
                tags=p.tags or [],
                is_system=p.is_system,
                current_version_id=p.current_version_id,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/coding/problems", response_model=ProblemDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    request: ProblemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new coding problem with initial immutable version and test cases."""
    problem = await problem_service.create_problem(request, current_user, db)
    return await problem_service.get_problem_detail(problem.id, current_user, db)


@router.get("/coding/problems/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem(
    problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches full problem details with candidate hidden-test sanitization."""
    return await problem_service.get_problem_detail(problem_id, current_user, db)


@router.patch("/coding/problems/{problem_id}", response_model=ProblemDetailResponse)
async def update_problem(
    problem_id: uuid.UUID,
    request: ProblemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates problem metadata and generates a new problem version on assessment content changes."""
    await problem_service.update_problem(problem_id, request, current_user, db)
    return await problem_service.get_problem_detail(problem_id, current_user, db)


@router.post("/coding/problems/{problem_id}/clone", response_model=ProblemDetailResponse, status_code=status.HTTP_201_CREATED)
async def clone_problem(
    problem_id: uuid.UUID,
    request: ProblemCloneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates an independent copy of a problem and its test cases into a workspace."""
    cloned = await problem_service.clone_problem(problem_id, request, current_user, db)
    return await problem_service.get_problem_detail(cloned.id, current_user, db)


@router.post("/coding/problems/{problem_id}/archive", response_model=ProblemSummaryResponse)
async def archive_problem(
    problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-archives a problem so historical interviews remain reproducible."""
    archived = await problem_service.archive_problem(problem_id, current_user, db)
    return ProblemSummaryResponse(
        id=archived.id,
        workspace_id=archived.workspace_id,
        created_by=archived.created_by,
        title=archived.title,
        slug=archived.slug,
        short_description=archived.short_description,
        difficulty=archived.difficulty.value,
        category=archived.category,
        status=archived.status.value,
        estimated_duration_minutes=archived.estimated_duration_minutes,
        default_time_limit_seconds=archived.default_time_limit_seconds,
        default_memory_limit_mb=archived.default_memory_limit_mb,
        tags=archived.tags or [],
        is_system=archived.is_system,
        current_version_id=archived.current_version_id,
        created_at=archived.created_at,
        updated_at=archived.updated_at,
    )


# ---------------------------------------------------------------------------
# 2. Problem Test Cases Management
# ---------------------------------------------------------------------------

@router.post("/coding/problem-versions/{version_id}/tests", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def add_test_case_to_version(
    version_id: uuid.UUID,
    request: TestCaseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Adds a test case to a problem version."""
    if current_user.role == UserRole.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidates cannot create test cases")

    res = await db.execute(select(CodingProblemVersion).where(CodingProblemVersion.id == version_id))
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem version not found")

    tc = CodingTestCase(
        id=uuid.uuid4(),
        problem_version_id=version.id,
        coding_session_id=None,
        title=request.title,
        input_data=request.input_data or "",
        expected_output=request.expected_output or "",
        explanation=request.explanation or "",
        is_hidden=request.is_hidden,
        weight=request.weight,
        order=request.order,
        timeout_seconds=request.timeout_seconds,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)

    return TestCaseResponse(
        id=tc.id,
        problem_version_id=tc.problem_version_id,
        title=tc.title,
        input_data=tc.input_data,
        expected_output=tc.expected_output,
        explanation=tc.explanation,
        is_hidden=tc.is_hidden,
        weight=tc.weight,
        order=tc.order,
        timeout_seconds=tc.timeout_seconds,
    )


# ---------------------------------------------------------------------------
# 3. Session Problem Assignment & Submissions
# ---------------------------------------------------------------------------

@router.post("/coding/sessions/{session_id}/problems/assign", response_model=SessionProblemResponse)
async def assign_problem_to_session(
    session_id: uuid.UUID,
    request: ProblemAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Interviewer assigns a problem version to an active coding session."""
    is_interviewer = current_user.role in (UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_ADMIN, UserRole.RECRUITER)
    return await assessment_service.assign_problem_to_session(session_id, request, current_user, is_interviewer, db)


@router.post("/coding/sessions/{session_id}/problems/submit", response_model=SubmissionResponse)
async def submit_problem_solution(
    session_id: uuid.UUID,
    request: ProblemSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submits candidate code, runs Docker sandbox on public + hidden tests, and scores attempt."""
    is_interviewer = current_user.role in (UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_ADMIN, UserRole.RECRUITER)
    return await assessment_service.submit_solution(session_id, request, current_user, is_interviewer, db)


@router.get("/coding/sessions/{session_id}/problems/submissions", response_model=List[SubmissionResponse])
async def get_problem_submissions(
    session_id: uuid.UUID,
    problem_version_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gets attempt history for the active session problem with hidden test sanitization."""
    is_interviewer = current_user.role in (UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_ADMIN, UserRole.RECRUITER)
    return await assessment_service.get_submission_history(session_id, problem_version_id, current_user, is_interviewer, db)


@router.get("/coding/sessions/{session_id}/problems/{version_id}/assessment", response_model=Optional[AssessmentSummaryResponse])
async def get_problem_assessment(
    session_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gets consolidated score summary for a problem assessment."""
    is_interviewer = current_user.role in (UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_ADMIN, UserRole.RECRUITER)
    return await assessment_service.get_assessment_summary(session_id, version_id, current_user, is_interviewer, db)
