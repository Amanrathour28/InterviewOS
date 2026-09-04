# Code Execution & Docker Sandbox Security

## Overview
InterviewOS executes untrusted user-submitted code in isolated Docker containers with strict security constraints.

---

## 1. Sandbox Isolation Model

```
Untrusted Code Execution Request
               │
               ▼
      Celery Task Worker
               │
               ▼
     DockerSandboxExecutor
               │
               ▼
  ┌─────────────────────────┐
  │   Disposable Container  │
  │                         │
  │ • --network none        │ (Zero outbound/inbound network)
  │ • --pids-limit 64       │ (Fork-bomb defense)
  │ • --memory 256m         │ (OOM exhaustion defense)
  │ • --cpus 1.0            │ (CPU exhaustion cap)
  │ • --cap-drop ALL        │ (Drops kernel capabilities)
  │ • no-new-privileges     │ (Prevents privilege escalation)
  │ • ephemeral /workspace  │ (Temporary safe workspace mount)
  │ • non-root user         │ (Runs as unprivileged UID)
  └────────────┬────────────┘
               │
               ▼
    Watchdog Host Timer (5s)
               │
               ▼
  Immediate Container Removal
```

---

## 2. Security Controls

| Threat Vector | Mitigation Strategy |
| :--- | :--- |
| **Network Probing / SSRF** | `--network none` flag completely isolates container from LAN, internet, and internal services (PostgreSQL, Redis, MinIO). |
| **Fork Bombs (`os.fork()`)** | `--pids-limit 64` terminates any attempt to exhaust system processes. |
| **Memory Exhaustion (OOM)** | Hard memory limit of `256m` enforced by cgroups. |
| **Infinite Loops / CPU Hangs** | Host-level timeout watchdog forcefully destroys containers after `timeout_seconds` (default 5s). |
| **File Traversal Attacks** | Strict path validation rejects `..`, drive letters, and leading slashes before writing files to the temporary sandbox directory. |
| **Output Flooding** | Standard output and error streams are truncated to `1MB` max to prevent buffer bloating. |
| **Hidden Test Leakage** | API response sanitizer masks hidden test inputs and expected outputs for candidate callers. |
| **Container Leaks / Orphans** | Execution containers are created with labels `interviewos.execution_id` and removed in `finally` blocks + automatic orphan reaper. |

---

## 3. Supported Languages

| Language | Runner Image | Compile Command | Run Command |
| :--- | :--- | :--- | :--- |
| **Python** | `python:3.11-alpine` | — | `python main.py` |
| **JavaScript** | `node:20-alpine` | — | `node index.js` |
| **TypeScript** | `node:20-alpine` | `esbuild index.ts --bundle` | `node dist.js` |
| **C++** | `gcc:13-alpine` | `g++ -O2 -o solution main.cpp` | `./solution` |
| **C** | `gcc:13-alpine` | `gcc -O2 -o solution main.c` | `./solution` |
| **Go** | `golang:1.22-alpine` | `go build -o solution main.go` | `./solution` |
| **Rust** | `rust:1.78-alpine` | `rustc -O -o solution main.rs` | `./solution` |
| **Java** | `eclipse-temurin:21-alpine` | `javac Main.java` | `java Main` |
| **SQL** | `python:3.11-alpine` | — | `sqlite3 db.sqlite < query.sql` |
