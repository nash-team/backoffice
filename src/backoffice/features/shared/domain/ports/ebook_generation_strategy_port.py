"""Strategy port for ebook generation algorithms."""

from abc import ABC, abstractmethod

from backoffice.features.shared.domain.entities.generation_request import (
    GenerationRequest,
    GenerationResult,
)


class EbookGenerationStrategyPort(ABC):
    """Port defining the strategy interface for ebook generation.

    Each ebook type (coloring, story, activity, etc.) implements this strategy
    to provide its specific generation algorithm.
    """

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate an ebook based on the request.

        Args:
            request: Generation request with all parameters

        Returns:
            GenerationResult with PDF URI and metadata

        Raises:
            DomainError: If generation fails
        """
        pass
