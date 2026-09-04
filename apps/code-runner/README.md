# InterviewOS Isolated Code Execution Engine

This service handles:
- Isolated Docker sandbox execution
- Resource constraint enforcement: CPU limits, memory limits, process count, timeout watchdog
- Network isolation (zero outbound network access for untrusted candidate code)
- Public vs hidden test case evaluation
- Supported languages: Python, JavaScript, TypeScript, Go, Rust, Java, C++, SQL

Implementation will proceed in Phase 10.
