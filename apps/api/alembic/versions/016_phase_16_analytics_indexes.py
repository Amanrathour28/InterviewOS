"""Migration for Phase 16: Analytics & Decision Platform performance indexes.

Revision ID: 016_phase_16_analytics_indexes
Revises: 015_phase_15_1_evaluation_integrity
Create Date: 2026-09-04 09:30:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016_phase_16_analytics_indexes"
down_revision: Union[str, None] = "015_phase_15_1_evaluation_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Optimizes analytics aggregation queries
    op.create_index(
        "ix_evaluations_ws_status_finalized",
        "evaluations",
        ["workspace_id", "status", "finalized_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_eval_comp_scores_name_score",
        "evaluation_competency_scores",
        ["competency_name", "calculated_score"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_sessions_ws_status_started",
        "interview_sessions",
        ["workspace_id", "status", "started_at"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_evaluations_ws_status_finalized", table_name="evaluations", if_exists=True)
    op.drop_index("ix_eval_comp_scores_name_score", table_name="evaluation_competency_scores", if_exists=True)
    op.drop_index("ix_sessions_ws_status_started", table_name="interview_sessions", if_exists=True)
