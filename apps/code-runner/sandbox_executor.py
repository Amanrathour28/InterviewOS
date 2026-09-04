"""Docker Sandbox Executor for Isolated Untrusted Code Execution."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
import docker
from docker.errors import DockerException, ImageNotFound

from languages import get_language_config, LanguageConfig

MAX_OUTPUT_BYTES = 1024 * 1024  # 1 MB truncation limit


class SandboxResult:
    def __init__(
        self,
        status: str,
        exit_code: Optional[int] = 0,
        stdout: str = "",
        stderr: str = "",
        compile_output: Optional[str] = None,
        duration_ms: int = 0,
        memory_bytes: Optional[int] = 0,
        tests_passed: int = 0,
        tests_failed: int = 0,
        test_results: Optional[List[Dict[str, Any]]] = None,
    ):
        self.status = status
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.compile_output = compile_output
        self.duration_ms = duration_ms
        self.memory_bytes = memory_bytes
        self.tests_passed = tests_passed
        self.tests_failed = tests_failed
        self.test_results = test_results or []


class DockerSandboxExecutor:
    """Executes untrusted candidate code inside disposable, resource-constrained Docker containers."""

    def __init__(self):
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
            # Test ping
            self.docker_client.ping()
        except Exception:
            self.docker_client = None

    @staticmethod
    def _truncate_output(text: str) -> str:
        if len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
            return text[:MAX_OUTPUT_BYTES] + "\n... [Output Truncated: Exceeded 1MB limit]"
        return text

    @staticmethod
    def _safe_write_files(base_dir: str, files: List[Dict[str, Any]]) -> None:
        """Writes submitted files safely to workspace directory, preventing path traversal."""
        real_base = os.path.realpath(base_dir)
        for f in files:
            rel_path = f.get("path") or f.get("name") or "main.py"
            # Normalize path
            norm_rel = os.path.normpath(rel_path.lstrip("/\\"))
            if norm_rel.startswith("..") or os.path.isabs(norm_rel):
                raise ValueError(f"Path traversal detected in file path: {rel_path}")

            target_path = os.path.realpath(os.path.join(real_base, norm_rel))
            if not target_path.startswith(real_base):
                raise ValueError(f"Target path {target_path} is outside sandbox workspace {real_base}")

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            content = f.get("content", "")
            with open(target_path, "w", encoding="utf-8") as out:
                out.write(content)

    def execute(
        self,
        execution_id: str,
        session_id: str,
        language_id: str,
        files: List[Dict[str, Any]],
        test_cases: Optional[List[Dict[str, Any]]] = None,
        custom_input: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> SandboxResult:
        """Runs the sandbox execution lifecycle for the given files and test cases."""
        lang_config = get_language_config(language_id)
        effective_timeout = timeout_seconds or lang_config.timeout_seconds

        with tempfile.TemporaryDirectory(prefix="interviewos_sandbox_") as temp_dir:
            self._safe_write_files(temp_dir, files)

            # Check if we should use Docker or process sandbox fallback
            if self.docker_client is not None:
                try:
                    return self._execute_docker(
                        execution_id=execution_id,
                        session_id=session_id,
                        lang_config=lang_config,
                        workspace_dir=temp_dir,
                        test_cases=test_cases,
                        custom_input=custom_input,
                        timeout_seconds=effective_timeout,
                    )
                except Exception:
                    return self._execute_local_process_sandbox(
                        execution_id=execution_id,
                        lang_config=lang_config,
                        workspace_dir=temp_dir,
                        test_cases=test_cases,
                        custom_input=custom_input,
                        timeout_seconds=effective_timeout,
                    )
            else:
                return self._execute_local_process_sandbox(
                    execution_id=execution_id,
                    lang_config=lang_config,
                    workspace_dir=temp_dir,
                    test_cases=test_cases,
                    custom_input=custom_input,
                    timeout_seconds=effective_timeout,
                )

    def _execute_docker(
        self,
        execution_id: str,
        session_id: str,
        lang_config: LanguageConfig,
        workspace_dir: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str],
        timeout_seconds: float,
    ) -> SandboxResult:
        """Executes inside disposable Docker container."""
        # Ensure image is present locally, else fallback cleanly
        try:
            self.docker_client.images.get(lang_config.docker_image)
        except Exception:
            return self._execute_local_process_sandbox(
                execution_id=execution_id,
                lang_config=lang_config,
                workspace_dir=workspace_dir,
                test_cases=test_cases,
                custom_input=custom_input,
                timeout_seconds=timeout_seconds,
            )

        # Handle Compilation step if language requires it
        compile_output = None
        if lang_config.compile_cmd:
            comp_res = self._run_docker_step(
                cmd=lang_config.compile_cmd,
                image=lang_config.docker_image,
                workspace_dir=workspace_dir,
                timeout=timeout_seconds,
                execution_id=execution_id,
                session_id=session_id,
            )
            if comp_res["exit_code"] != 0 or comp_res["timed_out"]:
                return SandboxResult(
                    status="compile_error" if not comp_res["timed_out"] else "timed_out",
                    exit_code=comp_res["exit_code"],
                    compile_output=self._truncate_output(comp_res["stderr"] or comp_res["stdout"]),
                    stderr=self._truncate_output(comp_res["stderr"]),
                    duration_ms=comp_res["duration_ms"],
                )
            compile_output = self._truncate_output(comp_res["stdout"])

        # Determine evaluation cases: if custom_input provided, run custom test; else test_cases or single run
        eval_cases = []
        if custom_input is not None:
            eval_cases.append({"id": "custom", "title": "Custom Input", "input_data": custom_input, "is_hidden": False})
        elif test_cases and len(test_cases) > 0:
            eval_cases = test_cases
        else:
            eval_cases.append({"id": "default", "title": "Standard Execution", "input_data": "", "is_hidden": False})

        test_results = []
        tests_passed = 0
        tests_failed = 0
        total_duration_ms = 0
        overall_stdout = ""
        overall_stderr = ""
        overall_status = "passed"

        for tc in eval_cases:
            tc_input = tc.get("input_data", "")
            expected_out = tc.get("expected_output")
            tc_timeout = tc.get("timeout_seconds", timeout_seconds)

            step_res = self._run_docker_step(
                cmd=lang_config.run_cmd,
                image=lang_config.docker_image,
                workspace_dir=workspace_dir,
                stdin_data=tc_input,
                timeout=tc_timeout,
                execution_id=execution_id,
                session_id=session_id,
            )

            total_duration_ms += step_res["duration_ms"]
            step_stdout = self._truncate_output(step_res["stdout"])
            step_stderr = self._truncate_output(step_res["stderr"])

            if not overall_stdout and step_stdout:
                overall_stdout = step_stdout
            if not overall_stderr and step_stderr:
                overall_stderr = step_stderr

            if step_res["timed_out"]:
                overall_status = "timed_out"
                test_results.append({
                    "test_id": str(tc.get("id", "")),
                    "title": tc.get("title", "Test"),
                    "passed": False,
                    "duration_ms": step_res["duration_ms"],
                    "error": f"Execution timed out after {tc_timeout} seconds.",
                    "stdout": step_stdout,
                    "is_hidden": tc.get("is_hidden", False),
                })
                tests_failed += 1
                break
            elif step_res["exit_code"] != 0:
                overall_status = "runtime_error"
                test_results.append({
                    "test_id": str(tc.get("id", "")),
                    "title": tc.get("title", "Test"),
                    "passed": False,
                    "duration_ms": step_res["duration_ms"],
                    "error": step_stderr or f"Process exited with non-zero code {step_res['exit_code']}",
                    "stdout": step_stdout,
                    "is_hidden": tc.get("is_hidden", False),
                })
                tests_failed += 1
            else:
                passed = True
                if expected_out is not None:
                    # Normalized string comparison
                    passed = step_stdout.strip() == expected_out.strip()

                if passed:
                    tests_passed += 1
                else:
                    tests_failed += 1
                    overall_status = "failed"

                test_results.append({
                    "test_id": str(tc.get("id", "")),
                    "title": tc.get("title", "Test"),
                    "passed": passed,
                    "duration_ms": step_res["duration_ms"],
                    "stdout": step_stdout,
                    "is_hidden": tc.get("is_hidden", False),
                })

        if overall_status == "passed" and tests_failed > 0:
            overall_status = "failed"

        return SandboxResult(
            status=overall_status,
            exit_code=0 if overall_status == "passed" else 1,
            stdout=overall_stdout,
            stderr=overall_stderr,
            compile_output=compile_output,
            duration_ms=total_duration_ms,
            memory_bytes=step_res.get("memory_bytes", 0),
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            test_results=test_results,
        )

    def _run_docker_step(
        self,
        cmd: str,
        image: str,
        workspace_dir: str,
        timeout: float,
        execution_id: str,
        session_id: str,
        stdin_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs a single command in an isolated Docker container with resource constraints."""
        container = None
        start_time = time.time()
        try:
            # Mount host directory as /workspace
            host_mount_path = os.path.abspath(workspace_dir)

            # Security Configuration:
            # - network_mode="none": ZERO outbound or local network access
            # - pids_limit=64: prevents fork bombs
            # - mem_limit="256m": prevents memory exhaustion
            # - cpu_quota=100000: limits to 1 CPU core
            # - cap_drop=["ALL"]: drops all kernel capabilities
            # - security_opt=["no-new-privileges:true"]: prevents privilege escalation
            # - read-only/writable mounts
            container = self.docker_client.containers.create(
                image=image,
                command=f"/bin/sh -c '{cmd}'",
                volumes={host_mount_path: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                network_mode="none",
                mem_limit="256m",
                pids_limit=64,
                cpu_quota=100000,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                labels={
                    "interviewos.execution_id": str(execution_id),
                    "interviewos.session_id": str(session_id),
                },
                stdin_open=True,
                detach=True,
            )

            # Wait for completion or timeout via polling
            timed_out = False
            exit_code = 0
            poll_interval = 0.1
            elapsed = 0.0
            while elapsed < timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval
                try:
                    container.reload()
                    if container.status != "running":
                        exit_code = container.attrs.get("State", {}).get("ExitCode", 0)
                        break
                except Exception:
                    break
            else:
                timed_out = True
                try:
                    container.kill()
                except Exception:
                    pass

            duration_ms = int((time.time() - start_time) * 1000)

            # Capture stdout / stderr
            stdout = ""
            stderr = ""
            try:
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                stdout = logs
            except Exception:
                pass

            return {
                "exit_code": exit_code if not timed_out else -1,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": timed_out,
                "duration_ms": duration_ms,
                "memory_bytes": 0,
            }
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _execute_local_process_sandbox(
        self,
        execution_id: str,
        lang_config: LanguageConfig,
        workspace_dir: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str],
        timeout_seconds: float,
    ) -> SandboxResult:
        """Process sandbox for local testing when Docker daemon is not active."""
        start_time = time.time()
        compile_output = None

        if lang_config.compile_cmd:
            try:
                comp_cmd = lang_config.compile_cmd
                comp = subprocess.run(
                    comp_cmd,
                    shell=True,
                    cwd=workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                if comp.returncode != 0:
                    return SandboxResult(
                        status="compile_error",
                        exit_code=comp.returncode,
                        compile_output=self._truncate_output(comp.stderr or comp.stdout),
                        stderr=self._truncate_output(comp.stderr),
                        duration_ms=int((time.time() - start_time) * 1000),
                    )
                compile_output = self._truncate_output(comp.stdout)
            except subprocess.TimeoutExpired:
                return SandboxResult(status="timed_out", stderr=f"Compilation timed out after {timeout_seconds}s")

        eval_cases = []
        if custom_input is not None:
            eval_cases.append({"id": "custom", "title": "Custom Input", "input_data": custom_input, "is_hidden": False})
        elif test_cases and len(test_cases) > 0:
            eval_cases = test_cases
        else:
            eval_cases.append({"id": "default", "title": "Standard Execution", "input_data": "", "is_hidden": False})

        test_results = []
        tests_passed = 0
        tests_failed = 0
        total_duration = 0
        overall_stdout = ""
        overall_stderr = ""
        overall_status = "passed"

        for tc in eval_cases:
            tc_input = tc.get("input_data", "")
            expected_out = tc.get("expected_output")
            tc_timeout = tc.get("timeout_seconds", timeout_seconds)

            tc_start = time.time()
            proc = None
            try:
                run_cmd = lang_config.run_cmd
                if run_cmd.startswith("python "):
                    cmd_args = [sys.executable] + run_cmd.split()[1:]
                elif run_cmd.startswith("node "):
                    cmd_args = ["node"] + run_cmd.split()[1:]
                else:
                    cmd_args = run_cmd.split()

                proc = subprocess.Popen(
                    cmd_args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=workspace_dir,
                    text=True,
                )
                stdout_data, stderr_data = proc.communicate(input=tc_input, timeout=tc_timeout)
                tc_dur = int((time.time() - tc_start) * 1000)
                total_duration += tc_dur
                step_stdout = self._truncate_output(stdout_data or "")
                step_stderr = self._truncate_output(stderr_data or "")

                if not overall_stdout:
                    overall_stdout = step_stdout
                if not overall_stderr:
                    overall_stderr = step_stderr

                if proc.returncode != 0:
                    overall_status = "runtime_error"
                    tests_failed += 1
                    test_results.append({
                        "test_id": str(tc.get("id", "")),
                        "title": tc.get("title", "Test"),
                        "passed": False,
                        "duration_ms": tc_dur,
                        "error": step_stderr or f"Exited with code {proc.returncode}",
                        "stdout": step_stdout,
                        "is_hidden": tc.get("is_hidden", False),
                    })
                else:
                    passed = True
                    if expected_out is not None:
                        passed = step_stdout.strip() == expected_out.strip()

                    if passed:
                        tests_passed += 1
                    else:
                        tests_failed += 1
                        overall_status = "failed"

                    test_results.append({
                        "test_id": str(tc.get("id", "")),
                        "title": tc.get("title", "Test"),
                        "passed": passed,
                        "duration_ms": tc_dur,
                        "stdout": step_stdout,
                        "is_hidden": tc.get("is_hidden", False),
                    })
            except subprocess.TimeoutExpired:
                if proc:
                    proc.kill()
                    try:
                        proc.communicate(timeout=0.5)
                    except Exception:
                        pass
                overall_status = "timed_out"
                tc_dur = int((time.time() - tc_start) * 1000)
                total_duration += tc_dur
                tests_failed += 1
                test_results.append({
                    "test_id": str(tc.get("id", "")),
                    "title": tc.get("title", "Test"),
                    "passed": False,
                    "duration_ms": tc_dur,
                    "error": f"Execution timed out after {tc_timeout} seconds.",
                    "stdout": "",
                    "is_hidden": tc.get("is_hidden", False),
                })
                break

        if overall_status == "passed" and tests_failed > 0:
            overall_status = "failed"

        return SandboxResult(
            status=overall_status,
            exit_code=0 if overall_status == "passed" else 1,
            stdout=overall_stdout,
            stderr=overall_stderr,
            compile_output=compile_output,
            duration_ms=total_duration,
            memory_bytes=0,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            test_results=test_results,
        )

    def cleanup_orphaned_containers(self) -> int:
        """Finds and destroys any orphaned containers from previous crashed runs."""
        if not self.docker_client:
            return 0
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": "interviewos.execution_id"},
            )
            cleaned = 0
            for c in containers:
                try:
                    c.remove(force=True)
                    cleaned += 1
                except Exception:
                    pass
            return cleaned
        except Exception:
            return 0


sandbox_executor = DockerSandboxExecutor()
