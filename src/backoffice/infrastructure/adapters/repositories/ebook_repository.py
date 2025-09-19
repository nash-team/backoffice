from datetime import datetime

from sqlalchemy.orm import Session

from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.infrastructure.models.ebook_model import EbookModel
from backoffice.infrastructure.ports.repositories.ebook_repository_port import EbookRepositoryPort


class SqlAlchemyEbookRepository(EbookRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_all(self) -> list[Ebook]:
        db_ebooks = self.db.query(EbookModel).all()
        return [self._to_domain(ebook) for ebook in db_ebooks]

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        db_ebook = self.db.query(EbookModel).filter(EbookModel.id == ebook_id).first()
        return self._to_domain(db_ebook) if db_ebook else None

    async def get_by_status(self, status: EbookStatus) -> list[Ebook]:
        db_ebooks = self.db.query(EbookModel).filter(EbookModel.status == status.value).all()
        return [self._to_domain(ebook) for ebook in db_ebooks]

    async def create(self, ebook: Ebook) -> Ebook:
        """Crée un nouvel ebook."""
        db_ebook = EbookModel(
            title=ebook.title,
            author=ebook.author,
            status=ebook.status.value,
            preview_url=ebook.preview_url,
            drive_id=ebook.drive_id,
            created_at=datetime.utcnow(),
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

        self.db.commit()
        self.db.refresh(db_ebook)
        return self._to_domain(db_ebook)

    def _to_domain(self, db_ebook: EbookModel) -> Ebook:
        return Ebook(
            id=int(db_ebook.id),
            title=str(db_ebook.title),
            author=str(db_ebook.author),
            status=EbookStatus(db_ebook.status),
            preview_url=str(db_ebook.preview_url) if db_ebook.preview_url else None,
            drive_id=str(db_ebook.drive_id) if db_ebook.drive_id else None,
            created_at=db_ebook.created_at,
        )
