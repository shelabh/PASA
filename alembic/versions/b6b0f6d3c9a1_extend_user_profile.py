"""Extend user_profile with profile_context and resume fields

Revision ID: b6b0f6d3c9a1
Revises: 4343153540ef
Create Date: 2025-08-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6b0f6d3c9a1'
down_revision: Union[str, Sequence[str], None] = '4343153540ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add new profile and resume columns to user_profile."""
    op.add_column('user_profile', sa.Column('profile_context', sa.Text(), nullable=True))
    op.add_column('user_profile', sa.Column('resume_bytes', sa.LargeBinary(), nullable=True))
    op.add_column('user_profile', sa.Column('resume_filename', sa.String(), nullable=True))
    op.add_column('user_profile', sa.Column('resume_mime', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema: remove columns added in upgrade."""
    op.drop_column('user_profile', 'resume_mime')
    op.drop_column('user_profile', 'resume_filename')
    op.drop_column('user_profile', 'resume_bytes')
    op.drop_column('user_profile', 'profile_context')


