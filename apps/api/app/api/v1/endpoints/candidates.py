import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    verify_candidate_access,
    verify_workspace_access,
)
from app.models.candidate import (
    Candidate,
    CandidateActivity,
    CandidateDocument,
    CandidateNote,
    CandidateSource,
    CandidateStatus,
    CandidateTag,
    CandidateTagAssignment,
    DocumentType,
    JobCandidate,
)
from app.models.job import Job
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.schemas.candidate import (
    ActivityResponse,
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
    DocumentResponse,
    JobApplicationResponse,
    NoteCreate,
    NoteResponse,
    PaginatedCandidatesResponse,
    TagCreate,
    TagResponse,
)
from app.services.storage import storage_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedCandidatesResponse,
    summary="List and search candidates within a workspace with pagination and filters",
)
async def list_candidates(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    status_filter: Optional[CandidateStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Strict Tenant Isolation: user must have membership in workspace
    await verify_workspace_access(workspace_id, current_user, db)

    query = select(Candidate).where(
        Candidate.workspace_id == workspace_id,
        Candidate.is_deleted.is_(False),
    )

    if status_filter:
        query = query.where(Candidate.status == status_filter)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            (Candidate.first_name.ilike(search_pattern))
            | (Candidate.last_name.ilike(search_pattern))
            | (Candidate.email.ilike(search_pattern))
            | (Candidate.headline.ilike(search_pattern))
            | (Candidate.current_company.ilike(search_pattern))
            | (Candidate.current_title.ilike(search_pattern))
            | (Candidate.location.ilike(search_pattern))
        )

    if tag:
        query = query.join(Candidate.tag_assignments).join(CandidateTagAssignment.tag).where(
            CandidateTag.name.ilike(tag.strip())
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    query = (
        query.order_by(Candidate.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(Candidate.tag_assignments).selectinload(CandidateTagAssignment.tag),
            selectinload(Candidate.job_applications).selectinload(JobCandidate.job),
            selectinload(Candidate.documents),
            selectinload(Candidate.notes),
        )
    )
    res = await db.execute(query)
    candidates = res.scalars().all()

    items = []
    for cand in candidates:
        tags = [
            TagResponse(
                id=ta.tag.id,
                workspace_id=ta.tag.workspace_id,
                name=ta.tag.name,
                color=ta.tag.color,
                created_at=ta.tag.created_at,
            )
            for ta in cand.tag_assignments
            if ta.tag
        ]
        apps = [
            JobApplicationResponse(
                id=app.id,
                job_id=app.job_id,
                job_title=app.job.title if app.job else None,
                job_department=app.job.department if app.job else None,
                candidate_id=app.candidate_id,
                status=app.status,
                source=app.source,
                applied_at=app.applied_at,
                last_activity_at=app.last_activity_at,
            )
            for app in cand.job_applications
        ]
        items.append(
            CandidateResponse(
                id=cand.id,
                workspace_id=cand.workspace_id,
                first_name=cand.first_name,
                last_name=cand.last_name,
                email=cand.email,
                phone=cand.phone,
                location=cand.location,
                headline=cand.headline,
                current_company=cand.current_company,
                current_title=cand.current_title,
                experience_years=cand.experience_years,
                education_summary=cand.education_summary,
                linkedin_url=cand.linkedin_url,
                github_url=cand.github_url,
                portfolio_url=cand.portfolio_url,
                status=cand.status,
                source=cand.source,
                notes_summary=cand.notes_summary,
                created_at=cand.created_at,
                updated_at=cand.updated_at,
                tags=tags,
                job_applications=apps,
                document_count=len(cand.documents),
                note_count=len(cand.notes),
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return PaginatedCandidatesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate in a workspace",
)
async def create_candidate(
    payload: CandidateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # RBAC: Workspace Admin or Recruiter can create candidates
    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating candidates requires Admin or Recruiter workspace permissions",
        )

    # Check for duplicate email in this workspace
    dup_stmt = select(Candidate).where(
        Candidate.workspace_id == payload.workspace_id,
        Candidate.email == payload.email.lower().strip(),
        Candidate.is_deleted.is_(False),
    )
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Candidate with email '{payload.email}' already exists in this workspace",
        )

    new_cand = Candidate(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=payload.email.lower().strip(),
        phone=payload.phone.strip() if payload.phone else None,
        location=payload.location.strip() if payload.location else None,
        headline=payload.headline.strip() if payload.headline else None,
        current_company=payload.current_company.strip() if payload.current_company else None,
        current_title=payload.current_title.strip() if payload.current_title else None,
        experience_years=payload.experience_years,
        education_summary=payload.education_summary,
        linkedin_url=payload.linkedin_url,
        github_url=payload.github_url,
        portfolio_url=payload.portfolio_url,
        status=payload.status,
        source=payload.source,
        notes_summary=payload.notes_summary,
    )
    db.add(new_cand)
    await db.flush()

    # Record Activity Timeline
    activity = CandidateActivity(
        candidate_id=new_cand.id,
        actor_id=current_user.id,
        event_type="candidate_created",
        details={"source": payload.source.value},
    )
    db.add(activity)

    # Handle optional initial tags
    tags = []
    if payload.tag_names:
        for tag_name in payload.tag_names:
            cleaned = tag_name.strip()
            if not cleaned:
                continue
            # Find or create tag in workspace
            tag_stmt = select(CandidateTag).where(
                CandidateTag.workspace_id == payload.workspace_id,
                CandidateTag.name.ilike(cleaned),
            )
            tag_res = await db.execute(tag_stmt)
            existing_tag = tag_res.scalar_one_or_none()
            if not existing_tag:
                existing_tag = CandidateTag(
                    workspace_id=payload.workspace_id,
                    name=cleaned,
                )
                db.add(existing_tag)
                await db.flush()

            assignment = CandidateTagAssignment(
                tag_id=existing_tag.id,
                candidate_id=new_cand.id,
            )
            db.add(assignment)
            tags.append(
                TagResponse(
                    id=existing_tag.id,
                    workspace_id=existing_tag.workspace_id,
                    name=existing_tag.name,
                    color=existing_tag.color,
                    created_at=existing_tag.created_at,
                )
            )

    # Handle optional initial job application
    apps = []
    if payload.job_id:
        job_stmt = select(Job).where(
            Job.id == payload.job_id,
            Job.workspace_id == payload.workspace_id,
            Job.is_deleted.is_(False),
        )
        job_res = await db.execute(job_stmt)
        target_job = job_res.scalar_one_or_none()
        if target_job:
            new_app = JobCandidate(
                job_id=target_job.id,
                candidate_id=new_cand.id,
                status=CandidateStatus.NEW,
                source=payload.source.value,
            )
            db.add(new_app)
            await db.flush()
            apps.append(
                JobApplicationResponse(
                    id=new_app.id,
                    job_id=new_app.job_id,
                    job_title=target_job.title,
                    job_department=target_job.department,
                    candidate_id=new_app.candidate_id,
                    status=new_app.status,
                    source=new_app.source,
                    applied_at=new_app.applied_at,
                    last_activity_at=new_app.last_activity_at,
                )
            )

    await db.commit()
    await db.refresh(new_cand)

    return CandidateResponse(
        id=new_cand.id,
        workspace_id=new_cand.workspace_id,
        first_name=new_cand.first_name,
        last_name=new_cand.last_name,
        email=new_cand.email,
        phone=new_cand.phone,
        location=new_cand.location,
        headline=new_cand.headline,
        current_company=new_cand.current_company,
        current_title=new_cand.current_title,
        experience_years=new_cand.experience_years,
        education_summary=new_cand.education_summary,
        linkedin_url=new_cand.linkedin_url,
        github_url=new_cand.github_url,
        portfolio_url=new_cand.portfolio_url,
        status=new_cand.status,
        source=new_cand.source,
        notes_summary=new_cand.notes_summary,
        created_at=new_cand.created_at,
        updated_at=new_cand.updated_at,
        tags=tags,
        job_applications=apps,
        document_count=0,
        note_count=0,
    )


@router.get(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Get single candidate profile with tags and applications",
)
async def get_candidate(
    candidate: Candidate = Depends(verify_candidate_access),
    db: AsyncSession = Depends(get_db),
):
    # Eager load relationships
    stmt = (
        select(Candidate)
        .where(Candidate.id == candidate.id)
        .options(
            selectinload(Candidate.tag_assignments).selectinload(CandidateTagAssignment.tag),
            selectinload(Candidate.job_applications).selectinload(JobCandidate.job),
            selectinload(Candidate.documents),
            selectinload(Candidate.notes),
        )
    )
    res = await db.execute(stmt)
    full_cand = res.scalar_one()

    tags = [
        TagResponse(
            id=ta.tag.id,
            workspace_id=ta.tag.workspace_id,
            name=ta.tag.name,
            color=ta.tag.color,
            created_at=ta.tag.created_at,
        )
        for ta in full_cand.tag_assignments
        if ta.tag
    ]
    apps = [
        JobApplicationResponse(
            id=app.id,
            job_id=app.job_id,
            job_title=app.job.title if app.job else None,
            job_department=app.job.department if app.job else None,
            candidate_id=app.candidate_id,
            status=app.status,
            source=app.source,
            applied_at=app.applied_at,
            last_activity_at=app.last_activity_at,
        )
        for app in full_cand.job_applications
    ]

    return CandidateResponse(
        id=full_cand.id,
        workspace_id=full_cand.workspace_id,
        first_name=full_cand.first_name,
        last_name=full_cand.last_name,
        email=full_cand.email,
        phone=full_cand.phone,
        location=full_cand.location,
        headline=full_cand.headline,
        current_company=full_cand.current_company,
        current_title=full_cand.current_title,
        experience_years=full_cand.experience_years,
        education_summary=full_cand.education_summary,
        linkedin_url=full_cand.linkedin_url,
        github_url=full_cand.github_url,
        portfolio_url=full_cand.portfolio_url,
        status=full_cand.status,
        source=full_cand.source,
        notes_summary=full_cand.notes_summary,
        created_at=full_cand.created_at,
        updated_at=full_cand.updated_at,
        tags=tags,
        job_applications=apps,
        document_count=len(full_cand.documents),
        note_count=len(full_cand.notes),
    )


@router.patch(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Update candidate profile information",
)
async def update_candidate(
    payload: CandidateUpdate,
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(candidate.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Updating candidates requires Admin or Recruiter workspace permissions",
        )

    old_status = candidate.status
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)

    if payload.status and payload.status != old_status:
        activity = CandidateActivity(
            candidate_id=candidate.id,
            actor_id=current_user.id,
            event_type="candidate_status_changed",
            details={"old_status": old_status.value, "new_status": payload.status.value},
        )
        db.add(activity)

    await db.commit()
    await db.refresh(candidate)

    return await get_candidate(candidate, db)


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete candidate",
)
async def delete_candidate(
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(candidate.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")

    candidate.is_deleted = True
    await db.commit()


# --- CANDIDATE DOCUMENTS (MINIO INTEGRATION) ---

@router.post(
    "/{candidate_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload candidate resume or document",
)
async def upload_candidate_document(
    file: UploadFile = File(...),
    document_type: DocumentType = DocumentType.RESUME,
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Upload to MinIO (or fallback)
    storage_key = storage_service.upload_document(
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=content_type,
        candidate_id=candidate.id,
    )

    doc = CandidateDocument(
        candidate_id=candidate.id,
        uploaded_by=current_user.id,
        file_name=file.filename,
        storage_key=storage_key,
        mime_type=content_type,
        file_size=len(file_bytes),
        document_type=document_type,
    )
    db.add(doc)

    activity = CandidateActivity(
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="candidate_document_uploaded",
        details={"file_name": file.filename, "document_type": document_type.value},
    )
    db.add(activity)
    await db.commit()
    await db.refresh(doc)

    return DocumentResponse(
        id=doc.id,
        candidate_id=doc.candidate_id,
        uploaded_by=doc.uploaded_by,
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        document_type=doc.document_type,
        created_at=doc.created_at,
    )


@router.get(
    "/{candidate_id}/documents",
    response_model=List[DocumentResponse],
    summary="List all documents for a candidate",
)
async def list_candidate_documents(
    candidate: Candidate = Depends(verify_candidate_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CandidateDocument)
        .where(
            CandidateDocument.candidate_id == candidate.id,
            CandidateDocument.is_deleted.is_(False),
        )
        .order_by(CandidateDocument.created_at.desc())
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()
    return [
        DocumentResponse(
            id=d.id,
            candidate_id=d.candidate_id,
            uploaded_by=d.uploaded_by,
            file_name=d.file_name,
            mime_type=d.mime_type,
            file_size=d.file_size,
            document_type=d.document_type,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get(
    "/{candidate_id}/documents/{document_id}/download",
    summary="Download candidate document from storage",
)
async def download_candidate_document(
    document_id: uuid.UUID,
    candidate: Candidate = Depends(verify_candidate_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CandidateDocument).where(
        CandidateDocument.id == document_id,
        CandidateDocument.candidate_id == candidate.id,
        CandidateDocument.is_deleted.is_(False),
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_bytes = storage_service.get_document_bytes(doc.storage_key)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found in storage")

    return FastAPIResponse(
        content=file_bytes,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.file_name}"',
            "Content-Length": str(len(file_bytes)),
        },
    )


@router.delete(
    "/{candidate_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete candidate document",
)
async def delete_candidate_document(
    document_id: uuid.UUID,
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CandidateDocument).where(
        CandidateDocument.id == document_id,
        CandidateDocument.candidate_id == candidate.id,
        CandidateDocument.is_deleted.is_(False),
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.is_deleted = True
    storage_service.delete_document(doc.storage_key)
    await db.commit()


# --- CANDIDATE NOTES ---

@router.get(
    "/{candidate_id}/notes",
    response_model=List[NoteResponse],
    summary="List candidate notes",
)
async def list_candidate_notes(
    candidate: Candidate = Depends(verify_candidate_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CandidateNote)
        .where(
            CandidateNote.candidate_id == candidate.id,
            CandidateNote.is_deleted.is_(False),
        )
        .options(selectinload(CandidateNote.author))
        .order_by(CandidateNote.created_at.desc())
    )
    res = await db.execute(stmt)
    notes = res.scalars().all()

    return [
        NoteResponse(
            id=n.id,
            candidate_id=n.candidate_id,
            author_id=n.author_id,
            author_name=f"{n.author.first_name} {n.author.last_name}" if n.author else None,
            content=n.content,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notes
    ]


@router.post(
    "/{candidate_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an internal note to candidate",
)
async def add_candidate_note(
    payload: NoteCreate,
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_note = CandidateNote(
        candidate_id=candidate.id,
        author_id=current_user.id,
        content=payload.content.strip(),
    )
    db.add(new_note)

    activity = CandidateActivity(
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="candidate_note_added",
        details={"note_snippet": payload.content[:100]},
    )
    db.add(activity)
    await db.commit()
    await db.refresh(new_note)

    return NoteResponse(
        id=new_note.id,
        candidate_id=new_note.candidate_id,
        author_id=new_note.author_id,
        author_name=f"{current_user.first_name} {current_user.last_name}",
        content=new_note.content,
        created_at=new_note.created_at,
        updated_at=new_note.updated_at,
    )


# --- CANDIDATE ACTIVITY TIMELINE ---

@router.get(
    "/{candidate_id}/activity",
    response_model=List[ActivityResponse],
    summary="Get candidate chronological activity timeline",
)
async def get_candidate_activity(
    candidate: Candidate = Depends(verify_candidate_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CandidateActivity)
        .where(CandidateActivity.candidate_id == candidate.id)
        .options(selectinload(CandidateActivity.actor))
        .order_by(CandidateActivity.created_at.desc())
    )
    res = await db.execute(stmt)
    acts = res.scalars().all()

    return [
        ActivityResponse(
            id=a.id,
            candidate_id=a.candidate_id,
            actor_id=a.actor_id,
            actor_name=f"{a.actor.first_name} {a.actor.last_name}" if a.actor else None,
            event_type=a.event_type,
            details=a.details or {},
            created_at=a.created_at,
        )
        for a in acts
    ]


# --- WORKSPACE CANDIDATE TAGS ---

@router.get(
    "/tags/workspace",
    response_model=List[TagResponse],
    summary="List all tags for a workspace",
)
async def list_workspace_tags(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)
    stmt = select(CandidateTag).where(CandidateTag.workspace_id == workspace_id).order_by(CandidateTag.name.asc())
    res = await db.execute(stmt)
    tags = res.scalars().all()
    return [
        TagResponse(
            id=t.id,
            workspace_id=t.workspace_id,
            name=t.name,
            color=t.color,
            created_at=t.created_at,
        )
        for t in tags
    ]


@router.post(
    "/tags/workspace",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag in workspace",
)
async def create_workspace_tag(
    payload: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(payload.workspace_id, current_user, db)

    # Check duplicate
    dup_stmt = select(CandidateTag).where(
        CandidateTag.workspace_id == payload.workspace_id,
        CandidateTag.name.ilike(payload.name.strip()),
    )
    dup = (await db.execute(dup_stmt)).scalar_one_or_none()
    if dup:
        return TagResponse(
            id=dup.id,
            workspace_id=dup.workspace_id,
            name=dup.name,
            color=dup.color,
            created_at=dup.created_at,
        )

    new_tag = CandidateTag(
        workspace_id=payload.workspace_id,
        name=payload.name.strip(),
        color=payload.color or "#6366f1",
    )
    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)

    return TagResponse(
        id=new_tag.id,
        workspace_id=new_tag.workspace_id,
        name=new_tag.name,
        color=new_tag.color,
        created_at=new_tag.created_at,
    )
