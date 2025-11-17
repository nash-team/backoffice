"""drop_token_usage_tables

Revision ID: b34b0200e8da
Revises: e7c51f753bca
Create Date: 2025-11-17 15:24:37.126837

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b34b0200e8da"
down_revision: str | None = "e7c51f753bca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop token_usage table if it exists
    op.execute("DROP TABLE IF EXISTS token_usage CASCADE")

    # Drop cost_calculation table if it exists
    op.execute("DROP TABLE IF EXISTS cost_calculation CASCADE")


def downgrade() -> None:
    # Note: Downgrade not supported - tables cannot be recreated without generation_costs code
    pass
