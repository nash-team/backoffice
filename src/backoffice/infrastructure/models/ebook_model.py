"""
Ce fichier définit le modèle EbookModel pour SQLAlchemy (ORM).
Il représente la structure de la table 'ebooks' dans la base de données.
Ce modèle est utilisé uniquement pour l'accès et
la manipulation des données en base (infrastructure).
Il ne doit pas être utilisé directement dans la logique métier ou l'API.
"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backoffice.domain.entities.ebook import EbookStatus


class Base(DeclarativeBase):
    pass


class EbookModel(Base):
    __tablename__ = "ebooks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=EbookStatus.PENDING.value)
    preview_url: Mapped[str | None]
    drive_id: Mapped[str | None]
    created_at: Mapped[datetime]
