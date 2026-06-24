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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # P3.2 - cost tracking column on logo_generations.
    # Nullable so existing rows (generated before this migration) remain valid
    # with cost_usd = NULL rather than requiring a backfill.
    logo_columns = {column["name"] for column in inspector.get_columns("logo_generations")}
    if "cost_usd" not in logo_columns:
        op.add_column(
            "logo_generations",
            sa.Column("cost_usd", sa.Float(), nullable=True),
        )

    # P3.4 - audit trail table.
    audit_tables = set(inspector.get_table_names())
    if "audit_logs" not in audit_tables:
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
    else:
        audit_columns = {column["name"] for column in inspector.get_columns("audit_logs")}
        missing_columns = {
            "id": sa.Column("id", sa.Integer(), nullable=False),
            "event_type": sa.Column("event_type", sa.String(50), nullable=False),
            "user_id": sa.Column("user_id", sa.String(255), nullable=True),
            "ip_hash": sa.Column("ip_hash", sa.String(16), nullable=True),
            "brand_name": sa.Column("brand_name", sa.String(255), nullable=True),
            "generator": sa.Column("generator", sa.String(50), nullable=True),
            "moderation_flagged": sa.Column("moderation_flagged", sa.Boolean(), nullable=True),
            "moderation_categories": sa.Column("moderation_categories", sa.Text(), nullable=True),
            "cost_usd": sa.Column("cost_usd", sa.Float(), nullable=True),
            "detail": sa.Column("detail", sa.Text(), nullable=True),
            "created_at": sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        }
        for column_name, column in missing_columns.items():
            if column_name not in audit_columns:
                op.add_column("audit_logs", column)

    audit_indexes = {index["name"] for index in inspector.get_indexes("audit_logs")}
    if "ix_audit_logs_user_id" not in audit_indexes:
        op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    if "ix_audit_logs_event_type" not in audit_indexes:
        op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    if "ix_audit_logs_created_at" not in audit_indexes:
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "audit_logs" in inspector.get_table_names():
        audit_indexes = {index["name"] for index in inspector.get_indexes("audit_logs")}
        if "ix_audit_logs_created_at" in audit_indexes:
            op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
        if "ix_audit_logs_event_type" in audit_indexes:
            op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
        if "ix_audit_logs_user_id" in audit_indexes:
            op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
        op.drop_table("audit_logs")

    logo_columns = {column["name"] for column in inspector.get_columns("logo_generations")}
    if "cost_usd" in logo_columns:
        op.drop_column("logo_generations", "cost_usd")
