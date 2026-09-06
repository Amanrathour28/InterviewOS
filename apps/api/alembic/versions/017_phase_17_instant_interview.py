"""Migration for Phase 17: Instant Interview & Guest Candidate support.

Adds:
- candidates.is_guest (Boolean, NOT NULL, default False)
- interview_invitations.candidate_session_token_hash (VARCHAR 64, nullable, unique)
- interview_invitations.candidate_name (VARCHAR 150, nullable)
- interview_invitations.candidate_email (VARCHAR 255, nullable)

Revision ID: 017_phase_17_instant_interview
Revises: 016_phase_16_analytics_indexes
Create Date: 2026-09-06 09:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017_phase_17_instant_interview"
down_revision: Union[str, None] = "016_phase_16_analytics_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. candidates — is_guest flag
    op.add_column(
        "candidates",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 2. interview_invitations — candidate identity/session columns
    op.add_column(
        "interview_invitations",
        sa.Column("candidate_session_token_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "interview_invitations",
        sa.Column("candidate_name", sa.String(150), nullable=True),
    )
    op.add_column(
        "interview_invitations",
        sa.Column("candidate_email", sa.String(255), nullable=True),
    )

    # Unique index on candidate_session_token_hash for fast lookup
    op.create_index(
        "ix_interview_invitations_candidate_session_token_hash",
        "interview_invitations",
        ["candidate_session_token_hash"],
        unique=True,
        postgresql_where=sa.text("candidate_session_token_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_interview_invitations_candidate_session_token_hash",
        table_name="interview_invitations",
    )
    op.drop_column("interview_invitations", "candidate_email")
    op.drop_column("interview_invitations", "candidate_name")
    op.drop_column("interview_invitations", "candidate_session_token_hash")
    op.drop_column("candidates", "is_guest")
