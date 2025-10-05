"""
Ce fichier définit le modèle EbookModel pour SQLAlchemy (ORM).
Il représente la structure de la table 'ebooks' dans la base de données.
Ce modèle est utilisé uniquement pour l'accès et
la manipulation des données en base (infrastructure).
Il ne doit pas être utilisé directement dans la logique métier ou l'API.
"""

from datetime import datetime

from sqlalchemy import JSON, LargeBinary, String
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

    # Legacy cost tracking columns removed - now in generation_costs feature
    # See: features/generation_costs/infrastructure/models/token_usage_model.py
