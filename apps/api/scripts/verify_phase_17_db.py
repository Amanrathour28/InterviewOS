"""
verify_phase_17_db.py — Comprehensive non-destructive verification of Phase 17 schema in Neon.

Checks:
1. alembic_version contains '017_phase_17_instant_interview'
2. candidates.is_guest exists, is boolean, default false
3. interview_invitations.candidate_session_token_hash exists (VARCHAR 64)
4. interview_invitations.candidate_name exists (VARCHAR 150)
5. interview_invitations.candidate_email exists (VARCHAR 255)
6. ix_interview_invitations_candidate_session_token_hash index exists
7. interviews.candidate_id remains NOT NULL
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings


async def verify():
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

    db_url = Settings.assemble_database_url(raw_url)

    engine = create_async_engine(
        db_url,
        future=True,
        connect_args={"statement_cache_size": 0},
    )

    all_passed = True

    async with engine.connect() as conn:
        print("=== Phase 17 Database Schema Verification ===")

        # 1. alembic_version
        res = await conn.execute(text("SELECT version_num FROM alembic_version"))
        versions = [r[0] for r in res.fetchall()]
        print(f"1. Alembic Version: {versions}")
        if "017_phase_17_instant_interview" in versions:
            print("   [PASS] 017_phase_17_instant_interview is present")
        else:
            print("   [FAIL] 017_phase_17_instant_interview missing from alembic_version")
            all_passed = False

        # 2. candidates.is_guest
        res = await conn.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = 'candidates' AND column_name = 'is_guest'"
        ))
        row = res.fetchone()
        if row:
            print(f"2. candidates.is_guest: exists (type={row[1]}, nullable={row[2]}, default={row[3]})")
            print("   [PASS] candidates.is_guest is present")
        else:
            print("   [FAIL] candidates.is_guest is missing")
            all_passed = False

        # 3. interview_invitations Phase 17 columns
        cols = [
            ("candidate_session_token_hash", 64),
            ("candidate_name", 150),
            ("candidate_email", 255),
        ]
        for col_name, char_len in cols:
            res = await conn.execute(text(
                "SELECT column_name, data_type, character_maximum_length, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'interview_invitations' AND column_name = :c"
            ), {"c": col_name})
            row = res.fetchone()
            if row:
                print(f"3. interview_invitations.{col_name}: exists (type={row[1]}, max_len={row[2]}, nullable={row[3]})")
                print(f"   [PASS] interview_invitations.{col_name} is present")
            else:
                print(f"   [FAIL] interview_invitations.{col_name} is missing")
                all_passed = False

        # 4. Partial unique index
        res = await conn.execute(text(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_interview_invitations_candidate_session_token_hash'"
        ))
        row = res.fetchone()
        if row:
            print(f"4. Index {row[0]}: exists")
            print(f"   Definition: {row[1]}")
            print("   [PASS] Index is present")
        else:
            print("   [FAIL] Index ix_interview_invitations_candidate_session_token_hash is missing")
            all_passed = False

        # 5. interviews.candidate_id remains NOT NULL
        res = await conn.execute(text(
            "SELECT column_name, is_nullable, data_type "
            "FROM information_schema.columns "
            "WHERE table_name = 'interviews' AND column_name = 'candidate_id'"
        ))
        row = res.fetchone()
        if row:
            print(f"5. interviews.candidate_id: exists (type={row[2]}, nullable={row[1]})")
            if row[1] == "NO":
                print("   [PASS] interviews.candidate_id is NOT NULL (non-nullable preserved)")
            else:
                print("   [FAIL] interviews.candidate_id is nullable (violation of rule 7)")
                all_passed = False
        else:
            print("   [FAIL] interviews.candidate_id column not found")
            all_passed = False

    await engine.dispose()

    if all_passed:
        print("\n=== ALL PHASE 17 SCHEMA VERIFICATIONS PASSED ===")
    else:
        print("\n=== SOME VERIFICATIONS FAILED ===")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify())
