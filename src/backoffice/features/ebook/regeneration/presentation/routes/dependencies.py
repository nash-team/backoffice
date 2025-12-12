"""Shared dependencies for regeneration routes."""

import logging

from backoffice.features.ebook.regeneration.domain.services.regeneration_service import (
    RegenerationService,
)
from backoffice.features.ebook.shared.domain.services.cover_generation import CoverGenerationService
from backoffice.features.ebook.shared.domain.services.page_generation import (
    ContentPageGenerationService,
)
from backoffice.features.ebook.shared.domain.services.pdf_assembly import PDFAssemblyService
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
)
from backoffice.features.ebook.shared.infrastructure.providers.provider_factory import (
    ProviderFactory,
)
from backoffice.features.ebook.shared.infrastructure.providers.weasyprint_assembly_provider import (
    WeasyPrintAssemblyProvider,
)

logger = logging.getLogger(__name__)


def create_regeneration_service(factory: RepositoryFactory) -> RegenerationService:
    """Create RegenerationService with all dependencies.

    This factory is shared across all regeneration routes to avoid
    code duplication when instantiating services.

    Args:
        factory: Repository factory for file storage access

    Returns:
        Configured RegenerationService instance
    """
    assembly_provider = WeasyPrintAssemblyProvider()
    assembly_service = PDFAssemblyService(assembly_port=assembly_provider)
    return RegenerationService(
        assembly_service=assembly_service,
        file_storage=factory.get_file_storage(),
    )


def create_cover_service() -> CoverGenerationService:
    """Create CoverGenerationService with provider.

    Returns:
        Configured CoverGenerationService instance
    """
    cover_provider = ProviderFactory.create_cover_provider()
    return CoverGenerationService(cover_port=cover_provider)


def create_page_service() -> ContentPageGenerationService:
    """Create ContentPageGenerationService with provider.

    Returns:
        Configured ContentPageGenerationService instance
    """
    page_provider = ProviderFactory.create_content_page_provider()
    return ContentPageGenerationService(page_port=page_provider)
