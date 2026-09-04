import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coding import (
    CodingProblem,
    CodingProblemDifficulty,
    CodingProblemStatus,
    CodingProblemVersion,
    CodingTestCase,
)
from app.models.user import User, UserRole
from app.models.workspace import WorkspaceMembership
from app.schemas.problem import (
    ProblemCreateRequest,
    ProblemUpdateRequest,
    ProblemCloneRequest,
    TestCaseCreateRequest,
    TestCaseUpdateRequest,
    TestCaseResponse,
    ProblemSummaryResponse,
    ProblemDetailResponse,
    ProblemVersionResponse,
)


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s_-]+", "-", s).strip("-")


class ProblemService:
    async def check_problem_access(
        self, problem: CodingProblem, user: User, db: AsyncSession, require_write: bool = False
    ) -> bool:
        """Enforces tenant isolation between system problems and workspace problems."""
        # Platform admins can read and write all problems
        if user.role == UserRole.PLATFORM_ADMIN:
            return True

        # System problems: anyone can read; only platform admin can write
        if problem.is_system or problem.workspace_id is None:
            if require_write:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="System problems cannot be modified by workspace users",
                )
            return True

        # Workspace problem: check membership
        mem_res = await db.execute(
            select(WorkspaceMembership).where(
                and_(
                    WorkspaceMembership.workspace_id == problem.workspace_id,
                    WorkspaceMembership.user_id == user.id,
                )
            )
        )
        membership = mem_res.scalar_one_or_none()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found in your workspace",
            )

        if require_write and user.role == UserRole.CANDIDATE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates cannot author or modify coding problems",
            )

        return True

    async def create_problem(
        self, request: ProblemCreateRequest, user: User, db: AsyncSession
    ) -> CodingProblem:
        """Creates a coding problem with initial immutable version (version 1) and test cases."""
        if user.role == UserRole.CANDIDATE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates cannot author coding problems",
            )

        # System problem authorization check
        if request.is_system and user.role != UserRole.PLATFORM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only platform administrators can create system-wide library problems",
            )

        slug = slugify(request.title)
        # Verify unique slug within workspace or system
        unique_check = await db.execute(
            select(CodingProblem).where(
                and_(
                    CodingProblem.workspace_id == request.workspace_id,
                    CodingProblem.slug == slug,
                )
            )
        )
        if unique_check.scalar_one_or_none():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        problem = CodingProblem(
            id=uuid.uuid4(),
            workspace_id=request.workspace_id if not request.is_system else None,
            created_by=user.id,
            title=request.title,
            slug=slug,
            short_description=request.short_description or "",
            difficulty=CodingProblemDifficulty(request.difficulty.lower()),
            category=request.category.lower(),
            status=CodingProblemStatus.PUBLISHED,
            estimated_duration_minutes=request.estimated_duration_minutes,
            default_time_limit_seconds=request.default_time_limit_seconds,
            default_memory_limit_mb=request.default_memory_limit_mb,
            tags=request.tags or [],
            is_system=request.is_system,
        )
        db.add(problem)
        await db.flush()

        # Create Version 1
        initial_version = CodingProblemVersion(
            id=uuid.uuid4(),
            problem_id=problem.id,
            version_number=1,
            problem_statement=request.problem_statement or request.short_description or "",
            examples=request.examples or [],
            constraints=request.constraints or [],
            expected_time_complexity=request.expected_time_complexity,
            expected_space_complexity=request.expected_space_complexity,
            starter_codes=request.starter_codes or {},
            scoring_policy=request.scoring_policy or {"public_test_weight": 0.2, "hidden_test_weight": 0.8},
            time_limit_seconds=request.default_time_limit_seconds,
            memory_limit_mb=request.default_memory_limit_mb,
            created_by=user.id,
        )
        db.add(initial_version)
        await db.flush()

        problem.current_version_id = initial_version.id

        # Add initial test cases
        if request.test_cases:
            for i, tc in enumerate(request.test_cases):
                test_case = CodingTestCase(
                    id=uuid.uuid4(),
                    problem_version_id=initial_version.id,
                    coding_session_id=None,
                    title=tc.title,
                    input_data=tc.input_data or "",
                    expected_output=tc.expected_output or "",
                    explanation=tc.explanation or "",
                    is_hidden=tc.is_hidden,
                    weight=tc.weight,
                    order=tc.order if tc.order is not None else i,
                    timeout_seconds=tc.timeout_seconds,
                )
                db.add(test_case)

        await db.commit()
        await db.refresh(problem)
        return problem

    async def get_problem_or_404(
        self, problem_id: uuid.UUID, user: User, db: AsyncSession, require_write: bool = False
    ) -> CodingProblem:
        result = await db.execute(
            select(CodingProblem)
            .options(
                selectinload(CodingProblem.versions).selectinload(CodingProblemVersion.test_cases)
            )
            .where(CodingProblem.id == problem_id)
        )
        problem = result.scalar_one_or_none()
        if not problem:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

        await self.check_problem_access(problem, user, db, require_write=require_write)
        return problem

    async def get_problem_detail(
        self, problem_id: uuid.UUID, user: User, db: AsyncSession
    ) -> ProblemDetailResponse:
        problem = await self.get_problem_or_404(problem_id, user, db, require_write=False)
        is_interviewer = user.role in (UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_ADMIN, UserRole.RECRUITER)

        # Resolve active / latest version
        latest_version = None
        if problem.versions:
            # find version matching current_version_id or highest version_number
            if problem.current_version_id:
                latest_version = next((v for v in problem.versions if v.id == problem.current_version_id), problem.versions[0])
            else:
                latest_version = problem.versions[0]

        version_res = None
        if latest_version:
            # Sanitize test cases for candidates
            test_cases_res = []
            for tc in latest_version.test_cases:
                if tc.is_hidden and not is_interviewer:
                    # Mask hidden test case input/output for candidates
                    test_cases_res.append(
                        TestCaseResponse(
                            id=tc.id,
                            problem_version_id=tc.problem_version_id,
                            title=tc.title,
                            input_data=None,
                            expected_output=None,
                            explanation=None,
                            is_hidden=True,
                            weight=tc.weight,
                            order=tc.order,
                            timeout_seconds=tc.timeout_seconds,
                        )
                    )
                else:
                    test_cases_res.append(
                        TestCaseResponse(
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
                    )

            version_res = ProblemVersionResponse(
                id=latest_version.id,
                problem_id=latest_version.problem_id,
                version_number=latest_version.version_number,
                problem_statement=latest_version.problem_statement,
                examples=latest_version.examples or [],
                constraints=latest_version.constraints or [],
                expected_time_complexity=latest_version.expected_time_complexity if is_interviewer else None,
                expected_space_complexity=latest_version.expected_space_complexity if is_interviewer else None,
                starter_codes=latest_version.starter_codes or {},
                scoring_policy=latest_version.scoring_policy or {},
                time_limit_seconds=latest_version.time_limit_seconds,
                memory_limit_mb=latest_version.memory_limit_mb,
                test_cases=test_cases_res,
                created_at=latest_version.created_at,
            )

        return ProblemDetailResponse(
            id=problem.id,
            workspace_id=problem.workspace_id,
            created_by=problem.created_by,
            title=problem.title,
            slug=problem.slug,
            short_description=problem.short_description,
            difficulty=problem.difficulty.value,
            category=problem.category,
            status=problem.status.value,
            estimated_duration_minutes=problem.estimated_duration_minutes,
            default_time_limit_seconds=problem.default_time_limit_seconds,
            default_memory_limit_mb=problem.default_memory_limit_mb,
            tags=problem.tags or [],
            is_system=problem.is_system,
            current_version_id=problem.current_version_id,
            current_version=version_res,
            versions_count=len(problem.versions),
            created_at=problem.created_at,
            updated_at=problem.updated_at,
        )

    async def list_problems(
        self,
        workspace_id: Optional[uuid.UUID],
        difficulty: Optional[str],
        category: Optional[str],
        tag: Optional[str],
        scope: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
        user: User,
        db: AsyncSession,
    ) -> Tuple[List[CodingProblem], int]:
        """Lists problems with multi-tenant filtering (system problems + accessible workspace problems)."""
        query = select(CodingProblem).where(CodingProblem.status != CodingProblemStatus.ARCHIVED)

        # Filter by Scope & Workspace
        if scope == "system":
            query = query.where(CodingProblem.is_system == True)
        elif scope == "workspace" and workspace_id:
            query = query.where(CodingProblem.workspace_id == workspace_id)
        elif workspace_id:
            query = query.where(
                or_(CodingProblem.workspace_id == workspace_id, CodingProblem.is_system == True)
            )
        else:
            if user.role != UserRole.PLATFORM_ADMIN:
                query = query.where(CodingProblem.is_system == True)

        # Filters
        if difficulty:
            query = query.where(CodingProblem.difficulty == CodingProblemDifficulty(difficulty.lower()))
        if category:
            query = query.where(CodingProblem.category == category.lower())
        if search:
            query = query.where(
                or_(
                    CodingProblem.title.ilike(f"%{search}%"),
                    CodingProblem.short_description.ilike(f"%{search}%"),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        # Paginate
        query = query.order_by(CodingProblem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        items = res.scalars().all()

        return list(items), total

    async def update_problem(
        self, problem_id: uuid.UUID, request: ProblemUpdateRequest, user: User, db: AsyncSession
    ) -> CodingProblem:
        """Updates problem metadata and generates a new immutable ProblemVersion if assessment details change."""
        problem = await self.get_problem_or_404(problem_id, user, db, require_write=True)

        if request.title is not None:
            problem.title = request.title
        if request.short_description is not None:
            problem.short_description = request.short_description
        if request.difficulty is not None:
            problem.difficulty = CodingProblemDifficulty(request.difficulty.lower())
        if request.category is not None:
            problem.category = request.category.lower()
        if request.estimated_duration_minutes is not None:
            problem.estimated_duration_minutes = request.estimated_duration_minutes
        if request.default_time_limit_seconds is not None:
            problem.default_time_limit_seconds = request.default_time_limit_seconds
        if request.default_memory_limit_mb is not None:
            problem.default_memory_limit_mb = request.default_memory_limit_mb
        if request.tags is not None:
            problem.tags = request.tags
        if request.status is not None:
            problem.status = CodingProblemStatus(request.status.lower())

        problem.updated_at = datetime.now(timezone.utc)

        # Check if version-relevant assessment fields changed
        has_version_change = any([
            request.problem_statement is not None,
            request.examples is not None,
            request.constraints is not None,
            request.expected_time_complexity is not None,
            request.expected_space_complexity is not None,
            request.starter_codes is not None,
            request.scoring_policy is not None,
        ])

        if has_version_change:
            latest_version = problem.versions[0] if problem.versions else None
            next_version_num = (latest_version.version_number + 1) if latest_version else 1

            new_version = CodingProblemVersion(
                id=uuid.uuid4(),
                problem_id=problem.id,
                version_number=next_version_num,
                problem_statement=request.problem_statement if request.problem_statement is not None else (latest_version.problem_statement if latest_version else ""),
                examples=request.examples if request.examples is not None else (latest_version.examples if latest_version else []),
                constraints=request.constraints if request.constraints is not None else (latest_version.constraints if latest_version else []),
                expected_time_complexity=request.expected_time_complexity if request.expected_time_complexity is not None else (latest_version.expected_time_complexity if latest_version else None),
                expected_space_complexity=request.expected_space_complexity if request.expected_space_complexity is not None else (latest_version.expected_space_complexity if latest_version else None),
                starter_codes=request.starter_codes if request.starter_codes is not None else (latest_version.starter_codes if latest_version else {}),
                scoring_policy=request.scoring_policy if request.scoring_policy is not None else (latest_version.scoring_policy if latest_version else {"public_test_weight": 0.2, "hidden_test_weight": 0.8}),
                time_limit_seconds=problem.default_time_limit_seconds,
                memory_limit_mb=problem.default_memory_limit_mb,
                created_by=user.id,
            )
            db.add(new_version)
            await db.flush()

            # Copy test cases from prior version
            if latest_version and latest_version.test_cases:
                for tc in latest_version.test_cases:
                    copied_tc = CodingTestCase(
                        id=uuid.uuid4(),
                        problem_version_id=new_version.id,
                        coding_session_id=None,
                        title=tc.title,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        explanation=tc.explanation,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        order=tc.order,
                        timeout_seconds=tc.timeout_seconds,
                    )
                    db.add(copied_tc)

            problem.current_version_id = new_version.id

        await db.commit()
        await db.refresh(problem)
        return problem

    async def clone_problem(
        self, problem_id: uuid.UUID, request: ProblemCloneRequest, user: User, db: AsyncSession
    ) -> CodingProblem:
        """Creates an independent duplicate clone of a problem and its active version."""
        original = await self.get_problem_or_404(problem_id, user, db, require_write=False)
        target_ws_id = request.target_workspace_id or original.workspace_id

        if user.role == UserRole.CANDIDATE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidates cannot clone problems")

        clone_title = request.new_title or f"{original.title} (Clone)"
        clone_slug = f"{slugify(clone_title)}-{uuid.uuid4().hex[:6]}"

        cloned_problem = CodingProblem(
            id=uuid.uuid4(),
            workspace_id=target_ws_id,
            created_by=user.id,
            title=clone_title,
            slug=clone_slug,
            short_description=original.short_description,
            difficulty=original.difficulty,
            category=original.category,
            status=CodingProblemStatus.PUBLISHED,
            estimated_duration_minutes=original.estimated_duration_minutes,
            default_time_limit_seconds=original.default_time_limit_seconds,
            default_memory_limit_mb=original.default_memory_limit_mb,
            tags=list(original.tags or []),
            is_system=False,
        )
        db.add(cloned_problem)
        await db.flush()

        # Clone current version
        latest_version = original.versions[0] if original.versions else None
        if latest_version:
            cloned_version = CodingProblemVersion(
                id=uuid.uuid4(),
                problem_id=cloned_problem.id,
                version_number=1,
                problem_statement=latest_version.problem_statement,
                examples=list(latest_version.examples or []),
                constraints=list(latest_version.constraints or []),
                expected_time_complexity=latest_version.expected_time_complexity,
                expected_space_complexity=latest_version.expected_space_complexity,
                starter_codes=dict(latest_version.starter_codes or {}),
                scoring_policy=dict(latest_version.scoring_policy or {}),
                time_limit_seconds=latest_version.time_limit_seconds,
                memory_limit_mb=latest_version.memory_limit_mb,
                created_by=user.id,
            )
            db.add(cloned_version)
            await db.flush()

            cloned_problem.current_version_id = cloned_version.id

            # Clone test cases
            for tc in latest_version.test_cases:
                cloned_tc = CodingTestCase(
                    id=uuid.uuid4(),
                    problem_version_id=cloned_version.id,
                    coding_session_id=None,
                    title=tc.title,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    explanation=tc.explanation,
                    is_hidden=tc.is_hidden,
                    weight=tc.weight,
                    order=tc.order,
                    timeout_seconds=tc.timeout_seconds,
                )
                db.add(cloned_tc)

        await db.commit()
        await db.refresh(cloned_problem)
        return cloned_problem

    async def archive_problem(
        self, problem_id: uuid.UUID, user: User, db: AsyncSession
    ) -> CodingProblem:
        """Soft-archives a problem so historical interviews remain reproducible."""
        problem = await self.get_problem_or_404(problem_id, user, db, require_write=True)
        problem.status = CodingProblemStatus.ARCHIVED
        problem.archived_at = datetime.now(timezone.utc)
        problem.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(problem)
        return problem


problem_service = ProblemService()
