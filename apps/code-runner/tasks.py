"""Celery tasks for executing code jobs in Docker sandboxes."""
import json
import logging
from typing import Any, Dict, List, Optional
from celery_app import celery_app
from sandbox_executor import sandbox_executor

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.execute_code_job", bind=True)
def execute_code_job(
    self,
    execution_id: str,
    session_id: str,
    language_id: str,
    files: List[Dict[str, Any]],
    test_cases: Optional[List[Dict[str, Any]]] = None,
    custom_input: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Celery task worker executing untrusted code in Docker sandbox."""
    logger.info(f"[Celery] Starting execution {execution_id} for session {session_id} (Lang: {language_id})")

    result = sandbox_executor.execute(
        execution_id=execution_id,
        session_id=session_id,
        language_id=language_id,
        files=files,
        test_cases=test_cases,
        custom_input=custom_input,
        timeout_seconds=timeout_seconds,
    )

    return {
        "execution_id": execution_id,
        "status": result.status,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "compile_output": result.compile_output,
        "duration_ms": result.duration_ms,
        "memory_bytes": result.memory_bytes,
        "tests_passed": result.tests_passed,
        "tests_failed": result.tests_failed,
        "test_results": result.test_results,
    }
