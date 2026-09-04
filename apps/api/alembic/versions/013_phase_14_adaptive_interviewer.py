"""Migration for Phase 14: AI Interviewer & Adaptive Questioning tables.

Revision ID: 013_phase_14_adaptive_interviewer
Revises: 012_phase_13_intelligence_and_planning
Create Date: 2026-09-04 06:10:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013_phase_14_adaptive_interviewer"
down_revision: Union[str, None] = "012_phase_13_intelligence_and_planning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. transcript_segments
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("speaker_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("speaker_role", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column("speaker_name", sa.String(length=100), nullable=True),
        sa.Column("start_time_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("end_time_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("detected_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_segments_interview_id", "transcript_segments", ["interview_id"])
    op.create_index("ix_transcript_segments_session_id", "transcript_segments", ["session_id"])
    op.create_index("ix_transcript_segments_workspace_id", "transcript_segments", ["workspace_id"])
    op.create_index("ix_transcript_segments_created_at", "transcript_segments", ["created_at"])

    # 2. ai_interview_recommendations
    op.create_table(
        "ai_interview_recommendations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False, server_default="generate_follow_up"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="generated"),
        sa.Column("recommended_question", sa.Text(), nullable=False),
        sa.Column("original_question", sa.Text(), nullable=True),
        sa.Column("edited_question", sa.Text(), nullable=True),
        sa.Column("competency", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_target", sa.Text(), nullable=True),
        sa.Column("time_cost_estimate_seconds", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("source_question_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source_claim_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("context_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requires_interviewer_approval", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reviewed_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_recs_interview_id", "ai_interview_recommendations", ["interview_id"])
    op.create_index("ix_ai_recs_session_id", "ai_interview_recommendations", ["session_id"])
    op.create_index("ix_ai_recs_workspace_id", "ai_interview_recommendations", ["workspace_id"])
    op.create_index("ix_ai_recs_status", "ai_interview_recommendations", ["status"])
    op.create_index("ix_ai_recs_created_at", "ai_interview_recommendations", ["created_at"])

    # 3. interview_competency_evidence
    op.create_table(
        "interview_competency_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("competency", sa.String(length=100), nullable=False),
        sa.Column("evidence_strength", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="not_started"),
        sa.Column("questions_asked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demonstrated_concepts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("missing_concepts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comp_evidence_interview_id", "interview_competency_evidence", ["interview_id"])
    op.create_index("ix_comp_evidence_session_id", "interview_competency_evidence", ["session_id"])
    op.create_index("ix_comp_evidence_competency", "interview_competency_evidence", ["competency"])


def downgrade() -> None:
    op.drop_table("interview_competency_evidence")
    op.drop_table("ai_interview_recommendations")
    op.drop_table("transcript_segments")
