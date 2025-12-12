"""Unit tests for RegenerationService (Chicago style with fakes)."""

import base64
from datetime import datetime

import pytest

from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    EbookConfig,
    EbookStatus,
)
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage

# === Fakes ===


class FakeAssemblyService:
    """Fake assembly service for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0
        self.last_cover: AssembledPage | None = None
        self.last_pages: list[AssembledPage] = []
        self.last_output_path: str | None = None

    async def assemble_ebook(
        self,
        cover: AssembledPage,
        pages: list[AssembledPage],
        output_path: str,
    ) -> None:
        """Fake assembly - writes fake PDF."""
        self.call_count += 1
        self.last_cover = cover
        self.last_pages = pages
        self.last_output_path = output_path

        if self.should_fail:
            raise Exception("Fake assembly failure")

        # Write fake PDF to output path
        with open(output_path, "wb") as f:
            f.write(b"%PDF-1.7 fake assembled pdf content")


class FakeFileStorage:
    """Fake file storage for testing."""

    def __init__(self, mode: str = "succeed"):
        """Initialize fake storage.

        Args:
            mode: Behavior mode (succeed, unavailable, fail_upload)
        """
        self.mode = mode
        self.upload_count = 0
        self.uploads: list[dict] = []

    def is_available(self) -> bool:
        return self.mode != "unavailable"

    async def upload_ebook(self, file_bytes: bytes, filename: str, metadata: dict | None = None) -> dict[str, str]:
        self.upload_count += 1
        self.uploads.append({"filename": filename, "size": len(file_bytes), "metadata": metadata})

        if self.mode == "fail_upload":
            raise Exception("Fake upload failure")

        return {
            "storage_id": f"fake_drive_id_{self.upload_count}",
            "storage_url": f"https://drive.google.com/fake/{self.upload_count}",
        }


class FakeEbookRepository:
    """Fake ebook repository for testing."""

    def __init__(self):
        self._ebooks: dict[int, Ebook] = {}
        self._ebook_bytes: dict[int, bytes] = {}
        self.save_bytes_count = 0

    async def save_ebook_bytes(self, ebook_id: int, pdf_bytes: bytes) -> None:
        """Save PDF bytes for ebook."""
        self.save_bytes_count += 1
        self._ebook_bytes[ebook_id] = pdf_bytes

    def get_saved_bytes(self, ebook_id: int) -> bytes | None:
        """Helper to verify saved bytes."""
        return self._ebook_bytes.get(ebook_id)


# === Fixtures ===


def _create_fake_png() -> bytes:
    """Create a minimal valid PNG for testing."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _create_sample_ebook(
    ebook_id: int = 1,
    status: EbookStatus = EbookStatus.DRAFT,
    page_count: int = 5,
    with_structure: bool = True,
) -> Ebook:
    """Create a sample ebook for testing."""
    fake_b64 = base64.b64encode(_create_fake_png()).decode("utf-8")

    structure_json = None
    if with_structure:
        structure_json = {
            "pages_meta": [
                {"page_number": 0, "title": "Cover", "image_data_base64": fake_b64, "prompt": "Cover prompt"},
                *[{"page_number": i, "title": f"Page {i}", "image_data_base64": fake_b64, "prompt": f"Prompt {i}"} for i in range(1, page_count - 1)],
                {"page_number": page_count - 1, "title": "Back Cover", "image_data_base64": fake_b64, "prompt": "Back prompt"},
            ]
        }

    return Ebook(
        id=ebook_id,
        title="Test Coloring Book",
        author="Test Author",
        created_at=datetime.now(),
        status=status,
        config=EbookConfig(ebook_type="coloring_book", number_of_pages=25),
        page_count=page_count,
        structure_json=structure_json,
    )


# === Tests ===


class TestRegenerationServiceValidation:
    """Test cases for RegenerationService validation methods."""

    @pytest.fixture
    def assembly_service(self):
        return FakeAssemblyService()

    @pytest.fixture
    def file_storage(self):
        return FakeFileStorage(mode="succeed")

    @pytest.fixture
    def service(self, assembly_service, file_storage):
        return RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

    def test_validate_draft_ebook_success(self, service):
        """Test validation passes for DRAFT ebook with structure."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)

        # Act - should not raise
        service.validate_ebook_for_regeneration(ebook)

    def test_validate_approved_ebook_fails(self, service):
        """Test validation fails for APPROVED ebook."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.APPROVED)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.validate_ebook_for_regeneration(ebook)

        assert "APPROVED" in str(exc_info.value)
        assert "DRAFT" in str(exc_info.value)

    def test_validate_rejected_ebook_fails(self, service):
        """Test validation fails for REJECTED ebook."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.REJECTED)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.validate_ebook_for_regeneration(ebook)

        assert "REJECTED" in str(exc_info.value)

    def test_validate_ebook_without_structure_fails(self, service):
        """Test validation fails for ebook without structure_json."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT, with_structure=False)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.validate_ebook_for_regeneration(ebook)

        assert "structure is missing" in str(exc_info.value)

    def test_validate_ebook_without_pages_meta_fails(self, service):
        """Test validation fails for ebook without pages_meta in structure."""
        # Arrange
        ebook = _create_sample_ebook(status=EbookStatus.DRAFT)
        ebook.structure_json = {"other_key": "value"}  # Missing pages_meta

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.validate_ebook_for_regeneration(ebook)

        assert "structure is missing" in str(exc_info.value)


class TestRegenerationServicePageAssembly:
    """Test cases for RegenerationService page assembly methods."""

    @pytest.fixture
    def assembly_service(self):
        return FakeAssemblyService()

    @pytest.fixture
    def file_storage(self):
        return FakeFileStorage(mode="succeed")

    @pytest.fixture
    def service(self, assembly_service, file_storage):
        return RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

    def test_assemble_pages_from_structure(self, service):
        """Test converting structure_json to AssembledPage objects."""
        # Arrange
        ebook = _create_sample_ebook(page_count=3)
        pages_meta = ebook.structure_json["pages_meta"]

        # Act
        assembled_pages = service.assemble_pages_from_structure(pages_meta)

        # Assert
        assert len(assembled_pages) == 3
        assert assembled_pages[0].page_number == 0
        assert assembled_pages[0].title == "Cover"
        assert assembled_pages[1].page_number == 1
        assert assembled_pages[1].title == "Page 1"
        assert assembled_pages[2].page_number == 2
        assert assembled_pages[2].title == "Back Cover"

    def test_assemble_pages_decodes_base64_images(self, service):
        """Test that base64 images are decoded correctly."""
        # Arrange
        ebook = _create_sample_ebook(page_count=2)
        pages_meta = ebook.structure_json["pages_meta"]

        # Act
        assembled_pages = service.assemble_pages_from_structure(pages_meta)

        # Assert - image_data should be decoded PNG bytes
        assert assembled_pages[0].image_data.startswith(b"\x89PNG")
        assert assembled_pages[1].image_data.startswith(b"\x89PNG")

    def test_assemble_pages_default_format(self, service):
        """Test that default format is PNG when not specified."""
        # Arrange
        fake_b64 = base64.b64encode(_create_fake_png()).decode("utf-8")
        pages_meta = [
            {"page_number": 0, "title": "Page 0", "image_data_base64": fake_b64}  # No format
        ]

        # Act
        assembled_pages = service.assemble_pages_from_structure(pages_meta)

        # Assert
        assert assembled_pages[0].image_format == "PNG"

    def test_assemble_pages_respects_format(self, service):
        """Test that specified format is preserved."""
        # Arrange
        fake_b64 = base64.b64encode(_create_fake_png()).decode("utf-8")
        pages_meta = [{"page_number": 0, "title": "Page 0", "image_data_base64": fake_b64, "image_format": "JPEG"}]

        # Act
        assembled_pages = service.assemble_pages_from_structure(pages_meta)

        # Assert
        assert assembled_pages[0].image_format == "JPEG"


class TestRegenerationServicePageUpdate:
    """Test cases for RegenerationService page update methods."""

    @pytest.fixture
    def assembly_service(self):
        return FakeAssemblyService()

    @pytest.fixture
    def file_storage(self):
        return FakeFileStorage(mode="succeed")

    @pytest.fixture
    def service(self, assembly_service, file_storage):
        return RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

    def test_update_page_in_structure(self, service):
        """Test updating a single page in structure."""
        # Arrange
        ebook = _create_sample_ebook(page_count=3)
        pages_meta = ebook.structure_json["pages_meta"]
        new_image_data = b"\x89PNG new image data"

        # Act
        updated_pages = service.update_page_in_structure(
            pages_meta=pages_meta,
            page_number=1,
            new_image_data=new_image_data,
        )

        # Assert
        assert len(updated_pages) == 3
        # Page 1 should be updated
        assert updated_pages[1]["page_number"] == 1
        assert updated_pages[1]["title"] == "Page 1"  # Default title for non-cover
        assert updated_pages[1]["image_format"] == "PNG"
        # Verify base64 encoding
        decoded = base64.b64decode(updated_pages[1]["image_data_base64"])
        assert decoded == new_image_data

    def test_update_cover_page_title(self, service):
        """Test that cover page (page 0) gets 'Cover' title by default."""
        # Arrange
        ebook = _create_sample_ebook(page_count=2)
        pages_meta = ebook.structure_json["pages_meta"]
        new_image_data = b"\x89PNG new cover"

        # Act
        updated_pages = service.update_page_in_structure(
            pages_meta=pages_meta,
            page_number=0,
            new_image_data=new_image_data,
        )

        # Assert
        assert updated_pages[0]["title"] == "Cover"

    def test_update_page_with_custom_title(self, service):
        """Test updating page with custom title."""
        # Arrange
        ebook = _create_sample_ebook(page_count=2)
        pages_meta = ebook.structure_json["pages_meta"]
        new_image_data = b"\x89PNG new image"

        # Act
        updated_pages = service.update_page_in_structure(
            pages_meta=pages_meta,
            page_number=1,
            new_image_data=new_image_data,
            title="Custom Title",
        )

        # Assert
        assert updated_pages[1]["title"] == "Custom Title"

    def test_update_page_preserves_existing_prompt(self, service):
        """Test that existing prompt is preserved when not provided."""
        # Arrange
        ebook = _create_sample_ebook(page_count=2)
        pages_meta = ebook.structure_json["pages_meta"]
        original_prompt = pages_meta[1]["prompt"]
        new_image_data = b"\x89PNG new image"

        # Act - don't provide prompt
        updated_pages = service.update_page_in_structure(
            pages_meta=pages_meta,
            page_number=1,
            new_image_data=new_image_data,
        )

        # Assert
        assert updated_pages[1]["prompt"] == original_prompt

    def test_update_page_with_new_prompt(self, service):
        """Test updating page with new prompt."""
        # Arrange
        ebook = _create_sample_ebook(page_count=2)
        pages_meta = ebook.structure_json["pages_meta"]
        new_image_data = b"\x89PNG new image"

        # Act
        updated_pages = service.update_page_in_structure(
            pages_meta=pages_meta,
            page_number=1,
            new_image_data=new_image_data,
            prompt="New prompt for regeneration",
        )

        # Assert
        assert updated_pages[1]["prompt"] == "New prompt for regeneration"

    def test_update_page_does_not_modify_other_pages(self, service):
        """Test that updating one page doesn't affect others."""
        # Arrange
        ebook = _create_sample_ebook(page_count=3)
        pages_meta = ebook.structure_json["pages_meta"]
        original_page_0 = pages_meta[0]["image_data_base64"]
        original_page_2 = pages_meta[2]["image_data_base64"]
        new_image_data = b"\x89PNG new image"

        # Act
        updated_pages = service.update_page_in_structure(
            pages_meta=pages_meta,
            page_number=1,
            new_image_data=new_image_data,
        )

        # Assert - other pages unchanged
        assert updated_pages[0]["image_data_base64"] == original_page_0
        assert updated_pages[2]["image_data_base64"] == original_page_2


class TestRegenerationServiceRebuild:
    """Test cases for RegenerationService rebuild and upload methods."""

    @pytest.fixture
    def assembly_service(self):
        return FakeAssemblyService()

    @pytest.fixture
    def file_storage(self):
        return FakeFileStorage(mode="succeed")

    @pytest.fixture
    def ebook_repository(self):
        return FakeEbookRepository()

    @pytest.fixture
    def service(self, assembly_service, file_storage):
        return RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )

    async def test_rebuild_and_upload_pdf_success(self, service, assembly_service, file_storage, ebook_repository):
        """Test successful PDF rebuild and upload."""
        # Arrange
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
            AssembledPage(page_number=1, title="Page 1", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act
        pdf_path, preview_url = await service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=ebook_repository,
        )

        # Assert
        assert pdf_path.exists()
        assert assembly_service.call_count == 1
        assert file_storage.upload_count == 1
        assert preview_url is not None
        assert ebook_repository.save_bytes_count == 1

    async def test_rebuild_saves_pdf_bytes_to_database(self, service, ebook_repository):
        """Test that PDF bytes are saved to database."""
        # Arrange
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act
        await service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=ebook_repository,
        )

        # Assert
        saved_bytes = ebook_repository.get_saved_bytes(ebook.id)
        assert saved_bytes is not None
        assert saved_bytes.startswith(b"%PDF")

    async def test_rebuild_without_storage(self, assembly_service, ebook_repository):
        """Test rebuild when storage is unavailable."""
        # Arrange
        file_storage = FakeFileStorage(mode="unavailable")
        service = RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act
        pdf_path, preview_url = await service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=ebook_repository,
        )

        # Assert - PDF created but no upload
        assert pdf_path.exists()
        assert file_storage.upload_count == 0
        assert preview_url is None
        # But bytes are still saved to database
        assert ebook_repository.save_bytes_count == 1

    async def test_rebuild_storage_upload_fails_gracefully(self, assembly_service, ebook_repository):
        """Test that storage upload failure doesn't break rebuild."""
        # Arrange
        file_storage = FakeFileStorage(mode="fail_upload")
        service = RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act - should NOT raise
        pdf_path, preview_url = await service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=ebook_repository,
        )

        # Assert
        assert pdf_path.exists()
        assert preview_url is None  # Upload failed, no URL
        assert ebook_repository.save_bytes_count == 1

    async def test_rebuild_with_custom_filename_suffix(self, service, file_storage, ebook_repository):
        """Test rebuild with custom filename suffix."""
        # Arrange
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act
        pdf_path, _ = await service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=ebook_repository,
            filename_suffix="cover_regenerated",
        )

        # Assert
        assert "cover_regenerated" in str(pdf_path)
        assert "cover_regenerated" in file_storage.uploads[0]["filename"]

    async def test_rebuild_splits_cover_and_content(self, service, assembly_service, ebook_repository):
        """Test that assembled pages are split into cover and content."""
        # Arrange
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
            AssembledPage(page_number=1, title="Page 1", image_data=_create_fake_png(), image_format="PNG"),
            AssembledPage(page_number=2, title="Page 2", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act
        await service.rebuild_and_upload_pdf(
            ebook=ebook,
            assembled_pages=assembled_pages,
            ebook_repository=ebook_repository,
        )

        # Assert
        assert assembly_service.last_cover.page_number == 0
        assert assembly_service.last_cover.title == "Cover"
        assert len(assembly_service.last_pages) == 2
        assert assembly_service.last_pages[0].page_number == 1
        assert assembly_service.last_pages[1].page_number == 2

    async def test_rebuild_assembly_fails(self, ebook_repository):
        """Test that assembly failure propagates."""
        # Arrange
        assembly_service = FakeAssemblyService(should_fail=True)
        file_storage = FakeFileStorage(mode="succeed")
        service = RegenerationService(
            assembly_service=assembly_service,
            file_storage=file_storage,
        )
        ebook = _create_sample_ebook()
        assembled_pages = [
            AssembledPage(page_number=0, title="Cover", image_data=_create_fake_png(), image_format="PNG"),
        ]

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service.rebuild_and_upload_pdf(
                ebook=ebook,
                assembled_pages=assembled_pages,
                ebook_repository=ebook_repository,
            )

        assert "Fake assembly failure" in str(exc_info.value)
