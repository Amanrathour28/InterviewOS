import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    verify_question_access,
    verify_workspace_access,
)
from app.models.interview import Question, QuestionDifficulty, QuestionType
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.schemas.interview import (
    PaginatedQuestionsResponse,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedQuestionsResponse,
    summary="List questions in a workspace including system questions",
)
async def list_questions(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    question_type: Optional[QuestionType] = Query(None),
    difficulty: Optional[QuestionDifficulty] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)

    # Questions accessible: workspace-owned OR global system questions (workspace_id is None)
    query = select(Question).where(
        or_(Question.workspace_id == workspace_id, Question.workspace_id.is_(None)),
        Question.is_deleted.is_(False),
    )

    if question_type:
        query = query.where(Question.question_type == question_type)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    if category:
        query = query.where(Question.category.ilike(f"%{category.strip()}%"))
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Question.title.ilike(search_pattern),
                Question.prompt.ilike(search_pattern),
                Question.category.ilike(search_pattern),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(Question.created_at.desc()).offset(offset).limit(page_size)
    res = await db.execute(query)
    questions = res.scalars().all()

    items = [
        QuestionResponse(
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
        )
        for q in questions
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedQuestionsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom question in a workspace",
)
async def create_question(
    payload: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required to create a question",
        )

    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
        WorkspaceMemberRole.INTERVIEWER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to create questions in this workspace",
        )

    new_q = Question(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        title=payload.title.strip(),
        prompt=payload.prompt.strip(),
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        category=payload.category.strip() or "General",
        expected_duration_minutes=payload.expected_duration_minutes,
        skills=payload.skills or [],
        topics=payload.topics or [],
        evaluation_criteria=payload.evaluation_criteria or [],
        hints=payload.hints or [],
        reference_answer=payload.reference_answer.strip() if payload.reference_answer else None,
        is_template=payload.is_template,
    )
    db.add(new_q)
    await db.commit()
    await db.refresh(new_q)

    return QuestionResponse(
        id=new_q.id,
        workspace_id=new_q.workspace_id,
        created_by=new_q.created_by,
        title=new_q.title,
        prompt=new_q.prompt,
        question_type=new_q.question_type,
        difficulty=new_q.difficulty,
        category=new_q.category,
        expected_duration_minutes=new_q.expected_duration_minutes,
        skills=new_q.skills or [],
        topics=new_q.topics or [],
        evaluation_criteria=new_q.evaluation_criteria or [],
        hints=new_q.hints or [],
        reference_answer=new_q.reference_answer,
        is_template=new_q.is_template,
        created_at=new_q.created_at,
        updated_at=new_q.updated_at,
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Get single question details",
)
async def get_question(
    question: Question = Depends(verify_question_access),
):
    return QuestionResponse(
        id=question.id,
        workspace_id=question.workspace_id,
        created_by=question.created_by,
        title=question.title,
        prompt=question.prompt,
        question_type=question.question_type,
        difficulty=question.difficulty,
        category=question.category,
        expected_duration_minutes=question.expected_duration_minutes,
        skills=question.skills or [],
        topics=question.topics or [],
        evaluation_criteria=question.evaluation_criteria or [],
        hints=question.hints or [],
        reference_answer=question.reference_answer,
        is_template=question.is_template,
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


@router.patch(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Update question",
)
async def update_question(
    payload: QuestionUpdate,
    question: Question = Depends(verify_question_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if question.workspace_id is None and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System-level questions cannot be modified directly.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)

    await db.commit()
    await db.refresh(question)
    return await get_question(question)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete question",
)
async def delete_question(
    question: Question = Depends(verify_question_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if question.workspace_id is None and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System-level questions cannot be deleted.",
        )

    question.is_deleted = True
    await db.commit()
