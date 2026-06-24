"""Add cost tracking column and audit_logs table (P3.2 / P3.4)

Revision ID: 004_cost_and_audit
Revises: 003_anonymise_ip
Create Date: 2026-06-18

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_cost_and_audit"
down_revision = "003_anonymise_ip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # P3.2 — cost tracking column on logo_generations.
    # Nullable so existing rows (generated before this migration) remain valid
    # with cost_usd = NULL rather than requiring a backfill.
    op.add_column(
        "logo_generations",
        sa.Column("cost_usd", sa.Float(), nullable=True),
    )

    # P3.4 — audit trail table.
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("ip_hash", sa.String(16), nullable=True),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("generator", sa.String(50), nullable=True),
        sa.Column("moderation_flagged", sa.Boolean(), nullable=True),
        sa.Column("moderation_categories", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_column("logo_generations", "cost_usd")
