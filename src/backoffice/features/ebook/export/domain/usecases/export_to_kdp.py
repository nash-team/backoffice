"""Use case for exporting ebook to Amazon KDP format."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backoffice.features.ebook.export.domain.events.kdp_export_generated_event import (
    KDPExportGeneratedEvent,
)
from backoffice.features.ebook.export.domain.protocols import (
    ImageProviderProtocol,
    KDPAssemblyProviderProtocol,
)
from backoffice.features.ebook.export.domain.services.kdp_export_validator import (
    KdpExportValidator,
)
from backoffice.features.ebook.shared.domain.entities.ebook import (
    Ebook,
    KDPExportConfig,
)
from backoffice.features.ebook.shared.domain.entities.theme_profile import ThemeProfile
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort
from backoffice.features.shared.infrastructure.events.event_bus import EventBus

if TYPE_CHECKING:
    from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import ThemeRepository

logger = logging.getLogger(__name__)


class ExportToKDPUseCase:
    """Use case for exporting an approved ebook to KDP paperback format."""

    def __init__(
        self,
        ebook_repository: EbookPort,
        event_bus: EventBus,
        image_provider: ImageProviderProtocol | None = None,
        kdp_assembly_provider: KDPAssemblyProviderProtocol | None = None,
        theme_repository: ThemeRepository | None = None,
    ):
        """Initialize export to KDP use case.

        Args:
            ebook_repository: Repository for ebook persistence
            event_bus: Event bus for publishing domain events
            image_provider: Optional image provider (uses OpenRouter if None)
            kdp_assembly_provider: Optional KDP assembly provider (uses default if None)
            theme_repository: Optional theme repository for ISBN lookup (uses default if None)
        """
        self.ebook_repository = ebook_repository
        self.event_bus = event_bus
        self.image_provider = image_provider
        self.kdp_assembly_provider = kdp_assembly_provider
        self.theme_repository = theme_repository
        logger.info("ExportToKDPUseCase initialized")

    async def execute(
        self,
        ebook_id: int,
        kdp_config: KDPExportConfig | None = None,
        preview_mode: bool = False,
    ) -> bytes:
        """Export an approved ebook to KDP format.

        Args:
            ebook_id: ID of the ebook to export
            kdp_config: Optional KDP export configuration
            preview_mode: If True, allows DRAFT ebooks (for preview only, not download)

        Returns:
            PDF bytes ready for KDP upload

        Raises:
            DomainError: If ebook not found, not approved, or export fails
        """
        # 1. Load and validate ebook
        ebook = await self.ebook_repository.get_by_id(ebook_id)
        ebook = KdpExportValidator.validate_for_export(ebook, ebook_id, preview_mode, export_type="KDP")

        logger.info(f"Exporting ebook {ebook_id} to KDP format: '{ebook.title}' ({ebook.page_count} pages)")

        # 2. Adjust KDP config for short books if needed
        kdp_config = KdpExportValidator.adjust_config_for_short_books(ebook, kdp_config)

        # 3. Initialize providers if not injected
        if not self.image_provider:
            from backoffice.features.ebook.shared.infrastructure.providers.images.openrouter import (
                openrouter_image_provider as or_provider,
            )

            self.image_provider = or_provider.OpenRouterImageProvider()

        if not self.kdp_assembly_provider:
            from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.assembly import (
                cover_assembly_provider as kdp_provider,
            )

            self.kdp_assembly_provider = kdp_provider.KDPAssemblyProvider()

        # 4. Get front cover bytes (WITH text - for assembly)
        front_cover_bytes = await self._get_front_cover_bytes(ebook)

        # 5. Get back cover bytes (already generated in coloring_book_strategy)
        logger.info("Extracting existing back cover from ebook structure...")
        back_cover_bytes = await self._get_back_cover_bytes(ebook)

        # 5b. Extract ISBN from theme config (if available)
        isbn = self._get_isbn_from_theme(ebook.theme_id)

        # 5c retrieve spine colors from theme config
        spine_colors = self._get_spine_colors_from_theme(ebook.theme_id)

        if not spine_colors:
            spine_colors = ["#FFFFFF", "#000000"]

        # 6. Assemble KDP PDF (back + spine + front)
        logger.info("Assembling KDP paperback PDF...")
        assert self.kdp_assembly_provider is not None  # guaranteed by lazy init above
        kdp_pdf_bytes = await self.kdp_assembly_provider.assemble_kdp_paperback(
            ebook=ebook, back_cover_bytes=back_cover_bytes, front_cover_bytes=front_cover_bytes, kdp_config=kdp_config, isbn=isbn, spine_colors=spine_colors
        )

        logger.info(f"✅ KDP export completed: {len(kdp_pdf_bytes)} bytes")

        # 7. Visual validation against KDP template
        if ebook.page_count is None:  # pragma: no cover — guaranteed by validator
            raise DomainError(code=ErrorCode.VALIDATION_ERROR, message="Ebook has no page count", actionable_hint="Regenerate the ebook first")
        await self._validate_cover_against_template(
            back_cover_bytes=back_cover_bytes,
            front_cover_bytes=front_cover_bytes,
            page_count=ebook.page_count,
        )

        # 8. Emit domain event
        await self.event_bus.publish(
            KDPExportGeneratedEvent(
                ebook_id=ebook_id,
                title=ebook.title or "Untitled",
                file_size_bytes=len(kdp_pdf_bytes),
                preview_mode=preview_mode,
                status=ebook.status.value,
            )
        )

        return kdp_pdf_bytes

    def _get_isbn_from_theme(self, theme_id: str | None) -> str | None:
        """Extract ISBN from the theme configuration.

        Args:
            theme_id: Theme identifier, or None if no theme is set

        Returns:
            ISBN-13 string (digits only) if found, None otherwise
        """
        try:
            theme_profile = self._get_theme_profile(theme_id)
            if theme_profile and theme_profile.back_cover and theme_profile.back_cover.isbn:
                isbn = theme_profile.back_cover.isbn
                logger.info(f"ISBN found in theme '{theme_id}': {isbn}")
                return isbn
        except Exception as e:
            logger.warning(f"Could not load theme for ISBN: {e}")

        return None

    def _get_spine_colors_from_theme(self, theme_id: str | None) -> list | None:
        """Extract Spine color from the theme configuration. it is based on the
        theme palette (the last 2 ones : spine background color and spine text color).

        Args:
            theme_id: Theme identifier, or None if no theme is set

        Returns:
            Spine colors tuple: first one is spine background color and
            second one is spine text color, None otherwise
        """
        try:
            theme_profile = self._get_theme_profile(theme_id)
            if theme_profile and theme_profile.palette and theme_profile.palette.base and len(theme_profile.palette.base) >= 2:
                spine_colors = theme_profile.palette.base[-2:]
                logger.info(f"Spine colors found in theme '{theme_id}': {spine_colors}")
                return spine_colors
        except Exception as e:
            logger.warning(f"Could not load theme for spine colors: {e}")

        return None

    def _get_theme_profile(self, theme_id: str | None) -> ThemeProfile | None:
        if not theme_id:
            return None

        try:
            if not self.theme_repository:
                from backoffice.features.ebook.shared.infrastructure.adapters.theme_repository import (
                    ThemeRepository as _ThemeRepository,
                )

                self.theme_repository = _ThemeRepository()

            theme_profile = self.theme_repository.get_theme_by_id(theme_id)

            if theme_profile:
                return theme_profile
        except Exception as e:
            logger.warning(f"Could not load theme : {e}")

        return None

    async def _get_front_cover_bytes(self, ebook: Ebook) -> bytes:
        """Extract front cover from ebook structure or bytes."""
        # For now, get the first page from structure_json
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook structure missing pages metadata",
                actionable_hint="Regenerate the ebook",
            )

        pages = ebook.structure_json.get("pages_meta", [])
        if not pages:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="No pages found in ebook structure",
                actionable_hint="Regenerate the ebook",
            )

        # First page is the cover
        cover_page = pages[0]
        import base64

        cover_bytes = base64.b64decode(cover_page["image_data_base64"])
        return cover_bytes

    async def _get_back_cover_bytes(self, ebook: Ebook) -> bytes:
        """Extract back cover from ebook structure (last page).

        The back cover is already generated in coloring_book_strategy.py
        as the last page of the ebook.
        """
        if not ebook.structure_json or "pages_meta" not in ebook.structure_json:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook structure missing pages metadata",
                actionable_hint="Regenerate the ebook",
            )

        pages = ebook.structure_json.get("pages_meta", [])
        if len(pages) < 2:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Ebook must have at least 2 pages (cover + back cover)",
                actionable_hint="Regenerate the ebook",
            )

        # Last page is the back cover
        back_cover_page = pages[-1]
        import base64

        back_cover_bytes = base64.b64decode(back_cover_page["image_data_base64"])
        logger.info(f"✅ Extracted back cover from ebook structure: {len(back_cover_bytes)} bytes")
        return back_cover_bytes

    async def _validate_cover_against_template(
        self,
        back_cover_bytes: bytes,
        front_cover_bytes: bytes,
        page_count: int,
    ) -> None:
        """Validate assembled full cover against official KDP template.

        This validation is informational only (logs warnings, doesn't fail export).

        Args:
            back_cover_bytes: Back cover image bytes
            front_cover_bytes: Front cover image bytes
            page_count: Number of pages for spine calculation
        """
        try:
            from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.visual_validator import (
                assemble_full_kdp_cover,
                validate_full_cover_against_template,
            )

            logger.info("🔍 Validating KDP cover against official template...")

            # Assemble full cover (same logic as KDPAssemblyProvider but in PNG)
            full_cover_bytes = assemble_full_kdp_cover(
                back_cover_bytes=back_cover_bytes,
                front_cover_bytes=front_cover_bytes,
                page_count=page_count,
            )

            # Validate against template
            validation_result = validate_full_cover_against_template(full_cover_bytes)

            if validation_result.get("valid"):
                logger.info(f"✅ {validation_result['message']}")
            else:
                logger.warning(f"⚠️ {validation_result['message']}")
                logger.warning(f"   Cover size: {validation_result.get('cover_size')} vs expected: {validation_result.get('expected_size')}")

        except Exception as e:
            # Don't fail export if validation fails - just log warning
            logger.warning(f"⚠️ KDP template validation failed (non-critical): {str(e)}")
