"""Initial migration

Revision ID: 28074d007126
Revises: 
Create Date: 2024-10-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '28074d007126'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create videos table
    op.create_table('videos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('original_path', sa.String(length=500), nullable=True),
        sa.Column('processed_path', sa.String(length=500), nullable=True),
        sa.Column('status', postgresql.ENUM('uploaded', 'processing', 'processed', 'failed', name='videostatus'), nullable=True),
        sa.Column('task_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)

    # Create votes table
    op.create_table('votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('voter_id', sa.Integer(), nullable=True),
        sa.Column('video_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['voter_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_votes_id'), 'votes', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_votes_id'), table_name='votes')
    op.drop_table('votes')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_table('videos')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
