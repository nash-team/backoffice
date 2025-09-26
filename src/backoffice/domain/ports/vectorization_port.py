from abc import ABC, abstractmethod


class VectorizationPort(ABC):
    """Port for image vectorization services"""

    @abstractmethod
    async def vectorize_image(self, image_data: bytes) -> str:
        """Convert raster image to SVG vector format

        Args:
            image_data: PNG/JPEG image data as bytes

        Returns:
            str: SVG content as string

        Raises:
            VectorizationError: If vectorization fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the vectorization service is available

        Returns:
            bool: True if service can be used for vectorization
        """
        pass

    @abstractmethod
    async def optimize_for_coloring(self, svg_content: str) -> str:
        """Optimize SVG for coloring book use (clean lines, proper fill areas)

        Args:
            svg_content: Original SVG content

        Returns:
            str: Optimized SVG content for coloring

        Raises:
            VectorizationError: If optimization fails
        """
        pass
