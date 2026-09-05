"""
InterviewOS — Production Database Migration Script (Phase 16.2)
Safely executes Alembic migrations up to head against PostgreSQL / Neon.
"""

import os
import sys
import subprocess
import urllib.parse


def sanitize_url(raw_url: str) -> str:
    """Masks password and user details for safe logging."""
    try:
        parsed = urllib.parse.urlparse(raw_url)
        netloc = parsed.hostname or "unknown"
        if parsed.port:
            netloc += f":{parsed.port}"
        return f"{parsed.scheme}://***:***@{netloc}{parsed.path}"
    except Exception:
        return "postgresql+asyncpg://***:***@hidden/db"


def normalize_database_url(url: str) -> str:
    """Normalizes and sanitizes DATABASE_URL for SQLAlchemy + asyncpg."""
    if not url or not isinstance(url, str):
        return url

    cleaned = url.strip()
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql+asyncpg://" + cleaned[len("postgres://"):]
    elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+asyncpg://"):
        cleaned = "postgresql+asyncpg://" + cleaned[len("postgresql://"):]

    try:
        parsed = urllib.parse.urlparse(cleaned)
        params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        UNSUPPORTED_ASYNC_PARAMS = {
            "channel_binding",
            "gssencmode",
            "sslrootcert",
            "sslcert",
            "sslkey",
            "sslpassword",
        }
        new_params = []
        has_ssl = False
        for k, val in params:
            if k.lower() in UNSUPPORTED_ASYNC_PARAMS:
                continue
            if k.lower() == "sslmode":
                if val.lower() != "disable":
                    new_params.append(("ssl", "require"))
                    has_ssl = True
                continue
            if k.lower() == "ssl":
                has_ssl = True
                new_params.append((k, val))
                continue
            new_params.append((k, val))

        host = parsed.hostname or ""
        cloud_hosts = [
            "neon.tech",
            "amazonaws.com",
            "supabase.com",
            "cockroachlabs.cloud",
            "elephantsql.com",
        ]
        if any(c in host for c in cloud_hosts) and not has_ssl:
            new_params.append(("ssl", "require"))

        new_query = urllib.parse.urlencode(new_params)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))
    except Exception:
        if "sslmode=require" in cleaned:
            cleaned = cleaned.replace("sslmode=require", "ssl=require")
        return cleaned


def run_migrations(target_url: str = None) -> bool:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(root_dir, "apps", "api")

    env = os.environ.copy()
    db_url = target_url or env.get("DATABASE_URL")

    if not db_url:
        try:
            sys.path.insert(0, api_dir)
            from app.core.config import settings
            db_url = settings.DATABASE_URL
        except Exception:
            db_url = None

    if db_url:
        db_url = normalize_database_url(db_url)
        env["DATABASE_URL"] = db_url
        print(f"\n[InterviewOS] Starting Production Alembic Migrations against: {sanitize_url(db_url)}")
    else:
        print("\n[InterviewOS] Starting Production Alembic Migrations...")

    # Run alembic upgrade head
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    result = subprocess.run(cmd, cwd=api_dir, env=env, capture_output=True, text=True)

    if result.returncode == 0:
        print("  [PASS] Alembic migrations applied successfully.")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print("  [FAIL] Alembic migration failed:")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        return False


if __name__ == "__main__":
    cli_url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_migrations(cli_url)
    sys.exit(0 if success else 1)
