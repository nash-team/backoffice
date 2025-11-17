"""drop_unused_tables

Revision ID: e7c51f753bca
Revises: b1c2d3e4f5g6
Create Date: 2025-11-17 14:52:47.661405

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7c51f753bca"
down_revision: Union[str, None] = "b1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unused tables: book_memory and orchestrator_config.

    These tables were never used in the codebase:
    - book_memory: 0 records, no code references
    - orchestrator_config: 1 orphaned record, no code references
    """
    # Drop unused tables (no foreign key dependencies)
    op.drop_table("book_memory")
    op.drop_table("orchestrator_config")


def downgrade() -> None:
    """Recreate dropped tables if rollback is needed.

    Note: This will recreate empty tables. Original data is not restored.
    """
    # Recreate book_memory table
    op.create_table(
        "book_memory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("theme", sa.String(), nullable=True),
        sa.Column("audience", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("ebook_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Recreate orchestrator_config table
    op.create_table(
        "orchestrator_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("config_key", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("max_concurrent_productions", sa.Integer(), nullable=True),
        sa.Column("poll_interval", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("enable_market_analysis", sa.Boolean(), nullable=True),
        sa.Column("enable_duplicate_check", sa.Boolean(), nullable=True),
        sa.Column("enable_auto_publish", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
