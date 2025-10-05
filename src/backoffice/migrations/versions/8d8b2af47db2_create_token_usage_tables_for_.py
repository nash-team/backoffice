"""create_token_usage_tables_for_generation_costs_feature

Revision ID: 8d8b2af47db2
Revises: 4d38adfff641
Create Date: 2025-10-04 19:47:11.331185

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d8b2af47db2"
down_revision: str | None = "4d38adfff641"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create token_usages table
    op.create_table(
        "token_usages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost", sa.NUMERIC(precision=10, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ebook_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_token_usages_request_id"), "token_usages", ["request_id"], unique=False
    )
    op.create_index(op.f("ix_token_usages_ebook_id"), "token_usages", ["ebook_id"], unique=False)

    # Create image_usages table
    op.create_table(
        "image_usages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("input_images", sa.Integer(), nullable=False),
        sa.Column("output_images", sa.Integer(), nullable=False),
        sa.Column("cost", sa.NUMERIC(precision=10, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ebook_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_image_usages_request_id"), "image_usages", ["request_id"], unique=False
    )
    op.create_index(op.f("ix_image_usages_ebook_id"), "image_usages", ["ebook_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_image_usages_ebook_id"), table_name="image_usages")
    op.drop_index(op.f("ix_image_usages_request_id"), table_name="image_usages")
    op.drop_table("image_usages")
    op.drop_index(op.f("ix_token_usages_ebook_id"), table_name="token_usages")
    op.drop_index(op.f("ix_token_usages_request_id"), table_name="token_usages")
    op.drop_table("token_usages")
