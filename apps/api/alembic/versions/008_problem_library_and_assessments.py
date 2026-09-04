"""Migration for Phase 9: Interview Problem Library, Versioning, and Assessments.

Revision ID: 008_problem_library_and_assessments
Revises: 007_coding_tables
Create Date: 2026-09-03 08:52:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_problem_library_and_assessments'
down_revision: Union[str, None] = '007_coding_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. coding_problems
    op.create_table(
        'coding_problems',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('short_description', sa.Text(), nullable=False, server_default=''),
        sa.Column('difficulty', sa.String(length=32), nullable=False, server_default='medium'),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='algorithms'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='published'),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('default_time_limit_seconds', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('default_memory_limit_mb', sa.Integer(), nullable=False, server_default='256'),
        sa.Column('tags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('current_version_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_problems_workspace_id', 'coding_problems', ['workspace_id'])
    op.create_index('ix_coding_problems_difficulty', 'coding_problems', ['difficulty'])
    op.create_index('ix_coding_problems_category', 'coding_problems', ['category'])
    op.create_index('ix_coding_problems_status', 'coding_problems', ['status'])
    op.create_index('ix_coding_problems_is_system', 'coding_problems', ['is_system'])

    # 2. coding_problem_versions
    op.create_table(
        'coding_problem_versions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('problem_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('problem_statement', sa.Text(), nullable=False, server_default=''),
        sa.Column('examples', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'),
        sa.Column('constraints', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'),
        sa.Column('expected_time_complexity', sa.String(length=64), nullable=True),
        sa.Column('expected_space_complexity', sa.String(length=64), nullable=True),
        sa.Column('starter_codes', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('solution_templates', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True, server_default='{}'),
        sa.Column('scoring_policy', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{"public_test_weight": 0.2, "hidden_test_weight": 0.8}'),
        sa.Column('time_limit_seconds', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('memory_limit_mb', sa.Integer(), nullable=False, server_default='256'),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('problem_id', 'version_number', name='uq_problem_version_number'),
    )
    op.create_index('ix_coding_problem_versions_problem_id', 'coding_problem_versions', ['problem_id'])

    # 3. coding_session_problems
    op.create_table(
        'coding_session_problems',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_version_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_problem_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='assigned'),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_session_problems_session_id', 'coding_session_problems', ['coding_session_id'])
    op.create_index('ix_coding_session_problems_version_id', 'coding_session_problems', ['problem_version_id'])

    # 4. coding_submissions
    op.create_table(
        'coding_submissions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_problem_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_session_problems.id', ondelete='SET NULL'), nullable=True),
        sa.Column('problem_version_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_problem_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('submission_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('language', sa.String(length=32), nullable=False),
        sa.Column('snapshot_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('execution_job_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_execution_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='evaluating'),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tests_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tests_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('runtime_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memory_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_coding_submissions_coding_session_id', 'coding_submissions', ['coding_session_id'])
    op.create_index('ix_coding_submissions_problem_version_id', 'coding_submissions', ['problem_version_id'])
    op.create_index('ix_coding_submissions_candidate_id', 'coding_submissions', ['candidate_id'])
    op.create_index('ix_coding_submissions_status', 'coding_submissions', ['status'])

    # 5. coding_assessments
    op.create_table(
        'coding_assessments',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('coding_session_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_version_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_problem_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_submissions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('best_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('evaluation_summary', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('coding_session_id', 'problem_version_id', 'candidate_id', name='uq_session_problem_candidate_assessment'),
    )
    op.create_index('ix_coding_assessments_coding_session_id', 'coding_assessments', ['coding_session_id'])
    op.create_index('ix_coding_assessments_problem_version_id', 'coding_assessments', ['problem_version_id'])
    op.create_index('ix_coding_assessments_candidate_id', 'coding_assessments', ['candidate_id'])

    # 6. Update coding_sessions
    op.add_column('coding_sessions', sa.Column('active_problem_version_id', sa.Uuid(as_uuid=True), nullable=True))

    # 7. Update coding_test_cases
    op.add_column('coding_test_cases', sa.Column('problem_version_id', sa.Uuid(as_uuid=True), sa.ForeignKey('coding_problem_versions.id', ondelete='CASCADE'), nullable=True))
    op.add_column('coding_test_cases', sa.Column('explanation', sa.Text(), nullable=False, server_default=''))
    op.add_column('coding_test_cases', sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'))
    op.add_column('coding_test_cases', sa.Column('order', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('coding_test_cases', 'coding_session_id', existing_type=sa.Uuid(as_uuid=True), nullable=True)
    op.create_index('ix_coding_test_cases_problem_version_id', 'coding_test_cases', ['problem_version_id'])


def downgrade() -> None:
    op.drop_index('ix_coding_test_cases_problem_version_id', 'coding_test_cases')
    op.alter_column('coding_test_cases', 'coding_session_id', existing_type=sa.Uuid(as_uuid=True), nullable=False)
    op.drop_column('coding_test_cases', 'order')
    op.drop_column('coding_test_cases', 'weight')
    op.drop_column('coding_test_cases', 'explanation')
    op.drop_column('coding_test_cases', 'problem_version_id')
    op.drop_column('coding_sessions', 'active_problem_version_id')
    op.drop_table('coding_assessments')
    op.drop_table('coding_submissions')
    op.drop_table('coding_session_problems')
    op.drop_table('coding_problem_versions')
    op.drop_table('coding_problems')
