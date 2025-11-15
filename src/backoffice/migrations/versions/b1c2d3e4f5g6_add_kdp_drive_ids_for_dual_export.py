"""add_kdp_drive_ids_for_dual_export

Revision ID: b1c2d3e4f5g6
Revises: aa609b520552
Create Date: 2025-11-15 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: str | None = "aa609b520552"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add drive_id_cover and drive_id_interior columns for KDP dual export.

    These columns store separate Google Drive IDs for:
    - drive_id_cover: KDP Cover PDF (back + spine + front)
    - drive_id_interior: KDP Interior PDF (content pages only)

    The existing drive_id column is kept for backward compatibility.
    """
    op.add_column("ebooks", sa.Column("drive_id_cover", sa.String(), nullable=True))
    op.add_column("ebooks", sa.Column("drive_id_interior", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove drive_id_cover and drive_id_interior columns (for rollback only)."""
    op.drop_column("ebooks", "drive_id_interior")
    op.drop_column("ebooks", "drive_id_cover")
