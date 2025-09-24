"""Update ebook status enum values

Revision ID: ac1b2ce11e70
Revises: 759a887542cb
Create Date: 2025-09-24 10:13:22.760880

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac1b2ce11e70"
down_revision: str | None = "097b735e8fb8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Convert column to varchar to allow data migration
    op.execute("ALTER TABLE ebooks ALTER COLUMN status TYPE varchar(20) USING status::text;")

    # Step 2: Update existing data from old enum values to new ones
    op.execute("UPDATE ebooks SET status = 'APPROVED' WHERE status = 'VALIDATED';")
    # PENDING remains PENDING

    # Step 3: Drop and recreate enum with new values
    op.execute("DROP TYPE ebookstatus CASCADE;")
    op.execute("CREATE TYPE ebookstatus AS ENUM ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED');")

    # Step 4: Convert column back to enum
    op.execute("ALTER TABLE ebooks ALTER COLUMN status TYPE ebookstatus USING status::ebookstatus;")


def downgrade() -> None:
    # Convert column to varchar for data migration
    op.execute("ALTER TABLE ebooks ALTER COLUMN status TYPE varchar(20) USING status::text;")

    # Update data back to old enum values
    op.execute("UPDATE ebooks SET status = 'VALIDATED' WHERE status = 'APPROVED';")

    # Recreate old enum
    op.execute("DROP TYPE ebookstatus CASCADE;")
    op.execute("CREATE TYPE ebookstatus AS ENUM ('PENDING', 'VALIDATED');")

    # Convert back to enum
    op.execute("ALTER TABLE ebooks ALTER COLUMN status TYPE ebookstatus USING status::ebookstatus;")
