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
    verify_template_access,
    verify_workspace_access,
)
from app.models.interview import (
    InterviewDifficulty,
    InterviewTemplate,
    InterviewTemplateQuestion,
    InterviewTemplateRound,
    InterviewType,
)
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.schemas.interview import (
    PaginatedTemplatesResponse,
    TemplateCreate,
    TemplateResponse,
    TemplateRoundResponse,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedTemplatesResponse,
    summary="List available interview templates (workspace and system defaults)",
)
async def list_templates(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    interview_type: Optional[InterviewType] = Query(None),
    difficulty: Optional[InterviewDifficulty] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)

    query = select(InterviewTemplate).where(
        or_(
            InterviewTemplate.workspace_id == workspace_id,
            InterviewTemplate.is_system.is_(True),
            InterviewTemplate.workspace_id.is_(None),
        ),
        InterviewTemplate.is_deleted.is_(False),
    )

    if interview_type:
        query = query.where(InterviewTemplate.interview_type == interview_type)
    if difficulty:
        query = query.where(InterviewTemplate.difficulty == difficulty)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                InterviewTemplate.name.ilike(search_pattern),
                InterviewTemplate.description.ilike(search_pattern),
            )
        )

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    query = (
        query.order_by(InterviewTemplate.is_system.desc(), InterviewTemplate.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(InterviewTemplate.template_rounds).selectinload(
                InterviewTemplateRound.template_questions
            )
        )
    )
    res = await db.execute(query)
    templates = res.scalars().all()

    items = []
    for t in templates:
        rounds = [
            TemplateRoundResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                round_type=r.round_type,
                sequence=r.sequence,
                duration_minutes=r.duration_minutes,
                difficulty=r.difficulty,
                instructions=r.instructions,
                configuration=r.configuration or {},
            )
            for r in t.template_rounds
        ]
        items.append(
            TemplateResponse(
                id=t.id,
                workspace_id=t.workspace_id,
                name=t.name,
                description=t.description,
                interview_type=t.interview_type,
                difficulty=t.difficulty,
                total_duration_minutes=t.total_duration_minutes,
                is_system=t.is_system,
                configuration=t.configuration or {},
                created_at=t.created_at,
                rounds=rounds,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedTemplatesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom interview template in a workspace",
)
async def create_template(
    payload: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required to create a template",
        )

    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating templates requires Admin or Recruiter permissions",
        )

    new_tpl = InterviewTemplate(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        total_duration_minutes=payload.total_duration_minutes,
        is_system=False,
        configuration=payload.configuration or {},
    )
    db.add(new_tpl)
    await db.flush()

    # Add template rounds if provided
    created_rounds = []
    for r_in in payload.rounds:
        new_round = InterviewTemplateRound(
            template_id=new_tpl.id,
            name=r_in.name.strip(),
            description=r_in.description,
            round_type=r_in.round_type,
            sequence=r_in.sequence,
            duration_minutes=r_in.duration_minutes,
            difficulty=r_in.difficulty,
            instructions=r_in.instructions,
            configuration=r_in.configuration or {},
        )
        db.add(new_round)
        await db.flush()

        # Add question associations
        for seq, q_id in enumerate(r_in.question_ids, start=1):
            q_link = InterviewTemplateQuestion(
                template_round_id=new_round.id,
                question_id=q_id,
                sequence=seq,
            )
            db.add(q_link)

        created_rounds.append(
            TemplateRoundResponse(
                id=new_round.id,
                name=new_round.name,
                description=new_round.description,
                round_type=new_round.round_type,
                sequence=new_round.sequence,
                duration_minutes=new_round.duration_minutes,
                difficulty=new_round.difficulty,
                instructions=new_round.instructions,
                configuration=new_round.configuration or {},
            )
        )

    await db.commit()
    await db.refresh(new_tpl)

    return TemplateResponse(
        id=new_tpl.id,
        workspace_id=new_tpl.workspace_id,
        name=new_tpl.name,
        description=new_tpl.description,
        interview_type=new_tpl.interview_type,
        difficulty=new_tpl.difficulty,
        total_duration_minutes=new_tpl.total_duration_minutes,
        is_system=new_tpl.is_system,
        configuration=new_tpl.configuration or {},
        created_at=new_tpl.created_at,
        rounds=created_rounds,
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get single interview template with rounds",
)
async def get_template(
    template: InterviewTemplate = Depends(verify_template_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewTemplate)
        .where(InterviewTemplate.id == template.id)
        .options(
            selectinload(InterviewTemplate.template_rounds).selectinload(
                InterviewTemplateRound.template_questions
            )
        )
    )
    res = await db.execute(stmt)
    full_tpl = res.scalar_one()

    rounds = [
        TemplateRoundResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            round_type=r.round_type,
            sequence=r.sequence,
            duration_minutes=r.duration_minutes,
            difficulty=r.difficulty,
            instructions=r.instructions,
            configuration=r.configuration or {},
        )
        for r in full_tpl.template_rounds
    ]

    return TemplateResponse(
        id=full_tpl.id,
        workspace_id=full_tpl.workspace_id,
        name=full_tpl.name,
        description=full_tpl.description,
        interview_type=full_tpl.interview_type,
        difficulty=full_tpl.difficulty,
        total_duration_minutes=full_tpl.total_duration_minutes,
        is_system=full_tpl.is_system,
        configuration=full_tpl.configuration or {},
        created_at=full_tpl.created_at,
        rounds=rounds,
    )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete interview template",
)
async def delete_template(
    template: InterviewTemplate = Depends(verify_template_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if template.is_system or template.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System-level templates cannot be deleted.",
        )

    template.is_deleted = True
    await db.commit()
