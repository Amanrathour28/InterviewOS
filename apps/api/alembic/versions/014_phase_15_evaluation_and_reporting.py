"""Migration for Phase 15: Evidence-Based Evaluation, Scoring & Reporting tables.

Revision ID: 014_phase_15_evaluation_and_reporting
Revises: 013_phase_14_adaptive_interviewer
Create Date: 2026-09-04 07:35:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "014_phase_15_evaluation_and_reporting"
down_revision: Union[str, None] = "013_phase_14_adaptive_interviewer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. evaluation_competencies
    op.create_table(
        "evaluation_competencies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="technical"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_competencies_workspace_id", "evaluation_competencies", ["workspace_id"])
    op.create_index("ix_eval_competencies_name", "evaluation_competencies", ["name"])

    # 2. competency_rubrics
    op.create_table(
        "competency_rubrics",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("competency_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column("indicators", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["competency_id"], ["evaluation_competencies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competency_rubrics_competency_id", "competency_rubrics", ["competency_id"])

    # 3. evaluation_evidence
    op.create_table(
        "evaluation_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("competency_name", sa.String(length=100), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("evidence_timestamp_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_candidate_evidence", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_interviewer_observation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_evidence_workspace_id", "evaluation_evidence", ["workspace_id"])
    op.create_index("ix_eval_evidence_interview_id", "evaluation_evidence", ["interview_id"])
    op.create_index("ix_eval_evidence_candidate_id", "evaluation_evidence", ["candidate_id"])
    op.create_index("ix_eval_evidence_competency_name", "evaluation_evidence", ["competency_name"])

    # 4. evaluations
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("overall_rubric_level", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recommendation", sa.String(length=50), nullable=False, server_default="insufficient_evidence"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("development_areas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("evidence_gaps", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("reviewed_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finalized_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", name="uq_evaluations_interview_id"),
    )
    op.create_index("ix_evaluations_workspace_id", "evaluations", ["workspace_id"])
    op.create_index("ix_evaluations_candidate_id", "evaluations", ["candidate_id"])
    op.create_index("ix_evaluations_status", "evaluations", ["status"])

    # 5. evaluation_competency_scores
    op.create_table(
        "evaluation_competency_scores",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("competency_name", sa.String(length=100), nullable=False),
        sa.Column("rubric_level", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("calculated_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="assessed"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("observed_facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("inferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_overridden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("original_ai_rubric_level", sa.Float(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("overridden_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["overridden_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_comp_scores_eval_id", "evaluation_competency_scores", ["evaluation_id"])
    op.create_index("ix_eval_comp_scores_comp_name", "evaluation_competency_scores", ["competency_name"])

    # 6. evaluation_contradictions
    op.create_table(
        "evaluation_contradictions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False, server_default="medium"),
        sa.Column("source_a_type", sa.String(length=50), nullable=False),
        sa.Column("source_a_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source_a_description", sa.Text(), nullable=False),
        sa.Column("source_b_type", sa.String(length=50), nullable=False),
        sa.Column("source_b_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source_b_description", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_contradictions_eval_id", "evaluation_contradictions", ["evaluation_id"])

    # 7. evaluation_score_inputs
    op.create_table(
        "evaluation_score_inputs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("scoring_formula", sa.String(length=100), nullable=False, server_default="weighted_rubric_average"),
        sa.Column("competency_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("competency_rubric_levels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("calculated_overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("calculated_recommendation", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_score_inputs_eval_id", "evaluation_score_inputs", ["evaluation_id"])

    # 8. evaluation_versions
    op.create_table(
        "evaluation_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("snapshot_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_versions_eval_id", "evaluation_versions", ["evaluation_id"])

    # 9. evaluation_audit_events
    op.create_table(
        "evaluation_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_audit_events_eval_id", "evaluation_audit_events", ["evaluation_id"])
    op.create_index("ix_eval_audit_events_workspace_id", "evaluation_audit_events", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("evaluation_audit_events")
    op.drop_table("evaluation_versions")
    op.drop_table("evaluation_score_inputs")
    op.drop_table("evaluation_contradictions")
    op.drop_table("evaluation_competency_scores")
    op.drop_table("evaluations")
    op.drop_table("evaluation_evidence")
    op.drop_table("competency_rubrics")
    op.drop_table("evaluation_competencies")
