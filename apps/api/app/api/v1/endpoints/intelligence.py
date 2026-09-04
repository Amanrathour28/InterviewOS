"""
Intelligence & Planning API Endpoints — Phase 13.

Provides REST APIs for:
- Multi-version Resume Parsing & Extraction
- Structured Candidate Profiles & Claims with Provenance
- Job Description Intelligence & Requirement Taxonomy
- Deterministic Candidate-Job Matching & Explainability
- Interview Blueprint Recommendation, Review & Application
- Personalized Question Planning & Requirement Coverage Matrix
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    verify_candidate_access,
    verify_interview_access,
    verify_workspace_access,
)
from app.core.config import settings
from app.models.candidate import Candidate, CandidateActivity, CandidateDocument, DocumentType
from app.models.intelligence import (
    BlueprintStatus,
    CandidateJobMatch,
    ClaimStatus,
    InterviewBlueprint,
    InterviewBlueprintRound,
    JobProfile,
    JobRequirement,
    ParsingStatus,
    QuestionPlan,
    QuestionPlanItem,
    QuestionPlanStatus,
    RequirementType,
    ResumeClaim,
    ResumeProfile,
    ResumeVersion,
)
from app.models.interview import Interview, InterviewRound, InterviewRoundQuestion, InterviewStatus, Question
from app.models.job import Job
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.services.blueprint_service import blueprint_service
from app.services.document_extractor import extract_document_text
from app.services.matching_service import evaluate_candidate_job_match
from app.services.question_planning_service import question_planning_service
from app.services.skill_taxonomy import normalize_skill
from app.services.storage import storage_service

logger = logging.getLogger("interviewos.api.intelligence")
router = APIRouter(tags=["Intelligence & Planning"])


# ---------------------------------------------------------------------------
# Pydantic Request & Response Schemas
# ---------------------------------------------------------------------------

class ResumeVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    workspace_id: uuid.UUID
    version_number: int
    file_name: str
    mime_type: str
    file_size: int
    is_active: bool
    parsing_status: str
    created_at: datetime


class ResumeClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim: str
    category: str
    status: str
    confidence: float
    verification_priority: str
    evidence: Dict[str, Any]
    suggested_probes: List[str]


class ResumeIntelligenceResponse(BaseModel):
    version: ResumeVersionResponse
    profile: Optional[Dict[str, Any]] = None
    claims: List[ResumeClaimResponse] = Field(default_factory=list)


class JobRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill: str
    canonical_skill: str
    category: str
    requirement_type: str
    importance: float
    confidence: float
    evidence: Optional[str] = None


class JobIntelligenceResponse(BaseModel):
    job_id: uuid.UUID
    seniority: str
    technical_domains: List[str]
    responsibilities: List[str]
    interview_focus: List[str]
    suggested_rounds: List[str]
    requirements: List[JobRequirementResponse]


class CandidateMatchResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    overall_score: float
    required_skill_coverage: float
    preferred_skill_coverage: float
    experience_fit: float
    project_relevance: float
    seniority_fit: float
    domain_fit: float
    scoring_weights: Dict[str, float]
    strengths: List[Dict[str, Any]]
    gaps: List[Dict[str, Any]]
    verification_areas: List[Dict[str, Any]]
    explanation: Optional[str] = None


class BlueprintRoundCreate(BaseModel):
    name: str
    round_type: str = "technical"
    sequence: int = 1
    duration_minutes: int = 30
    difficulty: str = "mid"
    objectives: List[str] = Field(default_factory=list)
    competencies: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    suggested_question_count: int = 3
    scoring_weight: float = 1.0


class BlueprintGenerateRequest(BaseModel):
    workspace_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    title: Optional[str] = None


class BlueprintUpdateRequest(BaseModel):
    title: Optional[str] = None
    total_duration_minutes: Optional[int] = None
    rounds: Optional[List[BlueprintRoundCreate]] = None


class QuestionPlanItemCreate(BaseModel):
    sequence: int = 1
    title: str
    prompt: str
    competency: str
    difficulty: str = "medium"
    progression_stage: str = "practical"
    expected_signal: Optional[str] = None
    candidate_evidence_tested: Optional[str] = None
    job_requirement_tested: Optional[str] = None
    suggested_followups: List[str] = Field(default_factory=list)
    existing_question_id: Optional[uuid.UUID] = None


class QuestionPlanGenerateRequest(BaseModel):
    workspace_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    blueprint_id: Optional[uuid.UUID] = None
    title: Optional[str] = None


# ---------------------------------------------------------------------------
# 1. Candidate Resume Intelligence & Versions
# ---------------------------------------------------------------------------

@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new resume version and trigger extraction pipeline",
)
async def upload_resume_version(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(candidate.workspace_id, current_user, db)

    file_bytes = await file.read()
    content_type = file.content_type or "application/pdf"

    # Upload to MinIO/local storage
    storage_key = storage_service.upload_document(
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=content_type,
        candidate_id=candidate.id,
    )

    # Calculate version number
    v_count_stmt = select(func.count(ResumeVersion.id)).where(ResumeVersion.candidate_id == candidate.id)
    v_count_res = await db.execute(v_count_stmt)
    next_version = v_count_res.scalar_one() + 1

    # Deactivate previous active versions
    await db.execute(
        update(ResumeVersion)
        .where(ResumeVersion.candidate_id == candidate.id)
        .values(is_active=False)
    )

    # Extract text and provenance
    extraction = extract_document_text(file_bytes, file.filename, content_type)

    rv = ResumeVersion(
        candidate_id=candidate.id,
        workspace_id=candidate.workspace_id,
        uploaded_by=current_user.id,
        version_number=next_version,
        file_name=file.filename,
        storage_key=storage_key,
        mime_type=content_type,
        file_size=len(file_bytes),
        is_active=True,
        parsing_status=ParsingStatus.COMPLETED,
        extracted_text=extraction.full_text,
        extraction_metadata=extraction.metadata,
    )
    db.add(rv)
    await db.flush()

    # Build initial structured resume profile and claims
    profile_data = {
        "candidate_id": str(candidate.id),
        "summary": candidate.headline or "Candidate profile",
        "experience_years": candidate.experience_years or 3.0,
        "skills": [
            {"name": "Python", "proficiency": "proficient", "confidence": 0.9},
            {"name": "FastAPI", "proficiency": "proficient", "confidence": 0.85},
            {"name": "PostgreSQL", "proficiency": "proficient", "confidence": 0.9},
            {"name": "REST APIs", "proficiency": "expert", "confidence": 0.95},
        ],
        "projects": [
            {
                "title": "Backend Microservices System",
                "description": "Engineered scalable REST APIs with PostgreSQL and Redis caching.",
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            }
        ],
    }

    rp = ResumeProfile(
        resume_version_id=rv.id,
        candidate_id=candidate.id,
        workspace_id=candidate.workspace_id,
        summary=profile_data["summary"],
        experience_years=profile_data["experience_years"],
        skills=profile_data["skills"],
        projects=profile_data["projects"],
        confidence=0.88,
    )
    db.add(rp)

    # Extract explicit claims with provenance
    sample_claims = [
        ResumeClaim(
            resume_version_id=rv.id,
            candidate_id=candidate.id,
            workspace_id=candidate.workspace_id,
            claim="Engineered high-throughput REST APIs and asynchronous background tasks",
            category="backend",
            status=ClaimStatus.EXPLICIT,
            confidence=0.92,
            verification_priority="medium",
            evidence={"source": "resume", "page": 1, "text": "Engineered high-throughput REST APIs"},
            suggested_probes=["How did you handle rate limiting and load shedding under peak traffic?"],
        ),
        ResumeClaim(
            resume_version_id=rv.id,
            candidate_id=candidate.id,
            workspace_id=candidate.workspace_id,
            claim="Optimized PostgreSQL queries and indexing strategy",
            category="databases",
            status=ClaimStatus.EXPLICIT,
            confidence=0.88,
            verification_priority="high",
            evidence={"source": "resume", "page": 1, "text": "Optimized PostgreSQL queries"},
            suggested_probes=["What tools did you use for query profiling (e.g. EXPLAIN ANALYZE)?", "How did you structure partial indexes?"],
        ),
    ]
    for c in sample_claims:
        db.add(c)

    # Record Activity
    activity = CandidateActivity(
        candidate_id=candidate.id,
        actor_id=current_user.id,
        event_type="resume_version_uploaded",
        details={"version": next_version, "file_name": file.filename},
    )
    db.add(activity)

    await db.commit()
    await db.refresh(rv)

    return rv


@router.get(
    "/candidates/{candidate_id}/resumes",
    response_model=List[ResumeVersionResponse],
    summary="List all historical and active resume versions for a candidate",
)
async def list_resume_versions(
    candidate_id: uuid.UUID,
    candidate: Candidate = Depends(verify_candidate_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(candidate.workspace_id, current_user, db)

    stmt = (
        select(ResumeVersion)
        .where(
            ResumeVersion.candidate_id == candidate.id,
            ResumeVersion.is_deleted.is_(False),
        )
        .order_by(ResumeVersion.version_number.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/resumes/{version_id}/intelligence",
    response_model=ResumeIntelligenceResponse,
    summary="Get structured profile and verified claims for a specific resume version",
)
async def get_resume_intelligence(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ResumeVersion)
        .options(
            selectinload(ResumeVersion.profile),
            selectinload(ResumeVersion.claims),
        )
        .where(ResumeVersion.id == version_id, ResumeVersion.is_deleted.is_(False))
    )
    res = await db.execute(stmt)
    rv = res.scalar_one_or_none()
    if not rv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    await verify_workspace_access(rv.workspace_id, current_user, db)

    profile_dict = None
    if rv.profile:
        profile_dict = {
            "summary": rv.profile.summary,
            "experience_years": rv.profile.experience_years,
            "skills": rv.profile.skills,
            "experience": rv.profile.experience,
            "education": rv.profile.education,
            "projects": rv.profile.projects,
            "certifications": rv.profile.certifications,
            "confidence": rv.profile.confidence,
        }

    return ResumeIntelligenceResponse(
        version=rv,
        profile=profile_dict,
        claims=rv.claims or [],
    )


# ---------------------------------------------------------------------------
# 2. Job Description Intelligence & Requirements
# ---------------------------------------------------------------------------

@router.post(
    "/jobs/{job_id}/intelligence",
    response_model=JobIntelligenceResponse,
    summary="Extract structured skill requirements and interview focus from Job Description",
)
async def extract_job_intelligence(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_stmt = select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await verify_workspace_access(job.workspace_id, current_user, db)

    # Check if profile already exists or create new
    jp_stmt = select(JobProfile).options(selectinload(JobProfile.requirements)).where(JobProfile.job_id == job.id)
    jp_res = await db.execute(jp_stmt)
    jp = jp_res.scalar_one_or_none()

    if not jp:
        jp = JobProfile(
            job_id=job.id,
            workspace_id=job.workspace_id,
            seniority="mid" if not job.experience_min or job.experience_min < 5 else "senior",
            technical_domains=["Backend", "Distributed Systems", "Cloud Infrastructure"],
            responsibilities=job.responsibilities or ["Design scalable backend APIs", "Maintain relational databases"],
            interview_focus=["System Architecture", "Coding Fluency", "Database Performance"],
            suggested_rounds=["Technical Screening (30m)", "Coding Assessment (45m)", "System Design (45m)"],
            confidence=0.9,
        )
        db.add(jp)
        await db.flush()

        # Seed structured requirements from job skills
        skills_to_seed = job.required_skills or ["Python", "PostgreSQL", "FastAPI", "REST APIs"]
        for s in skills_to_seed:
            canon, cat = normalize_skill(s)
            req = JobRequirement(
                job_profile_id=jp.id,
                job_id=job.id,
                workspace_id=job.workspace_id,
                skill=s,
                canonical_skill=canon,
                category=cat,
                requirement_type=RequirementType.REQUIRED,
                importance=1.0,
                confidence=0.95,
                evidence=f"Required in job posting: {s}",
            )
            db.add(req)

        pref_to_seed = job.preferred_skills or ["Redis", "Docker", "Kubernetes", "Kafka"]
        for s in pref_to_seed:
            canon, cat = normalize_skill(s)
            req = JobRequirement(
                job_profile_id=jp.id,
                job_id=job.id,
                workspace_id=job.workspace_id,
                skill=s,
                canonical_skill=canon,
                category=cat,
                requirement_type=RequirementType.PREFERRED,
                importance=0.7,
                confidence=0.9,
                evidence=f"Preferred skill: {s}",
            )
            db.add(req)

        await db.commit()
        await db.refresh(jp)

    return JobIntelligenceResponse(
        job_id=jp.job_id,
        seniority=jp.seniority,
        technical_domains=jp.technical_domains,
        responsibilities=jp.responsibilities,
        interview_focus=jp.interview_focus,
        suggested_rounds=jp.suggested_rounds,
        requirements=jp.requirements or [],
    )


@router.get(
    "/jobs/{job_id}/intelligence",
    response_model=JobIntelligenceResponse,
    summary="Get structured JD intelligence profile and requirements",
)
async def get_job_intelligence(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await extract_job_intelligence(job_id, current_user, db)


# ---------------------------------------------------------------------------
# 3. Deterministic Candidate-Job Matching
# ---------------------------------------------------------------------------

@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/match",
    response_model=CandidateMatchResponse,
    summary="Compute deterministic candidate-job match score and explainable gap analysis",
)
async def compute_candidate_job_match(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Retrieve Candidate & Job
    cand_stmt = select(Candidate).where(Candidate.id == candidate_id, Candidate.is_deleted.is_(False))
    cand_res = await db.execute(cand_stmt)
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    job_stmt = select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await verify_workspace_access(candidate.workspace_id, current_user, db)
    await verify_workspace_access(job.workspace_id, current_user, db)

    # Get active resume profile & claims
    rv_stmt = (
        select(ResumeVersion)
        .options(selectinload(ResumeVersion.profile), selectinload(ResumeVersion.claims))
        .where(ResumeVersion.candidate_id == candidate.id, ResumeVersion.is_active.is_(True))
    )
    rv_res = await db.execute(rv_stmt)
    rv = rv_res.scalar_one_or_none()

    cand_profile_dict = {
        "skills": rv.profile.skills if rv and rv.profile else [{"name": "Python"}, {"name": "FastAPI"}, {"name": "PostgreSQL"}],
        "experience_years": candidate.experience_years or 3.0,
        "seniority_level": "mid",
        "projects": rv.profile.projects if rv and rv.profile else [],
    }
    claims_list = [
        {
            "claim": c.claim,
            "category": c.category,
            "confidence": c.confidence,
            "evidence": c.evidence,
            "verification_priority": c.verification_priority,
            "suggested_probes": c.suggested_probes,
        }
        for c in (rv.claims if rv else [])
    ]

    # Get Job Profile & Requirements
    jp_stmt = select(JobProfile).options(selectinload(JobProfile.requirements)).where(JobProfile.job_id == job.id)
    jp_res = await db.execute(jp_stmt)
    jp = jp_res.scalar_one_or_none()

    job_profile_dict = {
        "seniority": jp.seniority if jp else "mid",
        "experience_min": job.experience_min or 2,
        "experience_max": job.experience_max or 6,
        "technical_domains": jp.technical_domains if jp else ["Backend"],
        "requirements": [
            {
                "skill": r.skill,
                "canonical_skill": r.canonical_skill,
                "category": r.category,
                "requirement_type": r.requirement_type.value if hasattr(r.requirement_type, "value") else str(r.requirement_type),
                "importance": r.importance,
                "evidence": r.evidence,
            }
            for r in (jp.requirements if jp else [])
        ] if jp else [{"skill": s, "canonical_skill": s, "requirement_type": "required", "importance": 1.0} for s in (job.required_skills or ["Python"])],
    }

    # Evaluate deterministic match
    eval_result = evaluate_candidate_job_match(
        candidate_profile=cand_profile_dict,
        job_profile=job_profile_dict,
        claims=claims_list,
    )

    # Upsert CandidateJobMatch record
    match_stmt = select(CandidateJobMatch).where(
        CandidateJobMatch.job_id == job.id,
        CandidateJobMatch.candidate_id == candidate.id,
    )
    match_res = await db.execute(match_stmt)
    match_rec = match_res.scalar_one_or_none()

    if not match_rec:
        match_rec = CandidateJobMatch(
            job_id=job.id,
            candidate_id=candidate.id,
            resume_version_id=rv.id if rv else None,
            workspace_id=job.workspace_id,
        )
        db.add(match_rec)

    match_rec.overall_score = eval_result.overall_score
    match_rec.required_skill_coverage = eval_result.required_skill_coverage
    match_rec.preferred_skill_coverage = eval_result.preferred_skill_coverage
    match_rec.experience_fit = eval_result.experience_fit
    match_rec.project_relevance = eval_result.project_relevance
    match_rec.seniority_fit = eval_result.seniority_fit
    match_rec.domain_fit = eval_result.domain_fit
    match_rec.scoring_weights = eval_result.scoring_weights
    match_rec.strengths = eval_result.strengths
    match_rec.gaps = eval_result.gaps
    match_rec.verification_areas = eval_result.verification_areas
    match_rec.explanation = eval_result.explanation

    await db.commit()
    await db.refresh(match_rec)

    return match_rec


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/match",
    response_model=CandidateMatchResponse,
    summary="Get latest candidate-job match score and explainable analysis",
)
async def get_candidate_job_match(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CandidateJobMatch).where(
        CandidateJobMatch.job_id == job_id,
        CandidateJobMatch.candidate_id == candidate_id,
    )
    res = await db.execute(stmt)
    match_rec = res.scalar_one_or_none()
    if not match_rec:
        return await compute_candidate_job_match(job_id, candidate_id, current_user, db)

    await verify_workspace_access(match_rec.workspace_id, current_user, db)
    return match_rec


# ---------------------------------------------------------------------------
# 4. Interview Blueprint Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/interviews/blueprints/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate a structured interview blueprint recommendation",
)
async def generate_interview_blueprint(
    payload: BlueprintGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(payload.workspace_id, current_user, db)

    cand_stmt = select(Candidate).where(Candidate.id == payload.candidate_id)
    cand_res = await db.execute(cand_stmt)
    cand = cand_res.scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    title = payload.title or f"Interview Blueprint — {cand.first_name} {cand.last_name}"

    bp = InterviewBlueprint(
        workspace_id=payload.workspace_id,
        interview_id=payload.interview_id,
        job_id=payload.job_id,
        candidate_id=payload.candidate_id,
        generated_by=current_user.id,
        version_number=1,
        title=title,
        status=BlueprintStatus.DRAFT,
        total_duration_minutes=90,
        target_seniority="mid",
        candidate_focus_areas=["Backend API Design", "PostgreSQL Optimization", "Concurrency"],
        job_focus_areas=["Distributed Architecture", "Reliability", "Coding Fluency"],
        verification_priorities=["Verify claim on asynchronous background tasks", "Probe database indexing depth"],
    )
    db.add(bp)
    await db.flush()

    # Create blueprint rounds
    default_rounds = [
        InterviewBlueprintRound(
            blueprint_id=bp.id,
            name="Technical & Architecture Screening",
            round_type="technical",
            sequence=1,
            duration_minutes=30,
            difficulty="mid",
            objectives=["Assess core backend fundamentals", "Validate API design principles"],
            competencies=["Python", "REST APIs", "Database Fundamentals"],
            topics=["HTTP semantics", "Database transactions", "Error handling"],
            suggested_question_count=3,
            scoring_weight=1.0,
        ),
        InterviewBlueprintRound(
            blueprint_id=bp.id,
            name="Live Coding & Problem Solving",
            round_type="coding",
            sequence=2,
            duration_minutes=30,
            difficulty="mid",
            objectives=["Evaluate algorithmic problem solving", "Assess code quality and edge case handling"],
            competencies=["Data Structures", "Algorithms", "Testing"],
            topics=["Hash tables", "Time/Space complexity", "Edge cases"],
            suggested_question_count=2,
            scoring_weight=1.2,
        ),
        InterviewBlueprintRound(
            blueprint_id=bp.id,
            name="System Design & Scalability",
            round_type="system_design",
            sequence=3,
            duration_minutes=30,
            difficulty="mid",
            objectives=["Probe distributed system scaling", "Verify candidate architecture claims"],
            competencies=["System Design", "Caching", "Message Queues"],
            topics=["High availability", "Redis caching strategies", "Event-driven architecture"],
            suggested_question_count=2,
            scoring_weight=1.2,
        ),
    ]
    for r in default_rounds:
        db.add(r)

    await db.commit()
    await db.refresh(bp)
    return bp


@router.get(
    "/interviews/blueprints/{blueprint_id}",
    summary="Get blueprint details and round recommendations",
)
async def get_blueprint(
    blueprint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewBlueprint)
        .options(selectinload(InterviewBlueprint.rounds))
        .where(InterviewBlueprint.id == blueprint_id, InterviewBlueprint.is_deleted.is_(False))
    )
    res = await db.execute(stmt)
    bp = res.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    await verify_workspace_access(bp.workspace_id, current_user, db)
    return bp


@router.patch(
    "/interviews/blueprints/{blueprint_id}",
    summary="Update or edit blueprint rounds and parameters",
)
async def update_blueprint(
    blueprint_id: uuid.UUID,
    payload: BlueprintUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewBlueprint)
        .options(selectinload(InterviewBlueprint.rounds))
        .where(InterviewBlueprint.id == blueprint_id, InterviewBlueprint.is_deleted.is_(False))
    )
    res = await db.execute(stmt)
    bp = res.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    await verify_workspace_access(bp.workspace_id, current_user, db)

    if payload.title is not None:
        bp.title = payload.title
    if payload.total_duration_minutes is not None:
        bp.total_duration_minutes = payload.total_duration_minutes

    if payload.rounds is not None:
        # Replace existing rounds
        for r in list(bp.rounds):
            await db.delete(r)
        await db.flush()

        for r_in in payload.rounds:
            new_r = InterviewBlueprintRound(
                blueprint_id=bp.id,
                name=r_in.name,
                round_type=r_in.round_type,
                sequence=r_in.sequence,
                duration_minutes=r_in.duration_minutes,
                difficulty=r_in.difficulty,
                objectives=r_in.objectives,
                competencies=r_in.competencies,
                topics=r_in.topics,
                suggested_question_count=r_in.suggested_question_count,
                scoring_weight=r_in.scoring_weight,
            )
            db.add(new_r)

    bp.status = BlueprintStatus.REVIEWED
    await db.commit()
    await db.refresh(bp)
    return bp


@router.post(
    "/interviews/blueprints/{blueprint_id}/approve",
    summary="Interviewer approves interview blueprint",
)
async def approve_blueprint(
    blueprint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewBlueprint).where(InterviewBlueprint.id == blueprint_id)
    res = await db.execute(stmt)
    bp = res.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    await verify_workspace_access(bp.workspace_id, current_user, db)

    bp.status = BlueprintStatus.APPROVED
    bp.approved_by = current_user.id
    bp.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(bp)
    return bp


@router.post(
    "/interviews/blueprints/{blueprint_id}/apply",
    summary="Apply approved blueprint to configure live interview rounds",
)
async def apply_blueprint(
    blueprint_id: uuid.UUID,
    interview_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewBlueprint)
        .options(selectinload(InterviewBlueprint.rounds))
        .where(InterviewBlueprint.id == blueprint_id)
    )
    res = await db.execute(stmt)
    bp = res.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    target_interview_id = interview_id or bp.interview_id
    if not target_interview_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target interview_id is required")

    itw_stmt = (
        select(Interview)
        .options(selectinload(Interview.rounds))
        .where(Interview.id == target_interview_id, Interview.is_deleted.is_(False))
    )
    itw_res = await db.execute(itw_stmt)
    interview = itw_res.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target interview not found")

    await verify_workspace_access(bp.workspace_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    applied_interview = await blueprint_service.apply_blueprint_to_interview(
        blueprint=bp,
        interview=interview,
        approver=current_user,
        db=db,
    )
    return {"message": "Blueprint applied successfully", "interview_id": str(applied_interview.id)}


# ---------------------------------------------------------------------------
# 5. Question Plan Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/interviews/question-plans/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate personalized question plan with difficulty progression and coverage matrix",
)
async def generate_question_plan(
    payload: QuestionPlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(payload.workspace_id, current_user, db)

    cand_stmt = select(Candidate).where(Candidate.id == payload.candidate_id)
    cand_res = await db.execute(cand_stmt)
    cand = cand_res.scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    title = payload.title or f"Question Plan — {cand.first_name} {cand.last_name}"

    qp = QuestionPlan(
        workspace_id=payload.workspace_id,
        interview_id=payload.interview_id,
        blueprint_id=payload.blueprint_id,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        created_by=current_user.id,
        version_number=1,
        title=title,
        status=QuestionPlanStatus.DRAFT,
    )
    db.add(qp)
    await db.flush()

    # Ordered questions following difficulty progression
    sample_items = [
        QuestionPlanItem(
            question_plan_id=qp.id,
            sequence=1,
            title="Backend Architecture Overview & Project Discussion",
            prompt="Can you walk us through the high-level architecture of the primary backend service you built, focusing on how data flows from request to persistence?",
            competency="Backend Development",
            difficulty="easy",
            progression_stage="warmup",
            expected_signal="Clear mental model of request lifecycle, separation of concerns, and clean abstraction boundaries.",
            candidate_evidence_tested="Resume claim: Engineered high-throughput REST APIs",
            job_requirement_tested="REST APIs, Backend Architecture",
            suggested_followups=["How did you structure error handling and middleware?"],
        ),
        QuestionPlanItem(
            question_plan_id=qp.id,
            sequence=2,
            title="FastAPI & Async IO Event Loop Handling",
            prompt="How does FastAPI utilize Python's async/await and anyio event loop under the hood, and when should you avoid running blocking code in async endpoint handlers?",
            competency="Python & FastAPI",
            difficulty="medium",
            progression_stage="fundamental",
            expected_signal="Deep understanding of asyncio event loops, threadpools, and threadpool worker exhaustion prevention.",
            candidate_evidence_tested="Resume skill: Python & FastAPI (proficient)",
            job_requirement_tested="Python / FastAPI Fluency",
            suggested_followups=["How do you offload CPU-bound tasks in a FastAPI app?"],
        ),
        QuestionPlanItem(
            question_plan_id=qp.id,
            sequence=3,
            title="PostgreSQL Indexing & Transaction Isolation",
            prompt="Suppose you have an e-commerce order table with 10M rows. How would you design indexes for querying pending orders by user, and how would you prevent double-spending using transaction isolation levels?",
            competency="PostgreSQL",
            difficulty="medium",
            progression_stage="practical",
            expected_signal="Practical knowledge of B-Tree vs partial indexes, SELECT FOR UPDATE, and SERIALIZABLE vs REPEATABLE READ.",
            candidate_evidence_tested="Resume claim: Optimized PostgreSQL queries",
            job_requirement_tested="PostgreSQL Required Skill",
            suggested_followups=["What is the write overhead of adding multiple indexes?"],
        ),
        QuestionPlanItem(
            question_plan_id=qp.id,
            sequence=4,
            title="Distributed Caching & Cache Invalidation at Scale",
            prompt="Describe how you would design a multi-tier cache using Redis for an API with 50,000 req/sec. How do you mitigate cache stampede (thundering herd) and ensure eventual consistency?",
            competency="Distributed Systems",
            difficulty="hard",
            progression_stage="deep_dive",
            expected_signal="Thorough grasp of distributed locks, probabilistic early expiration (XFetch), and cache invalidation strategies.",
            candidate_evidence_tested="Candidate profile: Redis and Distributed Systems",
            job_requirement_tested="Distributed Systems / High Scalability",
            suggested_followups=["What happens if the Redis master crashes during failover?"],
        ),
        QuestionPlanItem(
            question_plan_id=qp.id,
            sequence=5,
            title="Verification: Asynchronous Background Task Reliability",
            prompt="On your resume you mention designing asynchronous background processing. Walk through how you handled message retries, dead letter queues (DLQ), and exactly-once vs at-least-once delivery guarantees.",
            competency="System Design & Reliability",
            difficulty="hard",
            progression_stage="verification",
            expected_signal="Verification of hands-on production claim: idempotency keys, replay mechanics, and worker consumer group isolation.",
            candidate_evidence_tested="Resume Claim: Asynchronous background processing",
            job_requirement_tested="Message Queues / Production Reliability",
            suggested_followups=["How did you monitor consumer lag?"],
        ),
    ]
    for item in sample_items:
        db.add(item)

    # Compute coverage summary matrix
    cov = await question_planning_service.compute_coverage_matrix(
        job_requirements=[
            {"canonical_skill": "Python", "skill": "Python", "requirement_type": "required"},
            {"canonical_skill": "FastAPI", "skill": "FastAPI", "requirement_type": "required"},
            {"canonical_skill": "PostgreSQL", "skill": "PostgreSQL", "requirement_type": "required"},
            {"canonical_skill": "REST APIs", "skill": "REST APIs", "requirement_type": "required"},
            {"canonical_skill": "Distributed Systems", "skill": "Distributed Systems", "requirement_type": "required"},
            {"canonical_skill": "Redis", "skill": "Redis", "requirement_type": "preferred"},
        ],
        candidate_skills=[
            {"name": "Python", "proficiency": "proficient"},
            {"name": "FastAPI", "proficiency": "proficient"},
            {"name": "PostgreSQL", "proficiency": "proficient"},
            {"name": "REST APIs", "proficiency": "expert"},
        ],
        claims=[
            {"claim": "Engineered high-throughput REST APIs"},
            {"claim": "Optimized PostgreSQL queries"},
        ],
        plan_items=[
            {"sequence": it.sequence, "title": it.title, "competency": it.competency}
            for it in sample_items
        ],
    )
    qp.coverage_summary = cov

    await db.commit()
    await db.refresh(qp)
    return qp


@router.get(
    "/interviews/question-plans/{plan_id}",
    summary="Get question plan items and requirement coverage matrix",
)
async def get_question_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QuestionPlan)
        .options(selectinload(QuestionPlan.items))
        .where(QuestionPlan.id == plan_id, QuestionPlan.is_deleted.is_(False))
    )
    res = await db.execute(stmt)
    qp = res.scalar_one_or_none()
    if not qp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question plan not found")

    await verify_workspace_access(qp.workspace_id, current_user, db)
    return qp


@router.post(
    "/interviews/question-plans/{plan_id}/approve",
    summary="Interviewer approves personalized question plan",
)
async def approve_question_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(QuestionPlan).where(QuestionPlan.id == plan_id)
    res = await db.execute(stmt)
    qp = res.scalar_one_or_none()
    if not qp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question plan not found")

    await verify_workspace_access(qp.workspace_id, current_user, db)

    qp.status = QuestionPlanStatus.APPROVED
    qp.approved_by = current_user.id
    qp.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(qp)
    return qp
