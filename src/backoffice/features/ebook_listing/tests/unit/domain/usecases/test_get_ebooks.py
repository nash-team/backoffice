from datetime import datetime

import pytest

from backoffice.features.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.shared.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.features.shared.domain.ports.ebook.ebook_port import EbookPort
from backoffice.features.ebook_listing.domain.usecases.get_ebooks import GetEbooksUseCase


class FakeEbookRepository(EbookPort):
    def __init__(self):
        self._ebooks = []
        self._id_counter = 1

    async def get_all(self) -> list[Ebook]:
        return self._ebooks

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        for ebook in self._ebooks:
            if ebook.id == ebook_id:
                return ebook
        return None

    async def get_by_status(self, status: EbookStatus) -> list[Ebook]:
        return [e for e in self._ebooks if e.status == status]

    async def create(self, ebook: Ebook) -> Ebook:
        ebook.id = self._id_counter
        self._id_counter += 1
        self._ebooks.append(ebook)
        return ebook

    async def save(self, ebook: Ebook) -> Ebook:
        for i, e in enumerate(self._ebooks):
            if e.id == ebook.id:
                self._ebooks[i] = ebook
                return ebook
        self._ebooks.append(ebook)
        return ebook

    async def update(self, ebook: Ebook) -> Ebook:
        return await self.save(ebook)

    async def get_ebook_bytes(self, ebook_id: int) -> bytes | None:
        return None

    async def save_ebook_bytes(self, ebook_id: int, ebook_bytes: bytes) -> None:
        pass

    async def get_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        offset = params.offset
        limit = params.size
        total = len(self._ebooks)
        items = self._ebooks[offset : offset + limit]
        return PaginatedResult(items=items, total_count=total, page=params.page, size=params.size)

    async def get_paginated_by_status(
        self, status: EbookStatus, params: PaginationParams
    ) -> PaginatedResult[Ebook]:
        filtered = [e for e in self._ebooks if e.status == status]
        offset = params.offset
        limit = params.size
        total = len(filtered)
        items = filtered[offset : offset + limit]
        return PaginatedResult(items=items, total_count=total, page=params.page, size=params.size)


@pytest.fixture
def repository():
    return FakeEbookRepository()


@pytest.fixture
def usecase(repository):
    return GetEbooksUseCase(repository)


@pytest.fixture
async def _sample_ebooks(repository):
    ebooks = [
        Ebook(1, "Python pour les débutants", "John Doe", datetime.now(), EbookStatus.DRAFT),
        Ebook(2, "FastAPI Masterclass", "Jane Smith", datetime.now(), EbookStatus.APPROVED),
        Ebook(3, "Django REST", "Alice Johnson", datetime.now(), EbookStatus.DRAFT),
    ]
    for ebook in ebooks:
        await repository.save(ebook)
    return ebooks


@pytest.mark.asyncio
async def test_get_all_ebooks(usecase, _sample_ebooks):
    # Given (_sample_ebooks fixture already saved ebooks in repository)

    # When
    ebooks = await usecase.execute()

    # Then
    assert len(ebooks) == 3
    assert all(isinstance(ebook, Ebook) for ebook in ebooks)


@pytest.mark.asyncio
async def test_get_pending_ebooks(usecase, _sample_ebooks):
    # Given (_sample_ebooks fixture already saved ebooks in repository)

    # When
    ebooks = await usecase.execute(EbookStatus.DRAFT)

    # Then
    assert len(ebooks) == 2
    assert all(ebook.status == EbookStatus.DRAFT for ebook in ebooks)


@pytest.mark.asyncio
async def test_get_approved_ebooks(usecase, _sample_ebooks):
    # Given (_sample_ebooks fixture already saved ebooks in repository)

    # When
    ebooks = await usecase.execute(EbookStatus.APPROVED)

    # Then
    assert len(ebooks) == 1
    assert all(ebook.status == EbookStatus.APPROVED for ebook in ebooks)


@pytest.mark.asyncio
async def test_get_ebooks_empty_repository(usecase):
    # When
    ebooks = await usecase.execute()

    # Then
    assert len(ebooks) == 0
