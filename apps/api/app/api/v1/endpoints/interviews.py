import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    verify_interview_access,
    verify_workspace_access,
)
from app.models.candidate import Candidate
from app.models.interview import (
    Interview,
    InterviewDifficulty,
    InterviewParticipant,
    InterviewRound,
    InterviewRoundQuestion,
    InterviewStatus,
    InterviewType,
    Question,
)
from app.models.job import Job
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole, WorkspaceMembership
from app.schemas.interview import (
    InterviewCreate,
    InterviewDetailResponse,
    InterviewFromTemplateCreate,
    InterviewReadinessResponse,
    InterviewResponse,
    InterviewUpdate,
    PaginatedInterviewsResponse,
    ParticipantCreate,
    ParticipantResponse,
    QuestionResponse,
    ReorderRequest,
    RoundCreate,
    RoundQuestionCreate,
    RoundQuestionResponse,
    RoundResponse,
    RoundUpdate,
)
from app.services.interview_service import interview_service

router = APIRouter()


# --- 1. INTERVIEWS CRUD & LIFECYCLE ---

@router.get(
    "",
    response_model=PaginatedInterviewsResponse,
    summary="List and filter interview sessions in a workspace",
)
async def list_interviews(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    status_filter: Optional[InterviewStatus] = Query(None, alias="status"),
    interview_type: Optional[InterviewType] = Query(None),
    difficulty: Optional[InterviewDifficulty] = Query(None),
    candidate_id: Optional[uuid.UUID] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)

    query = select(Interview).where(
        Interview.workspace_id == workspace_id,
        Interview.is_deleted.is_(False),
    )

    if status_filter:
        query = query.where(Interview.status == status_filter)
    if interview_type:
        query = query.where(Interview.interview_type == interview_type)
    if difficulty:
        query = query.where(Interview.difficulty == difficulty)
    if candidate_id:
        query = query.where(Interview.candidate_id == candidate_id)
    if job_id:
        query = query.where(Interview.job_id == job_id)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Interview.title.ilike(search_pattern),
                Interview.description.ilike(search_pattern),
            )
        )

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    query = (
        query.order_by(Interview.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(Interview.candidate),
            selectinload(Interview.job),
            selectinload(Interview.rounds),
            selectinload(Interview.participants),
        )
    )
    res = await db.execute(query)
    interviews = res.scalars().all()

    items = []
    for itw in interviews:
        is_ready, _ = await interview_service.validate_interview_readiness(itw, db)
        items.append(
            InterviewResponse(
                id=itw.id,
                workspace_id=itw.workspace_id,
                candidate_id=itw.candidate_id,
                candidate_name=f"{itw.candidate.first_name} {itw.candidate.last_name}" if itw.candidate else None,
                candidate_email=itw.candidate.email if itw.candidate else None,
                job_id=itw.job_id,
                job_title=itw.job.title if itw.job else None,
                created_by=itw.created_by,
                template_id=itw.template_id,
                title=itw.title,
                description=itw.description,
                interview_type=itw.interview_type,
                status=itw.status,
                difficulty=itw.difficulty,
                duration_minutes=itw.duration_minutes,
                timezone=itw.timezone,
                instructions=itw.instructions,
                candidate_instructions=itw.candidate_instructions,
                interviewer_instructions=itw.interviewer_instructions,
                round_count=len(itw.rounds),
                participant_count=len(itw.participants),
                is_ready=is_ready,
                created_at=itw.created_at,
                updated_at=itw.updated_at,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedInterviewsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom interview configuration",
)
async def create_interview(
    payload: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating interviews requires Admin or Recruiter workspace permissions",
        )

    # 1. Candidate validation (must belong to same workspace)
    cand_stmt = select(Candidate).where(
        Candidate.id == payload.candidate_id,
        Candidate.workspace_id == payload.workspace_id,
        Candidate.is_deleted.is_(False),
    )
    cand = (await db.execute(cand_stmt)).scalar_one_or_none()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found in this workspace",
        )

    # 2. Job validation (must belong to same workspace if provided)
    job = None
    if payload.job_id:
        job_stmt = select(Job).where(
            Job.id == payload.job_id,
            Job.workspace_id == payload.workspace_id,
            Job.is_deleted.is_(False),
        )
        job = (await db.execute(job_stmt)).scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found in this workspace",
            )

    new_interview = Interview(
        workspace_id=payload.workspace_id,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        created_by=current_user.id,
        template_id=payload.template_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        interview_type=payload.interview_type,
        status=InterviewStatus.DRAFT,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        timezone=payload.timezone,
        instructions=payload.instructions,
        candidate_instructions=payload.candidate_instructions,
        interviewer_instructions=payload.interviewer_instructions,
    )
    db.add(new_interview)
    await db.flush()

    # Add initial rounds if provided
    round_count = 0
    if payload.initial_rounds:
        for r in payload.initial_rounds:
            new_round = InterviewRound(
                interview_id=new_interview.id,
                name=r.name.strip(),
                description=r.description,
                round_type=r.round_type,
                sequence=r.sequence,
                duration_minutes=r.duration_minutes,
                difficulty=r.difficulty,
                instructions=r.instructions,
                is_required=r.is_required,
                configuration=r.configuration or {},
            )
            db.add(new_round)
            round_count += 1

    await db.commit()
    await db.refresh(new_interview)

    return InterviewResponse(
        id=new_interview.id,
        workspace_id=new_interview.workspace_id,
        candidate_id=new_interview.candidate_id,
        candidate_name=f"{cand.first_name} {cand.last_name}",
        candidate_email=cand.email,
        job_id=new_interview.job_id,
        job_title=job.title if job else None,
        created_by=new_interview.created_by,
        template_id=new_interview.template_id,
        title=new_interview.title,
        description=new_interview.description,
        interview_type=new_interview.interview_type,
        status=new_interview.status,
        difficulty=new_interview.difficulty,
        duration_minutes=new_interview.duration_minutes,
        timezone=new_interview.timezone,
        instructions=new_interview.instructions,
        candidate_instructions=new_interview.candidate_instructions,
        interviewer_instructions=new_interview.interviewer_instructions,
        round_count=round_count,
        participant_count=0,
        is_ready=False,
        created_at=new_interview.created_at,
        updated_at=new_interview.updated_at,
    )


@router.post(
    "/from-template/{template_id}",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Instantiate interview from template",
)
async def create_interview_from_template(
    template_id: uuid.UUID,
    payload: InterviewFromTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating interviews requires Admin or Recruiter permissions",
        )

    new_itw = await interview_service.instantiate_interview_from_template(
        template_id=template_id,
        workspace_id=payload.workspace_id,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        title=payload.title,
        created_by=current_user.id,
        db=db,
    )

    # Eager load candidate and job for response
    cand_stmt = select(Candidate).where(Candidate.id == new_itw.candidate_id)
    cand = (await db.execute(cand_stmt)).scalar_one()

    job_title = None
    if new_itw.job_id:
        job_stmt = select(Job).where(Job.id == new_itw.job_id)
        job = (await db.execute(job_stmt)).scalar_one_or_none()
        if job:
            job_title = job.title

    rounds_count_stmt = select(func.count(InterviewRound.id)).where(
        InterviewRound.interview_id == new_itw.id,
        InterviewRound.is_deleted.is_(False),
    )
    round_count = (await db.execute(rounds_count_stmt)).scalar_one()

    return InterviewResponse(
        id=new_itw.id,
        workspace_id=new_itw.workspace_id,
        candidate_id=new_itw.candidate_id,
        candidate_name=f"{cand.first_name} {cand.last_name}",
        candidate_email=cand.email,
        job_id=new_itw.job_id,
        job_title=job_title,
        created_by=new_itw.created_by,
        template_id=new_itw.template_id,
        title=new_itw.title,
        description=new_itw.description,
        interview_type=new_itw.interview_type,
        status=new_itw.status,
        difficulty=new_itw.difficulty,
        duration_minutes=new_itw.duration_minutes,
        timezone=new_itw.timezone,
        instructions=new_itw.instructions,
        candidate_instructions=new_itw.candidate_instructions,
        interviewer_instructions=new_itw.interviewer_instructions,
        round_count=round_count,
        participant_count=0,
        is_ready=False,
        created_at=new_itw.created_at,
        updated_at=new_itw.updated_at,
    )


@router.get(
    "/{interview_id}",
    response_model=InterviewDetailResponse,
    summary="Get full interview configuration, rounds, participants, and readiness status",
)
async def get_interview_detail(
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Interview)
        .where(Interview.id == interview.id)
        .options(
            selectinload(Interview.candidate),
            selectinload(Interview.job),
            selectinload(Interview.rounds).selectinload(InterviewRound.round_questions).selectinload(InterviewRoundQuestion.question),
            selectinload(Interview.participants).selectinload(InterviewParticipant.user),
        )
    )
    res = await db.execute(stmt)
    full_itw = res.scalar_one()

    is_ready, issues = await interview_service.validate_interview_readiness(full_itw, db)

    rounds_out = []
    for r in full_itw.rounds:
        if r.is_deleted:
            continue
        q_out = []
        for rq in r.round_questions:
            q_detail = None
            if rq.question and not rq.question.is_deleted:
                q_detail = QuestionResponse(
                    id=rq.question.id,
                    workspace_id=rq.question.workspace_id,
                    created_by=rq.question.created_by,
                    title=rq.question.title,
                    prompt=rq.question.prompt,
                    question_type=rq.question.question_type,
                    difficulty=rq.question.difficulty,
                    category=rq.question.category,
                    expected_duration_minutes=rq.question.expected_duration_minutes,
                    skills=rq.question.skills or [],
                    topics=rq.question.topics or [],
                    evaluation_criteria=rq.question.evaluation_criteria or [],
                    hints=rq.question.hints or [],
                    reference_answer=rq.question.reference_answer,
                    is_template=rq.question.is_template,
                    created_at=rq.question.created_at,
                    updated_at=rq.question.updated_at,
                )
            q_out.append(
                RoundQuestionResponse(
                    id=rq.id,
                    round_id=rq.round_id,
                    question_id=rq.question_id,
                    sequence=rq.sequence,
                    is_required=rq.is_required,
                    time_limit_seconds=rq.time_limit_seconds,
                    configuration=rq.configuration or {},
                    question=q_detail,
                )
            )

        rounds_out.append(
            RoundResponse(
                id=r.id,
                interview_id=r.interview_id,
                name=r.name,
                description=r.description,
                round_type=r.round_type,
                sequence=r.sequence,
                duration_minutes=r.duration_minutes,
                difficulty=r.difficulty,
                instructions=r.instructions,
                is_required=r.is_required,
                configuration=r.configuration or {},
                created_at=r.created_at,
                updated_at=r.updated_at,
                questions=q_out,
            )
        )

    parts_out = [
        ParticipantResponse(
            id=p.id,
            interview_id=p.interview_id,
            user_id=p.user_id,
            user_name=f"{p.user.first_name} {p.user.last_name}" if p.user else None,
            user_email=p.user.email if p.user else None,
            participant_role=p.participant_role,
            is_primary=p.is_primary,
            created_at=p.created_at,
        )
        for p in full_itw.participants
    ]

    readiness = InterviewReadinessResponse(
        interview_id=full_itw.id,
        is_ready=is_ready,
        current_status=full_itw.status,
        issues=issues,
    )

    return InterviewDetailResponse(
        id=full_itw.id,
        workspace_id=full_itw.workspace_id,
        candidate_id=full_itw.candidate_id,
        candidate_name=f"{full_itw.candidate.first_name} {full_itw.candidate.last_name}" if full_itw.candidate else None,
        candidate_email=full_itw.candidate.email if full_itw.candidate else None,
        job_id=full_itw.job_id,
        job_title=full_itw.job.title if full_itw.job else None,
        created_by=full_itw.created_by,
        template_id=full_itw.template_id,
        title=full_itw.title,
        description=full_itw.description,
        interview_type=full_itw.interview_type,
        status=full_itw.status,
        difficulty=full_itw.difficulty,
        duration_minutes=full_itw.duration_minutes,
        timezone=full_itw.timezone,
        instructions=full_itw.instructions,
        candidate_instructions=full_itw.candidate_instructions,
        interviewer_instructions=full_itw.interviewer_instructions,
        round_count=len(rounds_out),
        participant_count=len(parts_out),
        is_ready=is_ready,
        created_at=full_itw.created_at,
        updated_at=full_itw.updated_at,
        rounds=rounds_out,
        participants=parts_out,
        readiness=readiness,
    )


@router.get(
    "/{interview_id}/readiness",
    response_model=InterviewReadinessResponse,
    summary="Check readiness status and configuration completeness",
)
async def check_readiness(
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    is_ready, issues = await interview_service.validate_interview_readiness(interview, db)
    return InterviewReadinessResponse(
        interview_id=interview.id,
        is_ready=is_ready,
        current_status=interview.status,
        issues=issues,
    )


@router.patch(
    "/{interview_id}",
    response_model=InterviewDetailResponse,
    summary="Update interview configuration and transition status",
)
async def update_interview(
    payload: InterviewUpdate,
    interview: Interview = Depends(verify_interview_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(interview.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Updating interview requires Admin or Recruiter permissions",
        )

    # If status change is requested, enforce state machine
    if payload.status and payload.status != interview.status:
        is_ready, issues = await interview_service.validate_interview_readiness(interview, db)
        interview_service.validate_state_transition(
            current_status=interview.status,
            target_status=payload.status,
            is_ready=is_ready,
            issues=issues,
        )
        interview.status = payload.status

    # If job_id change requested, verify job belongs to workspace
    if payload.job_id is not None:
        if payload.job_id:
            job_stmt = select(Job).where(
                Job.id == payload.job_id,
                Job.workspace_id == interview.workspace_id,
                Job.is_deleted.is_(False),
            )
            if not (await db.execute(job_stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found in this workspace",
                )
        interview.job_id = payload.job_id

    # Apply other fields
    for field, val in payload.model_dump(exclude_unset=True, exclude={"status", "job_id"}).items():
        setattr(interview, field, val)

    await db.commit()
    await db.refresh(interview)
    return await get_interview_detail(interview, db)


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete interview",
)
async def delete_interview(
    interview: Interview = Depends(verify_interview_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(interview.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Recruiter permissions required")

    interview.is_deleted = True
    interview.status = InterviewStatus.CANCELLED
    await db.commit()


# --- 2. ROUNDS MANAGEMENT ---

@router.get(
    "/{interview_id}/rounds",
    response_model=List[RoundResponse],
    summary="List rounds for an interview",
)
async def list_interview_rounds(
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewRound)
        .where(
            InterviewRound.interview_id == interview.id,
            InterviewRound.is_deleted.is_(False),
        )
        .order_by(InterviewRound.sequence.asc())
        .options(
            selectinload(InterviewRound.round_questions).selectinload(InterviewRoundQuestion.question)
        )
    )
    res = await db.execute(stmt)
    rounds = res.scalars().all()

    out = []
    for r in rounds:
        q_out = [
            RoundQuestionResponse(
                id=rq.id,
                round_id=rq.round_id,
                question_id=rq.question_id,
                sequence=rq.sequence,
                is_required=rq.is_required,
                time_limit_seconds=rq.time_limit_seconds,
                configuration=rq.configuration or {},
                question=QuestionResponse(
                    id=rq.question.id,
                    workspace_id=rq.question.workspace_id,
                    created_by=rq.question.created_by,
                    title=rq.question.title,
                    prompt=rq.question.prompt,
                    question_type=rq.question.question_type,
                    difficulty=rq.question.difficulty,
                    category=rq.question.category,
                    expected_duration_minutes=rq.question.expected_duration_minutes,
                    skills=rq.question.skills or [],
                    topics=rq.question.topics or [],
                    evaluation_criteria=rq.question.evaluation_criteria or [],
                    hints=rq.question.hints or [],
                    reference_answer=rq.question.reference_answer,
                    is_template=rq.question.is_template,
                    created_at=rq.question.created_at,
                    updated_at=rq.question.updated_at,
                ) if rq.question and not rq.question.is_deleted else None,
            )
            for rq in r.round_questions
        ]
        out.append(
            RoundResponse(
                id=r.id,
                interview_id=r.interview_id,
                name=r.name,
                description=r.description,
                round_type=r.round_type,
                sequence=r.sequence,
                duration_minutes=r.duration_minutes,
                difficulty=r.difficulty,
                instructions=r.instructions,
                is_required=r.is_required,
                configuration=r.configuration or {},
                created_at=r.created_at,
                updated_at=r.updated_at,
                questions=q_out,
            )
        )
    return out


@router.post(
    "/{interview_id}/rounds",
    response_model=RoundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a round to an interview",
)
async def create_round(
    payload: RoundCreate,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    # Check for sequence collision
    seq_check = await db.execute(
        select(InterviewRound).where(
            InterviewRound.interview_id == interview.id,
            InterviewRound.sequence == payload.sequence,
            InterviewRound.is_deleted.is_(False),
        )
    )
    if seq_check.scalar_one_or_none():
        # Auto bump sequence to max + 1
        max_seq_res = await db.execute(
            select(func.coalesce(func.max(InterviewRound.sequence), 0)).where(
                InterviewRound.interview_id == interview.id,
                InterviewRound.is_deleted.is_(False),
            )
        )
        target_seq = max_seq_res.scalar_one() + 1
    else:
        target_seq = payload.sequence

    new_round = InterviewRound(
        interview_id=interview.id,
        name=payload.name.strip(),
        description=payload.description,
        round_type=payload.round_type,
        sequence=target_seq,
        duration_minutes=payload.duration_minutes,
        difficulty=payload.difficulty,
        instructions=payload.instructions,
        is_required=payload.is_required,
        configuration=payload.configuration or {},
    )
    db.add(new_round)
    await db.commit()
    await db.refresh(new_round)

    return RoundResponse(
        id=new_round.id,
        interview_id=new_round.interview_id,
        name=new_round.name,
        description=new_round.description,
        round_type=new_round.round_type,
        sequence=new_round.sequence,
        duration_minutes=new_round.duration_minutes,
        difficulty=new_round.difficulty,
        instructions=new_round.instructions,
        is_required=new_round.is_required,
        configuration=new_round.configuration or {},
        created_at=new_round.created_at,
        updated_at=new_round.updated_at,
        questions=[],
    )


@router.patch(
    "/{interview_id}/rounds/{round_id}",
    response_model=RoundResponse,
    summary="Update an interview round",
)
async def update_round(
    round_id: uuid.UUID,
    payload: RoundUpdate,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewRound).where(
        InterviewRound.id == round_id,
        InterviewRound.interview_id == interview.id,
        InterviewRound.is_deleted.is_(False),
    )
    r = (await db.execute(stmt)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(r, field, val)

    await db.commit()
    await db.refresh(r)

    return RoundResponse(
        id=r.id,
        interview_id=r.interview_id,
        name=r.name,
        description=r.description,
        round_type=r.round_type,
        sequence=r.sequence,
        duration_minutes=r.duration_minutes,
        difficulty=r.difficulty,
        instructions=r.instructions,
        is_required=r.is_required,
        configuration=r.configuration or {},
        created_at=r.created_at,
        updated_at=r.updated_at,
        questions=[],
    )


@router.delete(
    "/{interview_id}/rounds/{round_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete an interview round",
)
async def delete_round(
    round_id: uuid.UUID,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewRound).where(
        InterviewRound.id == round_id,
        InterviewRound.interview_id == interview.id,
        InterviewRound.is_deleted.is_(False),
    )
    r = (await db.execute(stmt)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")

    r.is_deleted = True
    await db.commit()


@router.patch(
    "/{interview_id}/rounds/reorder",
    response_model=List[RoundResponse],
    summary="Reorder round sequence numbers",
)
async def reorder_rounds(
    payload: ReorderRequest,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    # Verify uniqueness of sequences in payload
    seqs = [item.sequence for item in payload.items]
    if len(seqs) != len(set(seqs)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate sequence numbers provided")

    for item in payload.items:
        r_stmt = select(InterviewRound).where(
            InterviewRound.id == item.id,
            InterviewRound.interview_id == interview.id,
        )
        r = (await db.execute(r_stmt)).scalar_one_or_none()
        if r:
            r.sequence = item.sequence

    await db.commit()
    return await list_interview_rounds(interview, db)


# --- 3. QUESTION ASSIGNMENT TO ROUNDS ---

@router.post(
    "/{interview_id}/rounds/{round_id}/questions",
    response_model=RoundQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a question to an interview round",
)
async def assign_question_to_round(
    round_id: uuid.UUID,
    payload: RoundQuestionCreate,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    # Verify round belongs to interview
    r_stmt = select(InterviewRound).where(
        InterviewRound.id == round_id,
        InterviewRound.interview_id == interview.id,
        InterviewRound.is_deleted.is_(False),
    )
    r = (await db.execute(r_stmt)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")

    # Verify question belongs to workspace or is global system question
    q_stmt = select(Question).where(
        Question.id == payload.question_id,
        or_(Question.workspace_id == interview.workspace_id, Question.workspace_id.is_(None)),
        Question.is_deleted.is_(False),
    )
    q = (await db.execute(q_stmt)).scalar_one_or_none()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found or does not belong to this workspace",
        )

    # Check for duplicate assignment
    dup_check = await db.execute(
        select(InterviewRoundQuestion).where(
            InterviewRoundQuestion.round_id == round_id,
            InterviewRoundQuestion.question_id == payload.question_id,
        )
    )
    if dup_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question is already assigned to this round",
        )

    # Determine sequence
    if payload.sequence is not None:
        target_seq = payload.sequence
    else:
        max_seq_res = await db.execute(
            select(func.coalesce(func.max(InterviewRoundQuestion.sequence), 0)).where(
                InterviewRoundQuestion.round_id == round_id
            )
        )
        target_seq = max_seq_res.scalar_one() + 1

    link = InterviewRoundQuestion(
        round_id=round_id,
        question_id=payload.question_id,
        sequence=target_seq,
        is_required=payload.is_required,
        time_limit_seconds=payload.time_limit_seconds,
        configuration=payload.configuration or {},
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return RoundQuestionResponse(
        id=link.id,
        round_id=link.round_id,
        question_id=link.question_id,
        sequence=link.sequence,
        is_required=link.is_required,
        time_limit_seconds=link.time_limit_seconds,
        configuration=link.configuration or {},
        question=QuestionResponse(
            id=q.id,
            workspace_id=q.workspace_id,
            created_by=q.created_by,
            title=q.title,
            prompt=q.prompt,
            question_type=q.question_type,
            difficulty=q.difficulty,
            category=q.category,
            expected_duration_minutes=q.expected_duration_minutes,
            skills=q.skills or [],
            topics=q.topics or [],
            evaluation_criteria=q.evaluation_criteria or [],
            hints=q.hints or [],
            reference_answer=q.reference_answer,
            is_template=q.is_template,
            created_at=q.created_at,
            updated_at=q.updated_at,
        ),
    )


@router.delete(
    "/{interview_id}/rounds/{round_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a question from a round",
)
async def remove_question_from_round(
    round_id: uuid.UUID,
    question_id: uuid.UUID,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewRoundQuestion).where(
        InterviewRoundQuestion.round_id == round_id,
        InterviewRoundQuestion.question_id == question_id,
    )
    link = (await db.execute(stmt)).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question link not found in this round")

    await db.delete(link)
    await db.commit()


# --- 4. PARTICIPANTS MANAGEMENT ---

@router.get(
    "/{interview_id}/participants",
    response_model=List[ParticipantResponse],
    summary="List assigned interview participants",
)
async def list_participants(
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewParticipant)
        .where(InterviewParticipant.interview_id == interview.id)
        .options(selectinload(InterviewParticipant.user))
    )
    res = await db.execute(stmt)
    parts = res.scalars().all()

    return [
        ParticipantResponse(
            id=p.id,
            interview_id=p.interview_id,
            user_id=p.user_id,
            user_name=f"{p.user.first_name} {p.user.last_name}" if p.user else None,
            user_email=p.user.email if p.user else None,
            participant_role=p.participant_role,
            is_primary=p.is_primary,
            created_at=p.created_at,
        )
        for p in parts
    ]


@router.post(
    "/{interview_id}/participants",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a participant to the interview",
)
async def add_participant(
    payload: ParticipantCreate,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    # Verify user belongs to the workspace
    ws_mem_stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == interview.workspace_id,
        WorkspaceMembership.user_id == payload.user_id,
    )
    mem = (await db.execute(ws_mem_stmt)).scalar_one_or_none()
    if not mem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to this workspace",
        )

    # Check for duplicate assignment
    dup_stmt = select(InterviewParticipant).where(
        InterviewParticipant.interview_id == interview.id,
        InterviewParticipant.user_id == payload.user_id,
    )
    if (await db.execute(dup_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this interview",
        )

    part = InterviewParticipant(
        interview_id=interview.id,
        user_id=payload.user_id,
        participant_role=payload.participant_role,
        is_primary=payload.is_primary,
    )
    db.add(part)
    await db.commit()
    await db.refresh(part)

    u_stmt = select(User).where(User.id == payload.user_id)
    u = (await db.execute(u_stmt)).scalar_one()

    return ParticipantResponse(
        id=part.id,
        interview_id=part.interview_id,
        user_id=part.user_id,
        user_name=f"{u.first_name} {u.last_name}",
        user_email=u.email,
        participant_role=part.participant_role,
        is_primary=part.is_primary,
        created_at=part.created_at,
    )


@router.delete(
    "/{interview_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove participant from interview",
)
async def remove_participant(
    user_id: uuid.UUID,
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewParticipant).where(
        InterviewParticipant.interview_id == interview.id,
        InterviewParticipant.user_id == user_id,
    )
    part = (await db.execute(stmt)).scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    await db.delete(part)
    await db.commit()
