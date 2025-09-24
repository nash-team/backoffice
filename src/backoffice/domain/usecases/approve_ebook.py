from backoffice.domain.entities.ebook import Ebook, EbookStatus
from backoffice.domain.ports.ebook.ebook_port import EbookPort


class ApproveEbookUseCase:
    def __init__(self, ebook_repository: EbookPort):
        self.ebook_repository = ebook_repository

    async def execute(self, ebook_id: int) -> Ebook:
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        if not ebook:
            raise ValueError(f"Ebook with id {ebook_id} not found")

        if ebook.status not in [EbookStatus.PENDING, EbookStatus.REJECTED]:
            raise ValueError(
                f"Cannot approve ebook with status {ebook.status.value}. "
                f"Only PENDING or REJECTED ebooks can be approved."
            )

        ebook.status = EbookStatus.APPROVED
        return await self.ebook_repository.save(ebook)
