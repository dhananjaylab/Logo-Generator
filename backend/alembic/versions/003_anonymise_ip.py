"""Replace raw ip_address column with anonymised ip_hash (GDPR / VULN-04)

Raw IP addresses stored in the logo_generations table are personal data under
GDPR Article 4(1) and CCPA.  This migration:

  1. Adds a new ip_hash column (String 16) to hold a salted SHA-256 hash
     of the IP address, derived via utils.anonymise_ip().
  2. NULLs out all existing raw ip_address values — we cannot retroactively
     hash them because the salt was not set when they were recorded, and
     using an unsalted hash would be trivially reversible.
  3. Drops the ip_address column entirely.

After running this migration, set IP_HASH_SALT in your environment before
restarting the backend.  Without the salt, anonymise_ip() returns None and
no IP-derived data is stored at all (fail-safe behaviour).

Revision ID: 003_anonymise_ip
Revises: 7238d453de14
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "003_anonymise_ip"
down_revision = "7238d453de14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: add the new anonymised column.
    op.add_column(
        "logo_generations",
        sa.Column("ip_hash", sa.String(16), nullable=True),
    )

    # Step 2: erase existing raw IP data to comply with GDPR storage-limitation
    # principle (Article 5(1)(e)).  We cannot hash retroactively because the
    # IP_HASH_SALT was not available when these rows were inserted.
    op.execute("UPDATE logo_generations SET ip_address = NULL")

    # Step 3: drop the now-emptied raw column.
    op.drop_column("logo_generations", "ip_address")


def downgrade() -> None:
    # Restores the column structure but the data is permanently gone —
    # this is intentional and correct for GDPR compliance.
    op.add_column(
        "logo_generations",
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.drop_column("logo_generations", "ip_hash")
