"""remove_pending_status_from_ebook

Revision ID: 3ce9199f7afa
Revises: a4fa571b69fb
Create Date: 2025-10-02 10:48:59.233428

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3ce9199f7afa"
down_revision: str | None = "a4fa571b69fb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Update any existing PENDING ebooks to DRAFT
    op.execute(
        """
        UPDATE ebooks
        SET status = 'DRAFT'
        WHERE status = 'PENDING'
        """
    )

    # Remove PENDING from enum (PostgreSQL)
    # Note: This requires recreating the enum type
    op.execute("ALTER TYPE ebookstatus RENAME TO ebookstatus_old")
    op.execute("CREATE TYPE ebookstatus AS ENUM ('DRAFT', 'APPROVED', 'REJECTED')")
    op.execute(
        """
        ALTER TABLE ebooks
        ALTER COLUMN status TYPE ebookstatus
        USING status::text::ebookstatus
        """
    )
    op.execute("DROP TYPE ebookstatus_old")


def downgrade() -> None:
    # Recreate enum with PENDING
    op.execute("ALTER TYPE ebookstatus RENAME TO ebookstatus_old")
    op.execute("CREATE TYPE ebookstatus AS ENUM ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED')")
    op.execute(
        """
        ALTER TABLE ebooks
        ALTER COLUMN status TYPE ebookstatus
        USING status::text::ebookstatus
        """
    )
    op.execute("DROP TYPE ebookstatus_old")
