"""OpenRouter response image extractor - handles multiple response formats."""

import asyncio
import base64
import logging

import httpx

from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class OpenRouterResponseExtractor:
    """Extracts image bytes from OpenRouter API responses.

    Handles multiple response formats from different models:
    - Gemini 2.5 Flash Image (images array)
    - Direct content string (base64 or URL)
    - Response metadata (data array)
    """

    def __init__(self, model: str):
        """Initialize extractor.

        Args:
            model: Model name for error context
        """
        self.model = model

    def extract_image_from_response(self, response) -> bytes:
        """Extract image bytes from OpenRouter response.

        Tries multiple extraction strategies in order:
        1. images array in message (Gemini 2.5 format)
        2. Direct content parsing (string with base64 or URL)
        3. Response metadata (data array)

        Args:
            response: OpenRouter API response

        Returns:
            Image bytes

        Raises:
            DomainError: If image extraction fails with all strategies
        """
        # Try multiple extraction strategies
        try:
            message = response.choices[0].message

            # Strategy 0: Check for images array in message (Gemini 2.5 format)
            image_bytes = self._extract_from_images_array(message)
            if image_bytes:
                return image_bytes

            # Strategy 1: Direct content parsing (for other models)
            image_bytes = self._extract_from_content_string(message)
            if image_bytes:
                return image_bytes

            # Strategy 2: Check for image data in response metadata
            image_bytes = self._extract_from_metadata(response)
            if image_bytes:
                return image_bytes

        except Exception as e:
            logger.error(f"Failed to extract image: {str(e)}")

        # If all strategies fail
        raise DomainError(
            code=ErrorCode.PROVIDER_TIMEOUT,
            message=f"Failed to extract image from {self.model} response",
            actionable_hint="Model might not support image generation or response format changed",
            context={
                "provider": "openrouter",
                "model": self.model,
                "response_type": type(response).__name__,
            },
        )

    def _extract_from_images_array(self, message) -> bytes | None:
        """Extract image from images array (Gemini 2.5 format).

        Args:
            message: Message object from response

        Returns:
            Image bytes or None if not found
        """
        if not hasattr(message, "images") or not message.images:
            return None

        logger.info("📸 Found images array in message (Gemini format)")
        first_image = message.images[0]

        # Extract from image_url.url
        if isinstance(first_image, dict) and "image_url" in first_image:
            image_url = first_image["image_url"]["url"]

            # Check if it's base64 data URL
            if "base64," in image_url:
                logger.info("Extracting base64 image from images array...")
                base64_data = image_url.split("base64,", 1)[1]
                return base64.b64decode(base64_data)

            # Check if it's HTTP URL
            if image_url.startswith("http"):
                logger.info("Downloading image from images array URL...")
                return self._download_image_sync(image_url)

        return None

    def _extract_from_content_string(self, message) -> bytes | None:
        """Extract image from content string (base64 or URL).

        Args:
            message: Message object from response

        Returns:
            Image bytes or None if not found
        """
        content = message.content

        if not isinstance(content, str):
            return None

        # Look for base64 image data
        if "base64," in content:
            # Extract base64 data after comma
            base64_data = content.split("base64,", 1)[1].split('"')[0]
            return base64.b64decode(base64_data)

        # Look for image URL
        if content.startswith("http"):
            logger.info("Downloading image from URL...")
            return self._download_image_sync(content)

        return None

    def _extract_from_metadata(self, response) -> bytes | None:
        """Extract image from response metadata (data array).

        Args:
            response: Full API response

        Returns:
            Image bytes or None if not found
        """
        if not hasattr(response, "data") or not response.data:
            return None

        for item in response.data:
            if hasattr(item, "b64_json"):
                return base64.b64decode(item.b64_json)
            if hasattr(item, "url"):
                logger.info("Downloading from data URL...")
                return self._download_image_sync(item.url)

        return None

    def _download_image_sync(self, url: str) -> bytes:
        """Download image from URL synchronously.

        Args:
            url: Image URL to download

        Returns:
            Image bytes
        """

        async def download():
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content

        result: bytes = asyncio.run(download())
        return result
