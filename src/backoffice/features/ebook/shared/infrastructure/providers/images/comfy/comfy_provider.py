"""Local Stable Diffusion provider (100% FREE, runs locally, no API token needed)."""

import logging
import os
import uuid
import json
import urllib.request
import urllib.parse
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
import websocket

from PIL import Image, ImageDraw

from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.domain.value_objects.usage_metrics import UsageMetrics
from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class ComfyProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Local Stable Diffusion provider using Comfy (100% FREE, no API).

    Supports both:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    """

    # Cost: FREE (runs locally)
    COST_PER_IMAGE = Decimal("0")  # Gratuit!

    def __init__(
        self,
        model: str | None = None,
        comfy_url: str | None = "127.0.0.1:8188"
    ):
        """Initialize Local Comfy provider."""

        self.client_id = str(uuid.uuid4())
        self.use_cpu = False
        self.hf_token = None
        self.pipeline = None
        self.controlnet = None
        self._model_loaded = False
        self.comfy_url = comfy_url
        self.model = model
        self.workflow = None

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req =  urllib.request.Request("http://{}/prompt".format(self.comfy_url), data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen("http://{}/view?{}".format(self.comfy_url, url_values)) as response:
            return response.read()

    def get_history(self, prompt_id):
        with urllib.request.urlopen("http://{}/history/{}".format(self.comfy_url, prompt_id)) as response:
            return json.loads(response.read())

    def get_images(self, ws, prompt):
        prompt_id = self.queue_prompt(prompt)['prompt_id']
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break #Execution is done
            else:
                continue #previews are binary data

        history = self.get_history(prompt_id)[prompt_id]
        for _ in history['outputs']:
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                images_output = []

                if 'images' in node_output:
                    for image in node_output['images']:
                        image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                output_images[node_id] = images_output

        return output_images

    def is_available(self) -> bool:
        """Check if provider is available."""
        req =  urllib.request.Request("http://{}".format(self.comfy_url), method="GET")
        ping: bool = False
        try:
            urllib.request.urlopen(req).read()
            ping = True
        except URLError as e:
            pass

        return ping

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - Local SD generates raster images (PNG)
        """
        return False

    def _retrieve_workflow(self, cover: bool):
        # Find project root by looking for config/ directory

        current = Path(__file__).resolve()
        while current.parent != current:
            config_dir = current / "config"
            if config_dir.exists() and (config_dir / "generation").exists():
                config_path = config_dir / "generation" / "comfy" / f"{self.model}"

                with open(config_path, "r", encoding="utf-8") as f:
                    workflow_data = f.read()

                self.workflow = json.loads(workflow_data)
                break
            current = current.parent
        else:
            raise FileNotFoundError(
                f"Could not find config/generation/{self.model}.json in project tree"
            )

    def _load_workflow(self, spec: ImageSpec, cover: bool):
        color = spec.color_mode

        self._retrieve_workflow(cover)

        if cover:
            workflow_file = self.model
            pass
        else:
            pass

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a colorful cover image.

        Args:
            prompt: Text description of the cover
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility

        Returns:
            Cover image as bytes

        Raises:
            DomainError: If generation fails
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Comfy provider not available",
                actionable_hint="Run comfy",
                context={"provider": "comfy", "model": self.model},
            )

        self._load_workflow(spec, True)
        self.workflow["31"]["inputs"]["seed"] = seed

        # Build prompt based on color mode
        # if spec.color_mode == ColorMode.BLACK_WHITE:
        #     # B&W coloring page style
        #     # Add ColoringBook LoRA trigger tags if using ColoringBook.Redmond
        #     lora_prefix = ""
        #     if self.lora_id and "ColoringBook" in self.lora_id:
        #         lora_prefix = "ColoringBookAF, Coloring Book, "
        #         logger.info("🎨 Using ColoringBook LoRA trigger tags")
        #
        #     # Clean prompt: remove redundant text from PromptTemplateEngine to save tokens
        #     clean_prompt = prompt.replace("Line art coloring page of a ", "")
        #     clean_prompt = clean_prompt.split("Bold clean outlines")[
        #         0
        #     ].strip()  # Remove quality_settings
        #
        #     full_prompt = (
        #         f"{lora_prefix}"
        #         f"cute simple cartoon style for young kids, "
        #         f"{clean_prompt}, "
        #         f"thick outlines, simple shapes"
        #     )
        # else:
        #     # Colorful cover style
        #     full_prompt = (
        #         f"Create a vibrant, colorful cover illustration perfect for a children's book. "
        #         f"IMPORTANT: The illustration must fill the ENTIRE frame edge-to-edge "
        #         f"with NO white margins or borders. "
        #         f"Full-bleed design - the main subject should extend to all edges of the image. "
        #         f"Rich colors, engaging composition. "
        #         f"Content: {prompt}"
        #     )

        # logger.info(f"Generating cover via Comfy UI workflow: {full_prompt[:100]}...")

        try:
            ws = websocket.WebSocket()
            ws.connect("ws://{}/ws?clientId={}".format(self.comfy_url, self.client_id))
            images = self.get_images(ws, self.workflow)

            result_bytes = None

            for node_id in images:
                for image_data in images[node_id]:
                    from PIL import Image
                    import io
                    # buffer = BytesIO()
                    result_bytes = image_data
                    # save image
                    image = Image.open(io.BytesIO(image_data))
                    image.save(f"/tmp/test-{node_id}-{seed}.png")

            # pil_image = result.images[0]

            # Convert to bytes
            # pil_image.save(buffer, format="PNG")
            # result_bytes = buffer.getvalue()
            #
            # # Add rounded border for B&W coloring pages
            # if spec.color_mode == ColorMode.BLACK_WHITE:
            #     logger.info("Adding rounded black border to coloring page...")
            #     result_bytes = self._add_rounded_border_to_image(result_bytes)
            #
            # logger.info(f"✅ Generated cover (LOCAL): {len(result_bytes)} bytes")
            return result_bytes

        except Exception as e:
            logger.error(f"❌ Local SD generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Local SD generation failed: {str(e)}",
                actionable_hint="Check system resources (RAM/GPU memory) and model availability",
                context={"provider": "local_sd", "model": self.model, "error": str(e)},
            ) from e

    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a content page (delegates to generate_cover with same logic).

        Args:
            prompt: Text description of the page
            spec: ImageSpec specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility

        Returns:
            Page image as bytes

        Raises:
            DomainError: If generation fails
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Comfy provider not available",
                actionable_hint="Run comfy",
                context={"provider": "comfy", "model": self.model},
            )

        self._load_workflow(spec, False)
        self.workflow["31"]["inputs"]["seed"] = seed

        # Build prompt based on color mode
        # if spec.color_mode == ColorMode.BLACK_WHITE:
        #     # B&W coloring page style
        #     # Add ColoringBook LoRA trigger tags if using ColoringBook.Redmond
        #     lora_prefix = ""
        #     if self.lora_id and "ColoringBook" in self.lora_id:
        #         lora_prefix = "ColoringBookAF, Coloring Book, "
        #         logger.info("🎨 Using ColoringBook LoRA trigger tags")
        #
        #     # Clean prompt: remove redundant text from PromptTemplateEngine to save tokens
        #     clean_prompt = prompt.replace("Line art coloring page of a ", "")
        #     clean_prompt = clean_prompt.split("Bold clean outlines")[
        #         0
        #     ].strip()  # Remove quality_settings
        #
        #     full_prompt = (
        #         f"{lora_prefix}"
        #         f"cute simple cartoon style for young kids, "
        #         f"{clean_prompt}, "
        #         f"thick outlines, simple shapes"
        #     )
        # else:
        #     # Colorful cover style
        #     full_prompt = (
        #         f"Create a vibrant, colorful cover illustration perfect for a children's book. "
        #         f"IMPORTANT: The illustration must fill the ENTIRE frame edge-to-edge "
        #         f"with NO white margins or borders. "
        #         f"Full-bleed design - the main subject should extend to all edges of the image. "
        #         f"Rich colors, engaging composition. "
        #         f"Content: {prompt}"
        #     )

        # logger.info(f"Generating cover via Comfy UI workflow: {full_prompt[:100]}...")

        try:
            ws = websocket.WebSocket()
            ws.connect("ws://{}/ws?clientId={}".format(self.comfy_url, self.client_id))
            images = self.get_images(ws, self.workflow)

            result_bytes = None

            for node_id in images:
                for image_data in images[node_id]:
                    from PIL import Image
                    import io
                    # buffer = BytesIO()
                    result_bytes = image_data
                    # save image
                    image = Image.open(io.BytesIO(image_data))
                    image.save(f"/tmp/test-{node_id}-{seed}.png")

            # pil_image = result.images[0]

            # Convert to bytes
            # pil_image.save(buffer, format="PNG")
            # result_bytes = buffer.getvalue()
            #
            # # Add rounded border for B&W coloring pages
            # if spec.color_mode == ColorMode.BLACK_WHITE:
            #     logger.info("Adding rounded black border to coloring page...")
            #     result_bytes = self._add_rounded_border_to_image(result_bytes)
            #
            # logger.info(f"✅ Generated cover (LOCAL): {len(result_bytes)} bytes")
            return result_bytes

        except Exception as e:
            logger.error(f"❌ Local SD generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Local SD generation failed: {str(e)}",
                actionable_hint="Check system resources (RAM/GPU memory) and model availability",
                context={"provider": "local_sd", "model": self.model, "error": str(e)},
            ) from e

    async def remove_text_from_cover(
            self,
            cover_bytes: bytes,
            barcode_width_inches: float = 2.0,
            barcode_height_inches: float = 1.5,
            barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover to create back cover.

        For Gemini, we just return the cover without text.
        The barcode space will be added later during KDP export assembly, not here.

        Args:
            cover_bytes: Original cover image (with text)
            barcode_width_inches: Unused (kept for interface compatibility)
            barcode_height_inches: Unused (kept for interface compatibility)
            barcode_margin_inches: Unused (kept for interface compatibility)

        Returns:
            Same image without text (barcode space will be added during KDP export)

        Raises:
            DomainError: If transformation fails
        """
        logger.info("🗑️  Removing text from cover (Gemini: returning cover as-is)...")

        # Just return the cover - barcode space will be added during KDP export
        # not during back cover generation
        logger.info(f"✅ Back cover ready (no barcode space): {len(cover_bytes)} bytes")
        return cover_bytes

    def _add_rounded_border_to_image(
        self,
        image_bytes: bytes,
        border_width: int = 5,
        corner_radius: int = 20,
        margin: int = 50,
    ) -> bytes:
        """Add a rounded black border to the image with white margin.

        Args:
            image_bytes: Original image bytes
            border_width: Width of the border in pixels (default: 5px)
            corner_radius: Radius for rounded corners in pixels (default: 20px)
            margin: White space between content and border in pixels (default: 50px)

        Returns:
            Image bytes with border and margin added
        """

        # Load image
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        orig_width, orig_height = img.size

        # Skip if image too small
        if orig_width < 100 or orig_height < 100:
            logger.warning(f"Image too small ({orig_width}x{orig_height}) for border, skipping")
            return image_bytes

        # Calculate new dimensions with margin
        total_padding = margin * 2
        new_width = orig_width
        new_height = orig_height

        # Create white background with padding
        bordered_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))

        # Shrink original image to leave margin
        content_width = new_width - total_padding
        content_height = new_height - total_padding
        img_resized = img.resize((content_width, content_height), Image.Resampling.LANCZOS)

        # Paste resized image centered with margin
        bordered_img.paste(img_resized, (margin, margin))

        # Draw the black rounded rectangle border
        draw = ImageDraw.Draw(bordered_img)
        draw.rounded_rectangle(
            (
                margin - border_width // 2,
                margin - border_width // 2,
                new_width - margin + border_width // 2 - 1,
                new_height - margin + border_width // 2 - 1,
            ),
            radius=corner_radius,
            outline=(0, 0, 0),
            width=border_width,
        )

        # Save and return
        buffer = BytesIO()
        bordered_img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _preprocess_for_controlnet(self, spec: ImageSpec) -> Image.Image | None:
        """Preprocess image for ControlNet Canny edge detection.

        Creates a white canvas with edge map that ControlNet will use
        as guidance for generating clean line art.

        Args:
            spec: Image specifications (dimensions)

        Returns:
            PIL Image for ControlNet control_image, or None if no ControlNet
        """
        if not self.controlnet_id:
            return None

        logger.info("🎨 Preprocessing for ControlNet Canny...")

        try:
            from controlnet_aux import CannyDetector

            # Create simple white canvas (ControlNet will guide the generation)
            # For text2img with ControlNet, we create a blank canvas
            # The model will use this as structure guidance
            control_image = Image.new("RGB", (spec.width_px, spec.height_px), (255, 255, 255))

            # Initialize Canny edge detector
            processor = CannyDetector()

            # Process image to extract edge structure
            # For blank canvas, this creates a minimal edge map
            processed_image = processor(control_image, low_threshold=50, high_threshold=100)

            logger.info("✅ ControlNet preprocessing complete")
            # processor returns PIL Image, just ensure type safety
            return processed_image if isinstance(processed_image, Image.Image) else None

        except Exception as e:
            logger.warning(f"⚠️  ControlNet preprocessing failed: {str(e)}, continuing without it")
            return None

    def _create_usage_metrics(self, model: str, num_images: int = 1) -> UsageMetrics:
        """Create usage metrics for Local SD response.

        Local SD is FREE (runs on your machine).

        Args:
            model: Model ID used
            num_images: Number of images generated

        Returns:
            UsageMetrics with cost = $0
        """
        total_cost = self.COST_PER_IMAGE * num_images

        logger.info(
            f"📊 Local SD usage (FREE) - {model} | "
            f"Images: {num_images} | "
            f"Cost: ${total_cost:.6f} 🎉"
        )

        return UsageMetrics(
            model=model,
            prompt_tokens=0,  # Local SD doesn't expose token usage
            completion_tokens=0,
            cost=total_cost,
        )
