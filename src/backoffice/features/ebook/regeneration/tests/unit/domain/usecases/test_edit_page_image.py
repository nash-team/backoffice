import base64
from datetime import datetime

import pytest

from backoffice.features.ebook.regeneration.domain.usecases.edit_page_image import (
    EditPageImageUseCase,
)
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.domain.entities.pagination import PaginatedResult, PaginationParams
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError
from backoffice.features.shared.tests.unit.fakes.fake_image_edit_port import FakeImageEditPort


class FakeEbookRepository:
    """Minimal fake repository covering EbookPort surface for tests."""

    def __init__(self, ebook: Ebook):
        self._ebook = ebook
        self.saved: Ebook | None = None
        self.saved_bytes: dict[int, bytes] = {}

    async def get_all(self) -> list[Ebook]:
        return [self._ebook]

    async def get_by_id(self, ebook_id: int) -> Ebook | None:
        return self._ebook if self._ebook.id == ebook_id else None

    async def get_by_status(self, status: EbookStatus) -> list[Ebook]:
        return [self._ebook] if self._ebook.status == status else []

    async def create(self, ebook: Ebook) -> Ebook:
        self.saved = ebook
        return ebook

    async def update(self, ebook: Ebook) -> Ebook:
        self.saved = ebook
        return ebook

    async def save(self, ebook: Ebook) -> Ebook:
        self.saved = ebook
        return ebook

    async def get_paginated(self, params: PaginationParams) -> PaginatedResult[Ebook]:
        return PaginatedResult(items=[self._ebook], total=1, page=params.page, page_size=params.page_size)

    async def get_paginated_by_status(self, status: EbookStatus, params: PaginationParams) -> PaginatedResult[Ebook]:
        items = [self._ebook] if self._ebook.status == status else []
        total = len(items)
        return PaginatedResult(items=items, total=total, page=params.page, page_size=params.page_size)

    async def get_ebook_bytes(self, ebook_id: int) -> bytes | None:
        return self.saved_bytes.get(ebook_id)

    async def save_ebook_bytes(self, ebook_id: int, ebook_bytes: bytes) -> None:
        self.saved_bytes[ebook_id] = ebook_bytes


def _make_ebook(fallback_image_b64: str) -> Ebook:
    return Ebook(
        id=1,
        title="Test",
        author="Author",
        created_at=datetime.utcnow(),
        status=EbookStatus.DRAFT,
        structure_json={
            "pages_meta": [
                {"page_number": 0, "image_data_base64": base64.b64encode(b"cover").decode()},
                {"page_number": 1, "image_data_base64": fallback_image_b64},
                {"page_number": 2, "image_data_base64": base64.b64encode(b"back").decode()},
            ]
        },
    )


@pytest.mark.asyncio
async def test_edit_uses_modal_image_when_provided():
    modal_bytes = b"MODAL_IMAGE"
    modal_b64 = base64.b64encode(modal_bytes).decode()
    fallback_b64 = base64.b64encode(b"PDF_IMAGE").decode()

    ebook = _make_ebook(fallback_b64)
    repo = FakeEbookRepository(ebook)
    edit_port = FakeImageEditPort(mode="succeed", edited_image_size=20)

    use_case = EditPageImageUseCase(ebook_repository=repo, image_edit_port=edit_port)

    result = await use_case.execute(
        ebook_id=1,
        page_index=1,
        edit_prompt="sharpen eyes",
        current_image_base64=modal_b64,
    )

    assert edit_port.call_count == 1
    assert edit_port.last_image == modal_bytes  # modal image should be the source
    assert result["page_index"] == 1
    assert isinstance(result["image_base64"], str)


@pytest.mark.asyncio
async def test_edit_falls_back_to_structure_json_when_modal_image_missing():
    fallback_bytes = b"PDF_IMAGE"
    fallback_b64 = base64.b64encode(fallback_bytes).decode()

    ebook = _make_ebook(fallback_b64)
    repo = FakeEbookRepository(ebook)
    edit_port = FakeImageEditPort(mode="succeed", edited_image_size=20)

    use_case = EditPageImageUseCase(ebook_repository=repo, image_edit_port=edit_port)

    result = await use_case.execute(
        ebook_id=1,
        page_index=1,
        edit_prompt="adjust shading",
        current_image_base64=None,
    )

    assert edit_port.call_count == 1
    assert edit_port.last_image == fallback_bytes  # fallback to stored PDF/base image
    assert result["page_index"] == 1
    assert isinstance(result["image_base64"], str)


@pytest.mark.asyncio
async def test_edit_raises_on_invalid_modal_base64():
    ebook = _make_ebook(base64.b64encode(b"PDF_IMAGE").decode())
    repo = FakeEbookRepository(ebook)
    edit_port = FakeImageEditPort()
    use_case = EditPageImageUseCase(ebook_repository=repo, image_edit_port=edit_port)

    with pytest.raises(DomainError):
        await use_case.execute(
            ebook_id=1,
            page_index=1,
            edit_prompt="invalid input",
            current_image_base64="@@not-base64@@",
        )
