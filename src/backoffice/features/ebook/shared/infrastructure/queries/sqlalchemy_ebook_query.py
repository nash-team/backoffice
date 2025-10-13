from sqlalchemy.orm import Session

from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.ports.ebook_query_port import EbookQueryPort
from backoffice.features.ebook.shared.infrastructure.models.ebook_model import EbookModel
from backoffice.features.shared.domain.entities.pagination import PaginatedResult, PaginationParams


class SqlAlchemyEbookQuery(EbookQueryPort):
    """SQLAlchemy implementation of ebook query operations"""

    def __init__(self, db: Session):
        self.db = db

    async def list_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        """List ebooks with pagination"""
        # Get total count
        total_count = self.db.query(EbookModel).count()

        # Get paginated results
        db_ebooks = (
            self.db.query(EbookModel)
            .order_by(EbookModel.created_at.desc())
            .offset(params.offset)
            .limit(params.size)
            .all()
        )

        ebooks = [self._to_domain(ebook) for ebook in db_ebooks]

        return PaginatedResult(
            items=ebooks,
            total_count=total_count,
            page=params.page,
            size=params.size,
        )

    async def list_paginated_by_status(
        self, status: EbookStatus, params: PaginationParams
    ) -> PaginatedResult[Ebook]:
        """List ebooks filtered by status with pagination"""
        # Get total count for the specific status
        total_count = self.db.query(EbookModel).filter(EbookModel.status == status.value).count()

        # Get paginated results for the specific status
        db_ebooks = (
            self.db.query(EbookModel)
            .filter(EbookModel.status == status.value)
            .order_by(EbookModel.created_at.desc())
            .offset(params.offset)
            .limit(params.size)
            .all()
        )

        ebooks = [self._to_domain(ebook) for ebook in db_ebooks]

        return PaginatedResult(
            items=ebooks,
            total_count=total_count,
            page=params.page,
            size=params.size,
        )

    def _to_domain(self, db_ebook: EbookModel) -> Ebook:
        """Convert database model to domain entity"""
        return Ebook(
            id=int(db_ebook.id),
            title=str(db_ebook.title),
            author=str(db_ebook.author),
            status=EbookStatus(db_ebook.status),
            preview_url=str(db_ebook.preview_url) if db_ebook.preview_url else None,
            drive_id=str(db_ebook.drive_id) if db_ebook.drive_id else None,
            created_at=db_ebook.created_at,
        )
