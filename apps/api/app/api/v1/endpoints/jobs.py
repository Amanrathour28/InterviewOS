import math
import re
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    verify_job_access,
    verify_workspace_access,
)
from app.models.candidate import Candidate, CandidateActivity, JobCandidate
from app.models.job import EmploymentType, Job, JobPriority, JobStatus
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.schemas.candidate import JobApplicationCreate, JobApplicationResponse, JobApplicationUpdate
from app.schemas.job import JobCreate, JobResponse, JobUpdate, PaginatedJobsResponse

router = APIRouter()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


@router.get(
    "",
    response_model=PaginatedJobsResponse,
    summary="List and search jobs in a workspace with pagination",
)
async def list_jobs(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Strict Tenant Isolation: verify membership in requested workspace
    await verify_workspace_access(workspace_id, current_user, db)

    query = select(Job).where(Job.workspace_id == workspace_id, Job.is_deleted.is_(False))

    if status_filter:
        query = query.where(Job.status == status_filter)
    if department:
        query = query.where(Job.department.ilike(f"%{department.strip()}%"))
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            (Job.title.ilike(search_pattern))
            | (Job.description.ilike(search_pattern))
            | (Job.department.ilike(search_pattern))
            | (Job.location.ilike(search_pattern))
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    query = (
        query.order_by(Job.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(selectinload(Job.candidate_applications))
    )
    res = await db.execute(query)
    jobs = res.scalars().all()

    items = [
        JobResponse(
            id=job.id,
            workspace_id=job.workspace_id,
            title=job.title,
            slug=job.slug,
            description=job.description,
            department=job.department,
            location=job.location,
            employment_type=job.employment_type,
            experience_min=job.experience_min,
            experience_max=job.experience_max,
            status=job.status,
            priority=job.priority,
            required_skills=job.required_skills or [],
            preferred_skills=job.preferred_skills or [],
            responsibilities=job.responsibilities or [],
            requirements=job.requirements or [],
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            currency=job.currency,
            is_active=job.is_active,
            created_at=job.created_at,
            updated_at=job.updated_at,
            candidate_count=len(job.candidate_applications),
        )
        for job in jobs
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedJobsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job requisition in a workspace",
)
async def create_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # RBAC: Workspace Admin or Recruiter can create jobs
    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating jobs requires Admin or Recruiter workspace permissions",
        )

    base_slug = payload.slug or _slugify(payload.title)
    if not base_slug:
        base_slug = f"job-{uuid.uuid4().hex[:8]}"

    # Uniqueness within workspace
    candidate_slug = base_slug
    suffix = 1
    while True:
        check = await db.execute(
            select(Job).where(
                Job.workspace_id == payload.workspace_id,
                Job.slug == candidate_slug,
                Job.is_deleted.is_(False),
            )
        )
        if not check.scalar_one_or_none():
            break
        candidate_slug = f"{base_slug}-{suffix}"
        suffix += 1

    new_job = Job(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        title=payload.title.strip(),
        slug=candidate_slug,
        description=payload.description or "",
        department=payload.department.strip() if payload.department else None,
        location=payload.location.strip() if payload.location else None,
        employment_type=payload.employment_type,
        experience_min=payload.experience_min,
        experience_max=payload.experience_max,
        status=payload.status,
        priority=payload.priority,
        required_skills=payload.required_skills or [],
        preferred_skills=payload.preferred_skills or [],
        responsibilities=payload.responsibilities or [],
        requirements=payload.requirements or [],
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        currency=payload.currency or "USD",
        is_active=True,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    return JobResponse(
        id=new_job.id,
        workspace_id=new_job.workspace_id,
        title=new_job.title,
        slug=new_job.slug,
        description=new_job.description,
        department=new_job.department,
        location=new_job.location,
        employment_type=new_job.employment_type,
        experience_min=new_job.experience_min,
        experience_max=new_job.experience_max,
        status=new_job.status,
        priority=new_job.priority,
        required_skills=new_job.required_skills or [],
        preferred_skills=new_job.preferred_skills or [],
        responsibilities=new_job.responsibilities or [],
        requirements=new_job.requirements or [],
        salary_min=new_job.salary_min,
        salary_max=new_job.salary_max,
        currency=new_job.currency,
        is_active=new_job.is_active,
        created_at=new_job.created_at,
        updated_at=new_job.updated_at,
        candidate_count=0,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get single job details",
)
async def get_job(
    job: Job = Depends(verify_job_access),
    db: AsyncSession = Depends(get_db),
):
    count_stmt = select(func.count(JobCandidate.id)).where(JobCandidate.job_id == job.id)
    count_res = await db.execute(count_stmt)
    candidate_count = count_res.scalar_one()

    return JobResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        title=job.title,
        slug=job.slug,
        description=job.description,
        department=job.department,
        location=job.location,
        employment_type=job.employment_type,
        experience_min=job.experience_min,
        experience_max=job.experience_max,
        status=job.status,
        priority=job.priority,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        responsibilities=job.responsibilities or [],
        requirements=job.requirements or [],
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        currency=job.currency,
        is_active=job.is_active,
        created_at=job.created_at,
        updated_at=job.updated_at,
        candidate_count=candidate_count,
    )


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update job requisition",
)
async def update_job(
    payload: JobUpdate,
    job: Job = Depends(verify_job_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # RBAC: Workspace Admin or Recruiter can edit jobs
    ws_membership = await verify_workspace_access(job.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Updating jobs requires Admin or Recruiter workspace permissions",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)

    count_stmt = select(func.count(JobCandidate.id)).where(JobCandidate.job_id == job.id)
    candidate_count = (await db.execute(count_stmt)).scalar_one()

    return JobResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        title=job.title,
        slug=job.slug,
        description=job.description,
        department=job.department,
        location=job.location,
        employment_type=job.employment_type,
        experience_min=job.experience_min,
        experience_max=job.experience_max,
        status=job.status,
        priority=job.priority,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        responsibilities=job.responsibilities or [],
        requirements=job.requirements or [],
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        currency=job.currency,
        is_active=job.is_active,
        created_at=job.created_at,
        updated_at=job.updated_at,
        candidate_count=candidate_count,
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete a job requisition",
)
async def delete_job(
    job: Job = Depends(verify_job_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(job.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")

    job.is_deleted = True
    job.status = JobStatus.ARCHIVED
    await db.commit()


# --- JOB ↔ CANDIDATE RELATIONSHIP ENDPOINTS ---

@router.get(
    "/{job_id}/candidates",
    response_model=List[JobApplicationResponse],
    summary="List all candidates applied to a job",
)
async def get_job_candidates(
    job: Job = Depends(verify_job_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(JobCandidate)
        .where(JobCandidate.job_id == job.id)
        .options(selectinload(JobCandidate.candidate))
        .order_by(JobCandidate.applied_at.desc())
    )
    res = await db.execute(stmt)
    apps = res.scalars().all()

    return [
        JobApplicationResponse(
            id=app.id,
            job_id=app.job_id,
            job_title=job.title,
            job_department=job.department,
            candidate_id=app.candidate_id,
            status=app.status,
            source=app.source,
            applied_at=app.applied_at,
            last_activity_at=app.last_activity_at,
        )
        for app in apps
    ]


@router.post(
    "/{job_id}/candidates",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign candidate to job",
)
async def assign_candidate_to_job(
    payload: JobApplicationCreate,
    job: Job = Depends(verify_job_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify candidate belongs to the same workspace
    cand_stmt = select(Candidate).where(
        Candidate.id == payload.candidate_id,
        Candidate.workspace_id == job.workspace_id,
        Candidate.is_deleted.is_(False),
    )
    cand_res = await db.execute(cand_stmt)
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found in this workspace",
        )

    # Check for existing application
    existing = await db.execute(
        select(JobCandidate).where(
            JobCandidate.job_id == job.id,
            JobCandidate.candidate_id == candidate.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate has already been assigned to this job",
        )

    new_app = JobCandidate(
        job_id=job.id,
        candidate_id=candidate.id,
        status=payload.status,
        source=payload.source,
    )
    db.add(new_app)

    # Record Activity Timeline
    activity = CandidateActivity(
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="candidate_assigned_to_job",
        details={"job_id": str(job.id), "job_title": job.title, "status": payload.status.value},
    )
    db.add(activity)
    await db.commit()
    await db.refresh(new_app)

    return JobApplicationResponse(
        id=new_app.id,
        job_id=new_app.job_id,
        job_title=job.title,
        job_department=job.department,
        candidate_id=new_app.candidate_id,
        status=new_app.status,
        source=new_app.source,
        applied_at=new_app.applied_at,
        last_activity_at=new_app.last_activity_at,
    )


@router.patch(
    "/{job_id}/candidates/{candidate_id}",
    response_model=JobApplicationResponse,
    summary="Update candidate pipeline status for a job",
)
async def update_job_candidate_status(
    candidate_id: uuid.UUID,
    payload: JobApplicationUpdate,
    job: Job = Depends(verify_job_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(JobCandidate).where(
        JobCandidate.job_id == job.id,
        JobCandidate.candidate_id == candidate_id,
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    old_status = app.status
    app.status = payload.status

    # Record activity
    activity = CandidateActivity(
        candidate_id=candidate_id,
        actor_id=current_user.id,
        event_type="candidate_status_changed",
        details={
            "job_id": str(job.id),
            "job_title": job.title,
            "old_status": old_status.value,
            "new_status": payload.status.value,
        },
    )
    db.add(activity)
    await db.commit()
    await db.refresh(app)

    return JobApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        job_title=job.title,
        job_department=job.department,
        candidate_id=app.candidate_id,
        status=app.status,
        source=app.source,
        applied_at=app.applied_at,
        last_activity_at=app.last_activity_at,
    )


@router.delete(
    "/{job_id}/candidates/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove candidate from job application pipeline",
)
async def remove_candidate_from_job(
    candidate_id: uuid.UUID,
    job: Job = Depends(verify_job_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(JobCandidate).where(
        JobCandidate.job_id == job.id,
        JobCandidate.candidate_id == candidate_id,
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    await db.delete(app)

    activity = CandidateActivity(
        candidate_id=candidate_id,
        actor_id=current_user.id,
        event_type="candidate_removed_from_job",
        details={"job_id": str(job.id), "job_title": job.title},
    )
    db.add(activity)
    await db.commit()
