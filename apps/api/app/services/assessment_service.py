import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coding import (
    CodingAssessment,
    CodingExecutionJob,
    CodingExecutionResult,
    CodingFile,
    CodingProblem,
    CodingProblemVersion,
    CodingSession,
    CodingSessionProblem,
    CodingSnapshot,
    CodingSnapshotReason,
    CodingTestCase,
    ExecutionJobStatus,
    ExecutionResultStatus,
    SessionProblemStatus,
    SubmissionStatus,
    CodingSubmission,
)
from app.models.session import InterviewSession
from app.models.user import User, UserRole
from app.schemas.problem import (
    AssessmentSummaryResponse,
    ProblemAssignRequest,
    ProblemSubmitRequest,
    SessionProblemResponse,
    SubmissionResponse,
)
from app.services.session_service import session_service
from app.services.coding_service import coding_service

# Add code-runner to path for local sandbox execution
runner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../code-runner"))
if runner_path not in sys.path:
    sys.path.insert(0, runner_path)

try:
    from sandbox_executor import sandbox_executor
except ImportError:
    sandbox_executor = None


class AssessmentService:
    async def assign_problem_to_session(
        self,
        coding_session_id: uuid.UUID,
        request: ProblemAssignRequest,
        user: User,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> SessionProblemResponse:
        """Assigns a problem version to an interview coding session."""
        if not is_interviewer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only interviewers can assign coding problems to the session",
            )

        coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
        session = await session_service.get_session(coding_session.interview_session_id, db)

        # Resolve problem version
        version_query = (
            select(CodingProblemVersion)
            .options(
                selectinload(CodingProblemVersion.problem),
                selectinload(CodingProblemVersion.test_cases),
            )
        )
        if request.problem_version_id:
            version_query = version_query.where(CodingProblemVersion.id == request.problem_version_id)
        else:
            version_query = version_query.where(CodingProblemVersion.problem_id == request.problem_id).order_by(
                CodingProblemVersion.version_number.desc()
            )

        res = await db.execute(version_query)
        problem_version = res.scalars().first()
        if not problem_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem or problem version not found")

        # Create or update CodingSessionProblem
        order_num = request.order or (len(coding_session.session_problems) + 1)
        session_problem = CodingSessionProblem(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            problem_version_id=problem_version.id,
            order=order_num,
            assigned_at=datetime.now(timezone.utc),
            assigned_by=user.id,
            started_at=datetime.now(timezone.utc),
            status=SessionProblemStatus.ASSIGNED,
            score=0.0,
        )
        db.add(session_problem)

        # Update coding session active problem
        coding_session.problem_id = problem_version.problem_id
        coding_session.active_problem_version_id = problem_version.id
        coding_session.updated_at = datetime.now(timezone.utc)

        # Populate starter code in workspace files if defined
        starter_codes = problem_version.starter_codes or {}
        chosen_lang = coding_session.language or "python"
        starter_content = starter_codes.get(chosen_lang)

        if starter_content and coding_session.files:
            # Update main file with problem starter code
            main_file = coding_session.files[0]
            main_file.content = starter_content
            main_file.language = chosen_lang
            main_file.updated_at = datetime.now(timezone.utc)

            # Create snapshot for problem assignment
            snapshot = CodingSnapshot(
                id=uuid.uuid4(),
                coding_session_id=coding_session.id,
                created_by=user.id,
                reason=CodingSnapshotReason.SESSION_START,
                files_json=[{
                    "path": main_file.path,
                    "name": main_file.name,
                    "language": main_file.language,
                    "content": main_file.content,
                }],
            )
            db.add(snapshot)

        # Log monotonic event
        await session_service.log_event(
            session=session,
            event_type="CODING_PROBLEM_ASSIGNED",
            actor_id=user.id,
            actor_role="interviewer",
            payload={
                "problem_id": str(problem_version.problem_id),
                "problem_version_id": str(problem_version.id),
                "problem_title": problem_version.problem.title if problem_version.problem else "Problem",
                "difficulty": problem_version.problem.difficulty.value if problem_version.problem else "medium",
                "order": order_num,
            },
            db=db,
        )

        await db.commit()
        await db.refresh(session_problem)

        return SessionProblemResponse(
            id=session_problem.id,
            coding_session_id=session_problem.coding_session_id,
            problem_version_id=session_problem.problem_version_id,
            order=session_problem.order,
            assigned_at=session_problem.assigned_at,
            started_at=session_problem.started_at,
            completed_at=session_problem.completed_at,
            status=session_problem.status.value,
            score=session_problem.score,
        )

    async def submit_solution(
        self,
        coding_session_id: uuid.UUID,
        request: ProblemSubmitRequest,
        user: User,
        is_interviewer: bool,
        db: AsyncSession,
    ) -> SubmissionResponse:
        """Executes candidate code against both public and hidden test cases, computes score, and records submission."""
        coding_session = await coding_service.get_coding_session_or_404(coding_session_id, db)
        session = await session_service.get_session(coding_session.interview_session_id, db)

        if not coding_session.active_problem_version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No problem is currently assigned to this coding session",
            )

        # Fetch problem version with test cases
        res = await db.execute(
            select(CodingProblemVersion)
            .options(
                selectinload(CodingProblemVersion.test_cases),
                selectinload(CodingProblemVersion.problem),
            )
            .where(CodingProblemVersion.id == coding_session.active_problem_version_id)
        )
        problem_version = res.scalar_one_or_none()
        if not problem_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem version not found")

        # 1. Resolve files
        files_to_run = request.files or [
            {"path": f.path, "name": f.name, "language": f.language, "content": f.content}
            for f in coding_session.files
        ]

        # 2. Create immutable submission snapshot
        snapshot = CodingSnapshot(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            created_by=user.id,
            reason=CodingSnapshotReason.SUBMISSION,
            files_json=files_to_run,
        )
        db.add(snapshot)
        await db.flush()

        # 3. Create execution job
        execution_job = CodingExecutionJob(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            requested_by=user.id,
            snapshot_id=snapshot.id,
            status=ExecutionJobStatus.RUNNING,
            language=request.language or coding_session.language,
            is_submission=True,
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution_job)
        await db.flush()

        # 4. Prepare test cases (Public + Hidden)
        test_cases_data = [
            {
                "id": str(tc.id),
                "title": tc.title,
                "input_data": tc.input_data,
                "expected_output": tc.expected_output,
                "is_hidden": tc.is_hidden,
                "timeout_seconds": tc.timeout_seconds or problem_version.time_limit_seconds,
            }
            for tc in problem_version.test_cases
        ]

        # 5. Run isolated Docker sandbox
        raw_res = None
        if sandbox_executor is not None:
            raw_res = sandbox_executor.execute(
                execution_id=str(execution_job.id),
                session_id=str(coding_session.id),
                language_id=execution_job.language,
                files=files_to_run,
                test_cases=test_cases_data if test_cases_data else None,
                timeout_seconds=problem_version.time_limit_seconds,
            )

        # 6. Evaluate Scoring & Verdict
        status_verdict = SubmissionStatus.ACCEPTED
        total_tests = len(test_cases_data)
        tests_passed = raw_res.tests_passed if raw_res else 0
        tests_failed = raw_res.tests_failed if raw_res else 0
        duration_ms = raw_res.duration_ms if raw_res else 0
        memory_bytes = raw_res.memory_bytes if raw_res else 0

        if raw_res:
            if raw_res.status == "compile_error":
                status_verdict = SubmissionStatus.COMPILE_ERROR
            elif raw_res.status == "timed_out":
                status_verdict = SubmissionStatus.TIME_LIMIT_EXCEEDED
            elif raw_res.status == "runtime_error":
                status_verdict = SubmissionStatus.RUNTIME_ERROR
            elif tests_failed > 0:
                status_verdict = SubmissionStatus.WRONG_ANSWER
            else:
                status_verdict = SubmissionStatus.ACCEPTED

        # Calculate weighted score
        calculated_score = 0.0
        if total_tests > 0:
            calculated_score = round((tests_passed / total_tests) * 100.0, 2)

        # Persist Execution Result
        exec_result = CodingExecutionResult(
            id=uuid.uuid4(),
            execution_job_id=execution_job.id,
            status=ExecutionResultStatus.PASSED if status_verdict == SubmissionStatus.ACCEPTED else ExecutionResultStatus.FAILED,
            exit_code=raw_res.exit_code if raw_res else 0,
            stdout=raw_res.stdout if raw_res else "",
            stderr=raw_res.stderr if raw_res else "",
            compile_output=raw_res.compile_output if raw_res else None,
            duration_ms=duration_ms,
            memory_bytes=memory_bytes,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            test_results_json=raw_res.test_results if raw_res else [],
        )
        db.add(exec_result)

        execution_job.status = ExecutionJobStatus.COMPLETED
        execution_job.completed_at = datetime.now(timezone.utc)

        # 7. Get attempt count
        count_res = await db.execute(
            select(func.count(CodingSubmission.id)).where(
                and_(
                    CodingSubmission.coding_session_id == coding_session.id,
                    CodingSubmission.problem_version_id == problem_version.id,
                )
            )
        )
        attempt_number = (count_res.scalar() or 0) + 1

        # 8. Create Submission
        submission = CodingSubmission(
            id=uuid.uuid4(),
            coding_session_id=coding_session.id,
            problem_version_id=problem_version.id,
            candidate_id=user.id,
            submission_number=attempt_number,
            language=execution_job.language,
            snapshot_id=snapshot.id,
            execution_job_id=execution_job.id,
            status=status_verdict,
            score=calculated_score,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            total_tests=total_tests,
            runtime_ms=duration_ms,
            memory_bytes=memory_bytes,
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(submission)

        # 9. Upsert Assessment Summary
        assess_res = await db.execute(
            select(CodingAssessment).where(
                and_(
                    CodingAssessment.coding_session_id == coding_session.id,
                    CodingAssessment.problem_version_id == problem_version.id,
                    CodingAssessment.candidate_id == user.id,
                )
            )
        )
        assessment = assess_res.scalar_one_or_none()
        if not assessment:
            assessment = CodingAssessment(
                id=uuid.uuid4(),
                coding_session_id=coding_session.id,
                problem_version_id=problem_version.id,
                candidate_id=user.id,
                total_submissions=1,
                best_score=calculated_score,
                passed=status_verdict == SubmissionStatus.ACCEPTED,
                evaluation_summary={"latest_status": status_verdict.value, "last_submission_id": str(submission.id)},
            )
            db.add(assessment)
        else:
            assessment.total_submissions += 1
            if calculated_score > assessment.best_score:
                assessment.best_score = calculated_score
            if status_verdict == SubmissionStatus.ACCEPTED:
                assessment.passed = True
            assessment.evaluation_summary = {
                "latest_status": status_verdict.value,
                "last_submission_id": str(submission.id),
                "total_attempts": assessment.total_submissions,
            }
            assessment.updated_at = datetime.now(timezone.utc)

        # 10. Log monotonic event
        await session_service.log_event(
            session=session,
            event_type="CODING_SUBMISSION_CREATED",
            actor_id=user.id,
            actor_role="interviewer" if is_interviewer else "candidate",
            payload={
                "submission_id": str(submission.id),
                "attempt_number": attempt_number,
                "status": status_verdict.value,
                "score": calculated_score,
                "tests_passed": tests_passed,
                "total_tests": total_tests,
            },
            db=db,
        )

        await db.commit()
        await db.refresh(submission)

        # Sanitize test results if caller is candidate
        sanitized_results = coding_service.sanitize_execution_result_for_candidate(exec_result, is_interviewer)

        return SubmissionResponse(
            id=submission.id,
            coding_session_id=submission.coding_session_id,
            session_problem_id=submission.session_problem_id,
            problem_version_id=submission.problem_version_id,
            candidate_id=submission.candidate_id,
            submission_number=submission.submission_number,
            language=submission.language,
            status=submission.status.value,
            score=submission.score,
            tests_passed=submission.tests_passed,
            tests_failed=submission.tests_failed,
            total_tests=submission.total_tests,
            runtime_ms=submission.runtime_ms,
            memory_bytes=submission.memory_bytes,
            submitted_at=submission.submitted_at,
            test_results=[
                {
                    "test_id": tr.test_id,
                    "title": tr.title,
                    "passed": tr.passed,
                    "duration_ms": tr.duration_ms,
                    "error": tr.error,
                    "stdout": tr.stdout,
                    "is_hidden": tr.is_hidden,
                }
                for tr in sanitized_results
            ],
        )

    async def get_submission_history(
        self, coding_session_id: uuid.UUID, problem_version_id: Optional[uuid.UUID], user: User, is_interviewer: bool, db: AsyncSession
    ) -> List[SubmissionResponse]:
        """Retrieves attempt submission history with candidate hidden test sanitization."""
        query = select(CodingSubmission).where(CodingSubmission.coding_session_id == coding_session_id)
        if problem_version_id:
            query = query.where(CodingSubmission.problem_version_id == problem_version_id)

        # If candidate, only see own submissions
        if not is_interviewer:
            query = query.where(CodingSubmission.candidate_id == user.id)

        query = query.order_by(CodingSubmission.submission_number.desc())
        res = await db.execute(query)
        submissions = res.scalars().all()

        return [
            SubmissionResponse(
                id=s.id,
                coding_session_id=s.coding_session_id,
                session_problem_id=s.session_problem_id,
                problem_version_id=s.problem_version_id,
                candidate_id=s.candidate_id,
                submission_number=s.submission_number,
                language=s.language,
                status=s.status.value,
                score=s.score,
                tests_passed=s.tests_passed,
                tests_failed=s.tests_failed,
                total_tests=s.total_tests,
                runtime_ms=s.runtime_ms,
                memory_bytes=s.memory_bytes,
                submitted_at=s.submitted_at,
            )
            for s in submissions
        ]

    async def get_assessment_summary(
        self, coding_session_id: uuid.UUID, problem_version_id: uuid.UUID, user: User, is_interviewer: bool, db: AsyncSession
    ) -> Optional[AssessmentSummaryResponse]:
        """Fetches consolidated score summary for a problem assessment."""
        res = await db.execute(
            select(CodingAssessment).where(
                and_(
                    CodingAssessment.coding_session_id == coding_session_id,
                    CodingAssessment.problem_version_id == problem_version_id,
                )
            )
        )
        assessment = res.scalar_one_or_none()
        if not assessment:
            return None

        # Fetch submissions
        subs = await self.get_submission_history(coding_session_id, problem_version_id, user, is_interviewer, db)

        return AssessmentSummaryResponse(
            id=assessment.id,
            coding_session_id=assessment.coding_session_id,
            problem_version_id=assessment.problem_version_id,
            candidate_id=assessment.candidate_id,
            total_submissions=assessment.total_submissions,
            best_score=assessment.best_score,
            passed=assessment.passed,
            evaluation_summary=assessment.evaluation_summary or {},
            submissions=subs,
            updated_at=assessment.updated_at,
        )


assessment_service = AssessmentService()
