"""Initial migration for auth, users, organizations, workspaces, and memberships.

Revision ID: 001_initial_auth_and_organizations
Revises: 
Create Date: 2026-09-02 07:28:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_auth_and_organizations'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=150), nullable=True),
        sa.Column('avatar_url', sa.String(length=1024), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='candidate'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])

    # 2. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('logo_url', sa.String(length=1024), nullable=True),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # 3. organization_memberships
    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )
    op.create_index('ix_org_memberships_id', 'organization_memberships', ['id'])
    op.create_index('ix_org_memberships_org_id', 'organization_memberships', ['organization_id'])
    op.create_index('ix_org_memberships_user_id', 'organization_memberships', ['user_id'])

    # 4. workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('organization_id', 'slug', name='uq_workspace_org_slug'),
    )
    op.create_index('ix_workspaces_id', 'workspaces', ['id'])
    op.create_index('ix_workspaces_org_id', 'workspaces', ['organization_id'])
    op.create_index('ix_workspaces_slug', 'workspaces', ['slug'])

    # 5. workspace_memberships
    op.create_table(
        'workspace_memberships',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.Uuid(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user'),
    )
    op.create_index('ix_workspace_memberships_id', 'workspace_memberships', ['id'])
    op.create_index('ix_workspace_memberships_ws_id', 'workspace_memberships', ['workspace_id'])
    op.create_index('ix_workspace_memberships_user_id', 'workspace_memberships', ['user_id'])

    # 6. refresh_sessions
    op.create_table(
        'refresh_sessions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_refresh_sessions_id', 'refresh_sessions', ['id'])
    op.create_index('ix_refresh_sessions_user_id', 'refresh_sessions', ['user_id'])
    op.create_index('ix_refresh_sessions_token_hash', 'refresh_sessions', ['token_hash'])
    op.create_index('ix_refresh_sessions_is_revoked', 'refresh_sessions', ['is_revoked'])

    # 7. password_reset_tokens
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'])
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'])


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
    op.drop_table('refresh_sessions')
    op.drop_table('workspace_memberships')
    op.drop_table('workspaces')
    op.drop_table('organization_memberships')
    op.drop_table('organizations')
    op.drop_table('users')
