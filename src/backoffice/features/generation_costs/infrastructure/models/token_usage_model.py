"""Database model for token usage tracking."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import NUMERIC, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backoffice.features.ebook.shared.infrastructure.models.ebook_model import Base


class TokenUsageModel(Base):
    """SQLAlchemy model for token usage records.

    Stores individual API call token usage and costs for tracking purposes.
    Part of the generation_costs bounded context.
    """

    __tablename__ = "token_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(255), index=True)
    model: Mapped[str] = mapped_column(String(255))
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    cost: Mapped[Decimal] = mapped_column(NUMERIC(10, 6))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Optional: Link to ebook if applicable
    ebook_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    def to_dict(self) -> dict:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {
            "id": self.id,
            "request_id": self.request_id,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost": self.cost,
            "created_at": self.created_at,
            "ebook_id": self.ebook_id,
        }


class ImageUsageModel(Base):
    """SQLAlchemy model for image usage records.

    Stores individual image generation API call usage and costs.
    Part of the generation_costs bounded context.
    """

    __tablename__ = "image_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(255), index=True)
    model: Mapped[str] = mapped_column(String(255))
    input_images: Mapped[int] = mapped_column(Integer)
    output_images: Mapped[int] = mapped_column(Integer)
    cost: Mapped[Decimal] = mapped_column(NUMERIC(10, 6))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Optional: Link to ebook if applicable
    ebook_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    def to_dict(self) -> dict:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {
            "id": self.id,
            "request_id": self.request_id,
            "model": self.model,
            "input_images": self.input_images,
            "output_images": self.output_images,
            "cost": self.cost,
            "created_at": self.created_at,
            "ebook_id": self.ebook_id,
        }
