from abc import ABC, abstractmethod


class ContentGenerationPort(ABC):
    """Port for AI-based ebook content generation"""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the content generation service is available

        Returns:
            bool: True if service can be used for generation
        """
        pass
