"""
Ce fichier définit le modèle EbookModel pour SQLAlchemy (ORM).
Il représente la structure de la table 'ebooks' dans la base de données.
Ce modèle est utilisé uniquement pour l'accès et
la manipulation des données en base (infrastructure).
Il ne doit pas être utilisé directement dans la logique métier ou l'API.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, NUMERIC, Integer, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backoffice.domain.entities.ebook import EbookStatus


class Base(DeclarativeBase):
    pass


class EbookModel(Base):
    __tablename__ = "ebooks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=EbookStatus.DRAFT.value)
    preview_url: Mapped[str | None]
    drive_id: Mapped[str | None]
    created_at: Mapped[datetime]

    # Theme-based generation fields
    theme_id: Mapped[str | None] = mapped_column(String(50))
    theme_version: Mapped[str | None] = mapped_column(String(20))
    audience: Mapped[str | None] = mapped_column(String(10))

    # Ebook structure as JSON (for regeneration)
    structure_json: Mapped[dict | None] = mapped_column(JSON)

    # PDF bytes for DRAFT ebooks (awaiting approval)
    ebook_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)

    # Page count for KDP export
    page_count: Mapped[int | None]

    # Generation cost tracking (Decimal for precision)
    generation_cost: Mapped[Decimal | None] = mapped_column(
        NUMERIC(12, 4), nullable=True, index=True
    )
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Provider and model used for generation
    generation_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generation_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_duration_seconds: Mapped[float | None] = mapped_column(NUMERIC(10, 2), nullable=True)
