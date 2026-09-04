"""
InterviewOS — Production Database Migration Script (Phase 16.2)
Safely executes Alembic migrations up to head against PostgreSQL / Neon.
"""

import os
import sys
import subprocess


def run_migrations():
    print("\n[InterviewOS] Starting Production Alembic Migrations...")
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(root_dir, "apps", "api")

    # Run alembic upgrade head
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    result = subprocess.run(cmd, cwd=api_dir, capture_output=True, text=True)

    if result.returncode == 0:
        print("  [PASS] Alembic migrations applied successfully.")
        print(result.stdout)
        return True
    else:
        print("  [FAIL] Alembic migration failed:")
        print(result.stderr)
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
