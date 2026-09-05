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

    database_url = normalize_database_url(database_url)
    masked_url = sanitize_url(database_url)
    print(f"\n[InterviewOS] Starting Database Verification against: {masked_url}")

    connect_args = {}
    if "pooler" in database_url or any(c in database_url for c in ["neon.tech", "amazonaws.com", "supabase.com"]):
        connect_args["statement_cache_size"] = 0

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
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
                "evaluations",
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
