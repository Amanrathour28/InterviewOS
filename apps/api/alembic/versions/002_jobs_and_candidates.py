"""Migration for Phase 2: Jobs, Candidates, Applications, Tags, Notes, Documents, and Activity.

Revision ID: 002_jobs_and_candidates
Revises: 001_initial_auth_and_organizations
Create Date: 2026-09-02 07:51:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_jobs_and_candidates'
down_revision: Union[str, None] = '001_initial_auth_and_organizations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. jobs
    op.create_table(
        'jobs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=150), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=False, server_default='full_time'),
        sa.Column('experience_min', sa.Integer(), nullable=True),
        sa.Column('experience_max', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('required_skills', sa.JSON(), nullable=False),
        sa.Column('preferred_skills', sa.JSON(), nullable=False),
        sa.Column('responsibilities', sa.JSON(), nullable=False),
        sa.Column('requirements', sa.JSON(), nullable=False),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_jobs_workspace_status', 'jobs', ['workspace_id', 'status'])
    op.create_index('ix_jobs_workspace_slug', 'jobs', ['workspace_id', 'slug'])

    # 2. candidates
    op.create_table(
        'candidates',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('location', sa.String(length=150), nullable=True),
        sa.Column('headline', sa.String(length=255), nullable=True),
        sa.Column('current_company', sa.String(length=150), nullable=True),
        sa.Column('current_title', sa.String(length=150), nullable=True),
        sa.Column('experience_years', sa.Float(), nullable=True),
        sa.Column('education_summary', sa.Text(), nullable=True),
        sa.Column('linkedin_url', sa.String(length=255), nullable=True),
        sa.Column('github_url', sa.String(length=255), nullable=True),
        sa.Column('portfolio_url', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='inbound'),
        sa.Column('notes_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index('ix_candidates_workspace_status', 'candidates', ['workspace_id', 'status'])
    op.create_index('ix_candidates_workspace_email', 'candidates', ['workspace_id', 'email'])

    # 3. job_candidates
    op.create_table(
        'job_candidates',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('job_id', sa.Uuid(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('job_id', 'candidate_id', name='uq_job_candidate'),
    )
    op.create_index('ix_job_candidates_job_status', 'job_candidates', ['job_id', 'status'])

    # 4. candidate_tags
    op.create_table(
        'candidate_tags',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False, server_default='#6366f1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_workspace_tag_name'),
    )

    # 5. candidate_tag_assignments
    op.create_table(
        'candidate_tag_assignments',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('tag_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidate_tags.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('tag_id', 'candidate_id', name='uq_tag_candidate'),
    )

    # 6. candidate_notes
    op.create_table(
        'candidate_notes',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 7. candidate_documents
    op.create_table(
        'candidate_documents',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False, unique=True),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False, server_default='resume'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 8. candidate_activities
    op.create_table(
        'candidate_activities',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', sa.Uuid(as_uuid=True), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_candidate_activities_type', 'candidate_activities', ['event_type'])


def downgrade() -> None:
    op.drop_table('candidate_activities')
    op.drop_table('candidate_documents')
    op.drop_table('candidate_notes')
    op.drop_table('candidate_tag_assignments')
    op.drop_table('candidate_tags')
    op.drop_table('job_candidates')
    op.drop_table('candidates')
    op.drop_table('jobs')
