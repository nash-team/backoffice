from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.domain.ports.ebook.ebook_port import EbookPort
from backoffice.domain.ports.ebook_query_port import EbookQueryPort
from backoffice.infrastructure.models.ebook_model import EbookModel


class SqlAlchemyEbookRepository(EbookPort):
    def __init__(self, db: Session, query_port: EbookQueryPort | None = None):
        self.db = db
        # Use dependency injection with fallback for backward compatibility
        if query_port is None:
            from backoffice.infrastructure.adapters.queries.sqlalchemy_ebook_query import (
                SqlAlchemyEbookQuery,
            )

            query_port = SqlAlchemyEbookQuery(db)
        self.query_port = query_port

    async def get_all(self) -> list[Ebook]:
        db_ebooks = self.db.query(EbookModel).all()
        return [self._to_domain(ebook) for ebook in db_ebooks]

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        db_ebook = self.db.query(EbookModel).filter(EbookModel.id == ebook_id).first()
        return self._to_domain(db_ebook) if db_ebook else None

    async def get_by_status(self, status: EbookStatus) -> list[Ebook]:
        db_ebooks = self.db.query(EbookModel).filter(EbookModel.status == status.value).all()
        return [self._to_domain(ebook) for ebook in db_ebooks]

    async def get_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        """Récupère une page d'ebooks avec pagination."""
        return await self.query_port.list_paginated(params)

    async def get_paginated_by_status(
        self, status: EbookStatus, params: PaginationParams
    ) -> PaginatedResult[Ebook]:
        """Récupère une page d'ebooks filtrés par statut avec pagination."""
        return await self.query_port.list_paginated_by_status(status, params)

    async def create(self, ebook: Ebook) -> Ebook:
        """Crée un nouvel ebook."""
        # Legacy cost tracking removed - now in generation_costs feature
        # Cost data is tracked separately via TokenUsageModel/ImageUsageModel

        db_ebook = EbookModel(
            title=ebook.title,
            author=ebook.author,
            status=ebook.status.value,
            preview_url=ebook.preview_url,
            drive_id=ebook.drive_id,
            created_at=datetime.now(UTC),
            theme_id=ebook.theme_id,
            theme_version=ebook.theme_version,
            audience=ebook.audience,
            structure_json=ebook.structure_json,
            page_count=ebook.page_count,
        )
        self.db.add(db_ebook)
        self.db.commit()
        self.db.refresh(db_ebook)
        return self._to_domain(db_ebook)

    async def update(self, ebook: Ebook) -> Ebook:
        """Met à jour un ebook existant."""
        db_ebook = self.db.query(EbookModel).filter(EbookModel.id == ebook.id).first()
        if not db_ebook:
            raise ValueError(f"Ebook with id {ebook.id} not found")

        db_ebook.title = ebook.title
        db_ebook.author = ebook.author
        db_ebook.status = ebook.status.value
        db_ebook.preview_url = ebook.preview_url
        db_ebook.drive_id = ebook.drive_id
        db_ebook.theme_id = ebook.theme_id
        db_ebook.theme_version = ebook.theme_version
        db_ebook.audience = ebook.audience
        db_ebook.structure_json = ebook.structure_json
        db_ebook.page_count = ebook.page_count

        # Legacy cost tracking removed - now in generation_costs feature

        self.db.commit()
        self.db.refresh(db_ebook)
        return self._to_domain(db_ebook)

    async def save(self, ebook: Ebook) -> Ebook:
        """Sauvegarde un ebook (create ou update selon qu'il existe déjà)."""
        if ebook.id is None:
            return await self.create(ebook)
        else:
            return await self.update(ebook)

    async def get_ebook_bytes(self, ebook_id: int) -> bytes | None:
        """Récupère les bytes du PDF d'un ebook."""
        db_ebook = self.db.query(EbookModel).filter(EbookModel.id == ebook_id).first()
        return db_ebook.ebook_bytes if db_ebook else None

    async def save_ebook_bytes(self, ebook_id: int, ebook_bytes: bytes) -> None:
        """Sauvegarde les bytes du PDF d'un ebook."""
        db_ebook = self.db.query(EbookModel).filter(EbookModel.id == ebook_id).first()
        if not db_ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        db_ebook.ebook_bytes = ebook_bytes
        self.db.commit()

    def _to_domain(self, db_ebook: EbookModel) -> Ebook:
        # Legacy generation_metadata removed - now in generation_costs feature
        # Cost tracking is via TokenUsageModel/ImageUsageModel linked by request_id

        return Ebook(
            id=int(db_ebook.id),
            title=str(db_ebook.title),
            author=str(db_ebook.author),
            status=EbookStatus(db_ebook.status),
            preview_url=str(db_ebook.preview_url) if db_ebook.preview_url else None,
            drive_id=str(db_ebook.drive_id) if db_ebook.drive_id else None,
            created_at=db_ebook.created_at,
            theme_id=str(db_ebook.theme_id) if db_ebook.theme_id else None,
            theme_version=str(db_ebook.theme_version) if db_ebook.theme_version else None,
            audience=str(db_ebook.audience) if db_ebook.audience else None,
            structure_json=db_ebook.structure_json,
            page_count=db_ebook.page_count,
        )
