"""Migration for Phase 15.1: Evaluation Integrity & Cryptographic Seal.

Revision ID: 015_phase_15_1_evaluation_integrity
Revises: 014_phase_15_evaluation_and_reporting
Create Date: 2026-09-04 08:35:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015_phase_15_1_evaluation_integrity"
down_revision: Union[str, None] = "014_phase_15_evaluation_and_reporting"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "evaluation_versions",
        sa.Column("integrity_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_versions", "integrity_hash")
