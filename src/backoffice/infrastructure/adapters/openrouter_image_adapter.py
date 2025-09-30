"""OpenRouter image generation adapter implementing ImageGenerationPort."""

import base64
import logging
from io import BytesIO

import httpx
from PIL import Image

from backoffice.domain.constants import (
    CONTENT_MIN_PIXELS_SQUARE,
    COVER_MIN_PIXELS_SQUARE,
    PageFormat,
)
from backoffice.domain.ports.image_generation_port import ImageGenerationPort

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    pass


class OpenRouterImageAdapter(ImageGenerationPort):
    """OpenRouter image generation adapter using Gemini 2.5 Flash Image Preview.

    ⚠️  IMPORTANT: Only Gemini 2.5 Flash Image Preview supports image generation via OpenRouter.

    Supported via OpenRouter:
    - google/gemini-2.5-flash-image-preview (with modalities: ["image", "text"])

    Other models require direct API access:
    - DALL-E 3: Use OpenAI API directly (api.openai.com)
    - FLUX: Use Together AI or Replicate API directly
    - Stable Diffusion: Use Stability AI API directly
    """

    def __init__(self, model: str | None = None):
        """Initialize adapter.

        Args:
            model: Specific image model to use (e.g., "openai/dall-e-3")
                   If None, will use LLM_IMAGE_MODEL from environment
        """
        import os

        self.api_key = os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_IMAGE_MODEL", "openai/dall-e-3")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        # For now, we'll use OpenAI client since OpenRouter is compatible
        # but note that image generation through OpenRouter is limited
        if self.api_key:
            from openai import AsyncOpenAI

            # Note: Image generation through OpenRouter is experimental
            # For production, consider using model-specific APIs
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"OpenRouterImageAdapter initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning("LLM_API_KEY not found, image generation will use fallbacks")

    def is_available(self) -> bool:
        """Check if OpenRouter service is available"""
        return self.client is not None

    async def generate_image_from_url(self, image_url: str, prompt: str | None = None) -> bytes:
        """Generate an image based on a URL (converted to coloring book style)

        For coloring book pages, we first download the image then convert it to a line art style
        """
        if not self.is_available():
            raise ValueError(
                "Configuration incomplète: la clé API LLM_API_KEY est manquante. "
                "Veuillez ajouter votre clé API dans le fichier .env"
            )

        try:
            logger.info(f"Processing image from URL: {image_url}")

            # Download the original image (for future use)
            async with httpx.AsyncClient() as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; OpenRouter-Image-Downloader/1.0)"
                }
                response = await client.get(image_url, headers=headers, follow_redirects=True)
                response.raise_for_status()

            # Create a descriptive prompt for coloring book style image
            fallback_prompt = (
                f"Create a simple black and white coloring book page with thick black outlines "
                f"and white fill areas. Simple design suitable for children to color. "
                f"{prompt or ''}"
            )

            return await self.generate_image_from_prompt(fallback_prompt, "1024x1024")

        except ValueError:
            # Re-raise configuration errors
            raise
        except Exception as e:
            logger.error(f"Error processing image from URL: {str(e)}")
            raise ImageGenerationError(
                f"Échec du traitement de l'image depuis l'URL: {str(e)}"
            ) from e

    async def generate_image_from_prompt(
        self,
        prompt: str,
        size: str = "1024x1024",
        is_cover: bool = False,
        page_format: PageFormat = PageFormat.A4,
    ) -> bytes:
        """Generate an image from a text prompt using Gemini via OpenRouter"""
        if not self.is_available():
            raise ValueError(
                "Configuration incomplète: la clé API LLM_API_KEY est manquante. "
                "Veuillez ajouter votre clé API dans le fichier .env"
            )

        try:
            # Determine optimal size based on usage and format
            if page_format == PageFormat.SQUARE_8_5:
                if is_cover:
                    quality = "hd"
                    target_pixels = COVER_MIN_PIXELS_SQUARE
                    target_info = f"cover (target: {target_pixels}x{target_pixels})"
                else:
                    quality = "standard"
                    target_pixels = CONTENT_MIN_PIXELS_SQUARE
                    target_info = f"content (target: {target_pixels}x{target_pixels})"
            else:
                # A4 or other formats
                quality = "standard"
                target_info = "A4 format"

            logger.info(
                f"Generating {quality} quality image for {target_info} "
                f"using model {self.model} from prompt: {prompt[:100]}..."
            )

            # Only Gemini 2.5 Flash Image Preview supports image generation via OpenRouter
            if "gemini" in self.model.lower() and "image" in self.model.lower():
                return await self._generate_via_chat_endpoint(prompt, size, quality)
            else:
                raise ImageGenerationError(
                    f"Le modèle {self.model} n'est pas supporté pour la génération "
                    "d'images via OpenRouter.\n\n"
                    "Seul google/gemini-2.5-flash-image-preview est supporté.\n\n"
                    "Pour utiliser d'autres modèles:\n"
                    "  • DALL-E 3: Configurez OPENAI_API_KEY\n"
                    "  • FLUX: Utilisez Together AI ou Replicate\n\n"
                    "Ou changez LLM_IMAGE_MODEL=google/gemini-2.5-flash-image-preview"
                )

        except ImageGenerationError:
            # Re-raise our own errors
            raise
        except ValueError:
            # Re-raise configuration errors
            raise
        except Exception as e:
            logger.error(f"Error generating image with OpenRouter: {str(e)}")
            raise ImageGenerationError(
                f"Erreur inattendue lors de la génération d'image: {str(e)}"
            ) from e

    async def _generate_via_chat_endpoint(self, prompt: str, size: str, quality: str) -> bytes:
        """Generate image via chat/completions endpoint with modalities (for Gemini image models)"""
        try:
            # Gemini 2.5 Flash Image Preview requires modalities: ["image", "text"]
            # This tells the model to generate images in its response
            logger.info("Requesting image generation with modalities=['image', 'text']")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                extra_body={
                    "modalities": ["image", "text"]  # KEY: This enables image generation
                },
                extra_headers={
                    "HTTP-Referer": "https://ebook-generator.app",
                    "X-Title": "Ebook Generator Backoffice",
                },
            )

            # Extract images from response
            # Gemini returns images in message.images array
            message = response.choices[0].message

            # Debug logging
            logger.info(f"Response message type: {type(message)}")
            logger.info(f"Message attributes: {dir(message)}")

            # Check for images in message
            if hasattr(message, "images") and message.images:
                logger.info(f"Found {len(message.images)} images in response")

                # Get the first image
                first_image = message.images[0]
                logger.info(f"Image structure: {type(first_image)}")

                # Extract image URL (should be base64 data URL)
                if hasattr(first_image, "image_url"):
                    # The image_url is an ImageURL object with a .url attribute
                    image_url_obj = first_image.image_url

                    # Get URL from the ImageURL object
                    if hasattr(image_url_obj, "url"):
                        image_url = image_url_obj.url
                    elif isinstance(image_url_obj, dict):
                        image_url = image_url_obj.get("url")
                    else:
                        image_url = str(image_url_obj)

                    logger.info(f"Image URL prefix: {image_url[:100] if image_url else 'None'}")

                    # Parse base64 data URL
                    if image_url and image_url.startswith("data:image"):
                        import re

                        match = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", image_url)
                        if match:
                            image_b64 = match.group(1)
                            image_data = base64.b64decode(image_b64)
                            logger.info(f"Successfully extracted image ({len(image_data)} bytes)")
                            return image_data
                        else:
                            logger.error(f"Could not parse base64 from URL: {image_url[:200]}")
                    else:
                        url_preview = image_url[:100] if image_url else "None"
                        logger.error(f"Image URL doesn't start with 'data:image': {url_preview}")

            # Fallback: try to get from content as before
            content = message.content
            if isinstance(content, str) and "data:image" in content:
                import re

                match = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", content)
                if match:
                    image_b64 = match.group(1)
                    image_data = base64.b64decode(image_b64)
                    logger.info(
                        f"Successfully extracted image from content ({len(image_data)} bytes)"
                    )
                    return image_data

            # If no image found, log full response and raise error
            logger.error("No image data found in Gemini response")
            logger.error(f"Full response: {response}")
            raise ImageGenerationError(
                f"Le modèle {self.model} n'a pas retourné d'image valide.\n"
                "La réponse ne contient pas de données d'image.\n\n"
                "Vérifiez que vous avez des crédits sur votre compte OpenRouter."
            )

        except ImageGenerationError:
            raise
        except Exception as e:
            logger.error(f"Error calling Gemini image API: {str(e)}")
            error_msg = str(e)

            # Check for specific errors
            if (
                "402" in error_msg
                or "insufficient" in error_msg.lower()
                or "credits" in error_msg.lower()
            ):
                raise ImageGenerationError(
                    "Crédits insuffisants sur votre compte OpenRouter. "
                    "Veuillez ajouter des crédits sur https://openrouter.ai/settings/credits"
                ) from e
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise ImageGenerationError(
                    "Clé API invalide. Veuillez vérifier votre LLM_API_KEY dans le fichier .env"
                ) from e
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                raise ImageGenerationError(
                    "Limite de requêtes atteinte. Veuillez réessayer dans quelques instants."
                ) from e
            else:
                raise ImageGenerationError(
                    f"Erreur lors de la génération d'image avec {self.model}: {error_msg}"
                ) from e

    def _upscale_image_for_print(
        self, image_data: bytes, is_cover: bool = False, page_format: PageFormat = PageFormat.A4
    ) -> bytes:
        """Upscale image to meet print quality requirements"""
        try:
            # Determine target size
            if page_format == PageFormat.SQUARE_8_5:
                if is_cover:
                    target_size = (COVER_MIN_PIXELS_SQUARE, COVER_MIN_PIXELS_SQUARE)
                else:
                    target_size = (CONTENT_MIN_PIXELS_SQUARE, CONTENT_MIN_PIXELS_SQUARE)
            else:
                return image_data

            # Load image
            img = Image.open(BytesIO(image_data))
            original_size = img.size

            # Check if upscaling is needed
            if img.width >= target_size[0] and img.height >= target_size[1]:
                logger.info(f"Image already meets size requirements: {original_size}")
                return image_data

            # Upscale using high-quality resampling
            logger.info(f"Upscaling image from {original_size} to {target_size}")
            upscaled_img = img.resize(target_size, Image.Resampling.LANCZOS)

            # Save upscaled image
            output = BytesIO()
            upscaled_img.save(output, format="PNG", optimize=True)
            upscaled_data = output.getvalue()

            logger.info(
                f"Image upscaled: {len(image_data)} -> {len(upscaled_data)} bytes "
                f"({original_size} -> {target_size})"
            )

            return upscaled_data

        except Exception as e:
            logger.error(f"Error upscaling image: {e}, using original")
            return image_data

    async def generate_coloring_page_from_description(
        self, description: str, is_cover: bool = False
    ) -> bytes:
        """Generate a coloring page or colorful cover image designed for children"""
        if is_cover:
            # Colorful cover with vibrant colors
            prompt = (
                f"Create a vibrant, colorful book cover illustration for children. "
                f"Bright colors, playful style, engaging and attractive. "
                f"Content: {description}"
            )
        else:
            # Black and white coloring page
            prompt = (
                f"Create a simple black and white coloring book page with thick black "
                f"outlines and white fill areas. Clean lines, simple shapes, perfect "
                f"for children aged 4-8 to color. Content: {description}"
            )

        return await self.generate_image_from_prompt(
            prompt, size="1024x1024", is_cover=is_cover, page_format=PageFormat.SQUARE_8_5
        )
