import sys
import os
import pytest

runner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../code-runner"))
if runner_path not in sys.path:
    sys.path.insert(0, runner_path)

from sandbox_executor import DockerSandboxExecutor, MAX_OUTPUT_BYTES


def test_sandbox_standard_output_and_custom_input():
    executor = DockerSandboxExecutor()
    files = [
        {
            "path": "main.py",
            "name": "main.py",
            "content": "import sys\nname = sys.stdin.read().strip()\nprint(f'Hello, {name}!')\n",
        }
    ]

    res = executor.execute(
        execution_id="exec-test-1",
        session_id="sess-test-1",
        language_id="python",
        files=files,
        custom_input="InterviewOS",
    )

    assert res.status == "passed"
    assert "Hello, InterviewOS!" in res.stdout
    assert res.exit_code == 0


def test_sandbox_runtime_exception():
    executor = DockerSandboxExecutor()
    files = [
        {
            "path": "main.py",
            "name": "main.py",
            "content": "raise ValueError('Intentional Exception Raised')",
        }
    ]

    res = executor.execute(
        execution_id="exec-test-2",
        session_id="sess-test-2",
        language_id="python",
        files=files,
    )

    assert res.status == "runtime_error"
    assert "ValueError" in (res.stderr or res.stdout)
    assert res.exit_code != 0


def test_sandbox_infinite_loop_timeout():
    executor = DockerSandboxExecutor()
    files = [
        {
            "path": "main.py",
            "name": "main.py",
            "content": "import time\nwhile True:\n    time.sleep(0.1)\n",
        }
    ]

    res = executor.execute(
        execution_id="exec-test-3",
        session_id="sess-test-3",
        language_id="python",
        files=files,
        timeout_seconds=1.5,
    )

    assert res.status == "timed_out"
    assert res.tests_failed >= 1


def test_sandbox_output_truncation_limit():
    executor = DockerSandboxExecutor()
    # Generates > 1MB output
    files = [
        {
            "path": "main.py",
            "name": "main.py",
            "content": "for _ in range(30000):\n    print('A' * 100)\n",
        }
    ]

    res = executor.execute(
        execution_id="exec-test-4",
        session_id="sess-test-4",
        language_id="python",
        files=files,
        timeout_seconds=5.0,
    )

    assert len(res.stdout.encode("utf-8")) <= MAX_OUTPUT_BYTES + 500
    assert "[Output Truncated" in res.stdout


def test_sandbox_path_traversal_rejection():
    executor = DockerSandboxExecutor()
    files = [
        {
            "path": "../../etc/shadow",
            "name": "shadow",
            "content": "root:x:0:0::/root:/bin/bash",
        }
    ]

    with pytest.raises(ValueError, match="Path traversal"):
        executor.execute(
            execution_id="exec-test-5",
            session_id="sess-test-5",
            language_id="python",
            files=files,
        )
