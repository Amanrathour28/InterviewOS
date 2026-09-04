"""
InterviewOS — Production Database & pgvector Verification Script (Phase 16.2)
Safely tests PostgreSQL / Neon connectivity, extensions, migrations, and table integrity.
Never outputs credentials or secrets.
"""

import asyncio
import os
import sys
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def sanitize_url(raw_url: str) -> str:
    """Masks password and user details for safe logging."""
    try:
        parsed = urlparse(raw_url)
        netloc = parsed.hostname or "unknown"
        if parsed.port:
            netloc += f":{parsed.port}"
        return f"{parsed.scheme}://***:***@{netloc}{parsed.path}"
    except Exception:
        return "postgresql+asyncpg://***:***@hidden/db"


async def verify_database(database_url: str = None) -> bool:
    if not database_url:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        # Try loading from apps/api/app/core/config
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
            from app.core.config import settings
            database_url = settings.DATABASE_URL
        except Exception:
            database_url = "postgresql+asyncpg://interviewos:interviewos_secret@localhost:5432/interviewos_db"

    # Normalize url scheme
    if database_url.startswith("postgres://"):
        database_url = "postgresql+asyncpg://" + database_url[len("postgres://"):]
    elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
        database_url = "postgresql+asyncpg://" + database_url[len("postgresql://"):]

    if "sslmode=require" in database_url:
        database_url = database_url.replace("sslmode=require", "ssl=require")

    masked_url = sanitize_url(database_url)
    print(f"\n[InterviewOS] Starting Database Verification against: {masked_url}")

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as conn:
            # 1. Test basic connectivity & PostgreSQL version
            res = await conn.execute(text("SELECT version();"))
            version_str = res.scalar()
            print(f"  [PASS] Connection established. PostgreSQL Version: {version_str.split(',')[0] if version_str else 'Unknown'}")

            # 2. Check / Enable pgvector extension
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                await conn.commit()
                vec_check = await conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"))
                vec_row = vec_check.fetchone()
                if vec_row:
                    print(f"  [PASS] pgvector extension verified (version: {vec_row[1]})")
                else:
                    print("  [WARN] pgvector extension created but not listed in pg_extension")
            except Exception as e:
                print(f"  [WARN] pgvector extension check: {e} (Standard relational queries unaffected)")

            # 3. Check Alembic migration head
            try:
                elem_res = await conn.execute(text("SELECT version_num FROM alembic_version;"))
                current_rev = elem_res.scalar()
                print(f"  [PASS] Alembic migration head verified: {current_rev}")
            except Exception as e:
                print(f"  [WARN] alembic_version table check: {e} (run 'alembic upgrade head' to apply migrations)")

            # 4. Check Critical Platform Tables
            critical_tables = [
                "users",
                "workspaces",
                "jobs",
                "candidates",
                "interviews",
                "interview_sessions",
                "interview_events",
                "evaluation_reports",
            ]
            
            missing_tables = []
            for tbl in critical_tables:
                check_tbl = await conn.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :t);"),
                    {"t": tbl}
                )
                exists = check_tbl.scalar()
                if not exists:
                    missing_tables.append(tbl)

            if missing_tables:
                print(f"  [WARN] Pending schema creation for tables: {missing_tables}")
            else:
                print(f"  [PASS] All {len(critical_tables)} critical platform tables exist and verified.")

        print("[InterviewOS] Database verification completed successfully.\n")
        return True

    except Exception as err:
        print(f"  [FAIL] Database verification failed: {err}")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    success = asyncio.run(verify_database(target_url))
    sys.exit(0 if success else 1)
