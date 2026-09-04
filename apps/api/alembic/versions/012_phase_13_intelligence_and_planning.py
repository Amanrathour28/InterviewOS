"""Migration for Phase 13: Resume & Job Intelligence, Candidate Matching, and Interview Planning tables.

Revision ID: 012_phase_13_intelligence_and_planning
Revises: 011_ai_request_log
Create Date: 2026-09-04 05:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012_phase_13_intelligence_and_planning"
down_revision: Union[str, None] = "011_ai_request_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. resume_versions
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("parsing_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("parser_version", sa.String(length=50), nullable=False, server_default="1.0"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resume_versions_candidate_id", "resume_versions", ["candidate_id"])
    op.create_index("ix_resume_versions_workspace_id", "resume_versions", ["workspace_id"])
    op.create_index("ix_resume_versions_candidate_active", "resume_versions", ["candidate_id", "is_active"])

    # 2. resume_profiles
    op.create_table(
        "resume_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("experience_years", sa.Float(), nullable=True),
        sa.Column("seniority_level", sa.String(length=50), nullable=True),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("experience", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("education", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("projects", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("certifications", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("achievements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_version_id", name="uq_resume_profile_version"),
    )
    op.create_index("ix_resume_profiles_resume_version_id", "resume_profiles", ["resume_version_id"])
    op.create_index("ix_resume_profiles_candidate_id", "resume_profiles", ["candidate_id"])
    op.create_index("ix_resume_profiles_workspace_id", "resume_profiles", ["workspace_id"])

    # 3. resume_claims
    op.create_table(
        "resume_claims",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False, server_default="general"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="explicit"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.9"),
        sa.Column("verification_priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("suggested_probes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resume_claims_resume_version_id", "resume_claims", ["resume_version_id"])
    op.create_index("ix_resume_claims_category", "resume_claims", ["category"])
    op.create_index("ix_resume_claims_candidate_id", "resume_claims", ["candidate_id"])

    # 4. job_profiles
    op.create_table(
        "job_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("seniority", sa.String(length=50), nullable=False, server_default="mid"),
        sa.Column("technical_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("responsibilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("interview_focus", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("suggested_rounds", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_job_profile_job"),
    )
    op.create_index("ix_job_profiles_job_id", "job_profiles", ["job_id"])
    op.create_index("ix_job_profiles_workspace_id", "job_profiles", ["workspace_id"])

    # 5. job_requirements
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("skill", sa.String(length=150), nullable=False),
        sa.Column("canonical_skill", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False, server_default="general"),
        sa.Column("requirement_type", sa.String(length=50), nullable=False, server_default="required"),
        sa.Column("importance", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.9"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_profile_id"], ["job_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_requirements_job_profile_id", "job_requirements", ["job_profile_id"])
    op.create_index("ix_job_requirements_canonical_skill", "job_requirements", ["canonical_skill"])
    op.create_index("ix_job_requirements_job_id", "job_requirements", ["job_id"])

    # 6. candidate_job_matches
    op.create_table(
        "candidate_job_matches",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("required_skill_coverage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("preferred_skill_coverage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("experience_fit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("project_relevance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("seniority_fit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("domain_fit", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("scoring_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("gaps", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("verification_areas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_candidate_job_match"),
    )
    op.create_index("ix_candidate_job_matches_job_id", "candidate_job_matches", ["job_id"])
    op.create_index("ix_candidate_job_matches_candidate_id", "candidate_job_matches", ["candidate_id"])
    op.create_index("ix_matches_workspace_overall", "candidate_job_matches", ["workspace_id", "overall_score"])

    # 7. interview_blueprints
    op.create_table(
        "interview_blueprints",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("generated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("approved_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("target_seniority", sa.String(length=50), nullable=False, server_default="mid"),
        sa.Column("candidate_focus_areas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("job_focus_areas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("verification_priorities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("scoring_rubric", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default="interview_blueprint:v1"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blueprints_workspace_status", "interview_blueprints", ["workspace_id", "status"])
    op.create_index("ix_blueprints_interview_id", "interview_blueprints", ["interview_id"])

    # 8. interview_blueprint_rounds
    op.create_table(
        "interview_blueprint_rounds",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("blueprint_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("round_type", sa.String(length=50), nullable=False, server_default="technical"),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("difficulty", sa.String(length=50), nullable=False, server_default="mid"),
        sa.Column("objectives", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("competencies", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("suggested_question_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("scoring_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["blueprint_id"], ["interview_blueprints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blueprint_id", "sequence", name="uq_blueprint_round_seq"),
    )
    op.create_index("ix_interview_blueprint_rounds_blueprint_id", "interview_blueprint_rounds", ["blueprint_id"])

    # 9. question_plans
    op.create_table(
        "question_plans",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("interview_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("blueprint_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("candidate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("approved_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("coverage_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default="question_plan:v1"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blueprint_id"], ["interview_blueprints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_question_plans_interview", "question_plans", ["interview_id"])
    op.create_index("ix_question_plans_workspace", "question_plans", ["workspace_id"])

    # 10. question_plan_items
    op.create_table(
        "question_plan_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("question_plan_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("existing_question_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("competency", sa.String(length=100), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False, server_default="medium"),
        sa.Column("progression_stage", sa.String(length=50), nullable=False, server_default="practical"),
        sa.Column("expected_signal", sa.Text(), nullable=True),
        sa.Column("candidate_evidence_tested", sa.Text(), nullable=True),
        sa.Column("job_requirement_tested", sa.Text(), nullable=True),
        sa.Column("suggested_followups", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["question_plan_id"], ["question_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["existing_question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_plan_id", "sequence", name="uq_plan_item_seq"),
    )
    op.create_index("ix_question_plan_items_plan_id", "question_plan_items", ["question_plan_id"])


def downgrade() -> None:
    op.drop_table("question_plan_items")
    op.drop_table("question_plans")
    op.drop_table("interview_blueprint_rounds")
    op.drop_table("interview_blueprints")
    op.drop_table("candidate_job_matches")
    op.drop_table("job_requirements")
    op.drop_table("job_profiles")
    op.drop_table("resume_claims")
    op.drop_table("resume_profiles")
    op.drop_table("resume_versions")
