"""remove_legacy_cost_tracking_columns_from_ebooks

Revision ID: aa609b520552
Revises: 8d8b2af47db2
Create Date: 2025-10-05 15:15:43.735529

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa609b520552"
down_revision: str | None = "8d8b2af47db2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove legacy cost tracking columns from ebooks table.

    These columns are now replaced by the generation_costs feature:
    - generation_cost -> CostCalculation.total_cost
    - prompt_tokens -> TokenUsage.prompt_tokens
    - completion_tokens -> TokenUsage.completion_tokens
    - generation_provider -> GenerationMetadata.provider
    - generation_model -> GenerationMetadata.model
    - generation_duration_seconds -> GenerationMetadata.duration_seconds
    """
    # Drop indexes first
    op.drop_index("ix_ebooks_generation_cost", table_name="ebooks")

    # Drop columns
    op.drop_column("ebooks", "generation_cost")
    op.drop_column("ebooks", "prompt_tokens")
    op.drop_column("ebooks", "completion_tokens")
    op.drop_column("ebooks", "generation_provider")
    op.drop_column("ebooks", "generation_model")
    op.drop_column("ebooks", "generation_duration_seconds")


def downgrade() -> None:
    """Restore legacy cost tracking columns (for rollback only)."""
    # Recreate columns
    op.add_column(
        "ebooks", sa.Column("generation_cost", sa.NUMERIC(precision=12, scale=4), nullable=True)
    )
    op.add_column("ebooks", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("ebooks", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("ebooks", sa.Column("generation_provider", sa.String(length=50), nullable=True))
    op.add_column("ebooks", sa.Column("generation_model", sa.String(length=100), nullable=True))
    op.add_column(
        "ebooks",
        sa.Column("generation_duration_seconds", sa.NUMERIC(precision=10, scale=2), nullable=True),
    )

    # Recreate indexes
    op.create_index("ix_ebooks_generation_cost", "ebooks", ["generation_cost"], unique=False)
