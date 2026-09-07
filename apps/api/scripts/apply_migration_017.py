"""
apply_migration_017.py — Idempotent script to apply Phase 17 schema changes to Neon.

Usage:
    DATABASE_URL="postgresql+asyncpg://..." python scripts/apply_migration_017.py

What it does (in one transaction):
  1. Adds candidates.is_guest              (Boolean NOT NULL DEFAULT FALSE)
  2. Adds interview_invitations.candidate_session_token_hash  (VARCHAR 64, nullable)
  3. Adds interview_invitations.candidate_name                (VARCHAR 150, nullable)
  4. Adds interview_invitations.candidate_email               (VARCHAR 255, nullable)
  5. Creates unique partial index on candidate_session_token_hash
  6. Stamps the alembic_version table with 017_phase_17_instant_interview

All steps are idempotent: if the column / index already exists the step is skipped.
"""
import asyncio
import os
import sys

# Allow running from anywhere in the repo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings


async def column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.scalar_one_or_none() is not None


async def index_exists(conn, index_name: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :n"
        ),
        {"n": index_name},
    )
    return result.scalar_one_or_none() is not None


async def revision_applied(conn, revision: str) -> bool:
    try:
        result = await conn.execute(
            text("SELECT 1 FROM alembic_version WHERE version_num = :v"),
            {"v": revision},
        )
        return result.scalar_one_or_none() is not None
    except Exception:
        return False


async def apply():
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        try:
            import dotenv
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            for env_name in [".env", ".env.local", ".vercel/.env.production.local"]:
                env_path = os.path.join(root_dir, env_name)
                if os.path.exists(env_path):
                    dotenv.load_dotenv(env_path)
            raw_url = os.environ.get("DATABASE_URL", "")
        except Exception:
            pass

    if not raw_url:
        from app.core.config import settings
        raw_url = settings.DATABASE_URL

    # Normalise URL for asyncpg
    db_url = Settings.assemble_database_url(raw_url)

    engine = create_async_engine(
        db_url,
        future=True,
        connect_args={"statement_cache_size": 0},
    )

    REVISION = "017_phase_17_instant_interview"

    async with engine.begin() as conn:
        print("=== Migration 017: Phase 17 Instant Interview ===")

        # ------------------------------------------------------------------
        # 1. Ensure alembic_version table exists (in case Alembic never ran)
        # ------------------------------------------------------------------
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "  version_num VARCHAR(128) NOT NULL "
            "  CONSTRAINT alembic_version_pkc PRIMARY KEY"
            ")"
        ))
        print("[OK] alembic_version table ensured")

        # ------------------------------------------------------------------
        # 2. candidates.is_guest
        # ------------------------------------------------------------------
        if not await column_exists(conn, "candidates", "is_guest"):
            await conn.execute(text(
                "ALTER TABLE candidates "
                "ADD COLUMN is_guest BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            print("[OK] Added candidates.is_guest")
        else:
            print("[SKIP] candidates.is_guest already exists")

        # ------------------------------------------------------------------
        # 3. interview_invitations.candidate_session_token_hash
        # ------------------------------------------------------------------
        if not await column_exists(conn, "interview_invitations", "candidate_session_token_hash"):
            await conn.execute(text(
                "ALTER TABLE interview_invitations "
                "ADD COLUMN candidate_session_token_hash VARCHAR(64)"
            ))
            print("[OK] Added interview_invitations.candidate_session_token_hash")
        else:
            print("[SKIP] interview_invitations.candidate_session_token_hash already exists")

        # ------------------------------------------------------------------
        # 4. interview_invitations.candidate_name
        # ------------------------------------------------------------------
        if not await column_exists(conn, "interview_invitations", "candidate_name"):
            await conn.execute(text(
                "ALTER TABLE interview_invitations "
                "ADD COLUMN candidate_name VARCHAR(150)"
            ))
            print("[OK] Added interview_invitations.candidate_name")
        else:
            print("[SKIP] interview_invitations.candidate_name already exists")

        # ------------------------------------------------------------------
        # 5. interview_invitations.candidate_email
        # ------------------------------------------------------------------
        if not await column_exists(conn, "interview_invitations", "candidate_email"):
            await conn.execute(text(
                "ALTER TABLE interview_invitations "
                "ADD COLUMN candidate_email VARCHAR(255)"
            ))
            print("[OK] Added interview_invitations.candidate_email")
        else:
            print("[SKIP] interview_invitations.candidate_email already exists")

        # ------------------------------------------------------------------
        # 6. Unique partial index on candidate_session_token_hash
        # ------------------------------------------------------------------
        idx_name = "ix_interview_invitations_candidate_session_token_hash"
        if not await index_exists(conn, idx_name):
            await conn.execute(text(
                f"CREATE UNIQUE INDEX {idx_name} "
                "ON interview_invitations (candidate_session_token_hash) "
                "WHERE candidate_session_token_hash IS NOT NULL"
            ))
            print(f"[OK] Created index {idx_name}")
        else:
            print(f"[SKIP] Index {idx_name} already exists")

        # ------------------------------------------------------------------
        # 7. Stamp alembic_version
        # ------------------------------------------------------------------
        existing = await conn.execute(
            text("SELECT version_num FROM alembic_version")
        )
        current_versions = [r[0] for r in existing.fetchall()]
        print(f"Current alembic_version: {current_versions}")

        if REVISION in current_versions:
            print(f"[SKIP] {REVISION} already in alembic_version")
        elif not current_versions:
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": REVISION},
            )
            print(f"[OK] Stamped alembic_version with {REVISION} (inserted)")
        else:
            prev_revision = "016_phase_16_analytics_indexes"
            result = await conn.execute(
                text("UPDATE alembic_version SET version_num = :v WHERE version_num = :p"),
                {"v": REVISION, "p": prev_revision},
            )
            if result.rowcount == 0:
                old_ver = current_versions[0]
                await conn.execute(
                    text("UPDATE alembic_version SET version_num = :v WHERE version_num = :old"),
                    {"v": REVISION, "old": old_ver},
                )
                print(f"[OK] Stamped alembic_version with {REVISION} (updated from {old_ver})")
            else:
                print(f"[OK] Stamped alembic_version with {REVISION} (updated from {prev_revision})")

        # Verify post-stamp alembic version
        check = await conn.execute(text("SELECT version_num FROM alembic_version"))
        final_versions = [r[0] for r in check.fetchall()]
        print(f"Verified alembic_version: {final_versions}")

        print("=== Migration 017 applied successfully ===")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(apply())
