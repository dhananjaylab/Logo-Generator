"""Initial schema: logo_generations table

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-06-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial logo_generations table."""
    op.create_table(
        'logo_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('brand_name', sa.String(255), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('generator', sa.String(50), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop logo_generations table."""
    op.drop_table('logo_generations')
