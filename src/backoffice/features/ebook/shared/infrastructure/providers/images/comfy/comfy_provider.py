"""Local Stable Diffusion provider (100% FREE, runs locally, no API token needed)."""

import base64
import json
import logging
import random
import urllib.parse
import urllib.request
import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

import websocket  # type: ignore[import-not-found]
from PIL import Image, ImageDraw

from backoffice.features.ebook.shared.domain.entities.generation_request import ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.domain.ports.image_edit_port import ImageEditPort

logger = logging.getLogger(__name__)


class ComfyProvider(CoverGenerationPort, ContentPageGenerationPort, ImageEditPort):
    """Local Stable Diffusion provider using Comfy (100% FREE, no API).

    Supports:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    - Image editing (via Qwen Image Edit 2509 workflow)
    """

    # Cost: FREE (runs locally)
    COST_PER_IMAGE = Decimal("0")  # Gratuit!

    def __init__(self, model: str | None = None, comfy_url: str | None = "127.0.0.1:8188"):
        """Initialize Local Comfy provider."""

        self.client_id = str(uuid.uuid4())
        self.use_cpu = False
        self.hf_token = None
        self.pipeline = None
        self._model_loaded = False
        self.comfy_url = comfy_url
        self.model = model
        self.workflow = None

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode("utf-8")
        req = urllib.request.Request(f"http://{self.comfy_url}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.comfy_url}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id):
        with urllib.request.urlopen(f"http://{self.comfy_url}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def get_images(self, ws, prompt):
        prompt_id = self.queue_prompt(prompt)["prompt_id"]
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message["type"] == "executing":
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break  # Execution is done
            else:
                continue  # previews are binary data

        history = self.get_history(prompt_id)[prompt_id]
        for _ in history["outputs"]:
            for node_id in history["outputs"]:
                node_output = history["outputs"][node_id]
                images_output = []

                if "images" in node_output:
                    for image in node_output["images"]:
                        image_data = self.get_image(image["filename"], image["subfolder"], image["type"])
                        images_output.append(image_data)
                output_images[node_id] = images_output

        return output_images

    def is_available(self) -> bool:
        """Check if provider is available."""
        req = urllib.request.Request(f"http://{self.comfy_url}", method="GET")
        ping: bool = False
        try:
            urllib.request.urlopen(req).read()
            ping = True
        except URLError:
            pass

        return ping

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - Local SD generates raster images (PNG)
        """
        return False

    def _retrieve_workflow(self, cover: bool, edit: bool = False):
        # Find project root by looking for config/ directory

        current = Path(__file__).resolve()
        while current.parent != current:
            config_dir = current / "config"
            if config_dir.exists() and (config_dir / "generation").exists():
                if not edit:
                    config_path = config_dir / "generation" / "comfy" / f"{self.model}"
                else:
                    config_path = config_dir / "generation" / "comfy" / "edit-image-flux-2.json"

                with open(config_path, encoding="utf-8") as f:
                    workflow_data = f.read()

                self.workflow = json.loads(workflow_data)
                break
            current = current.parent
        else:
            raise FileNotFoundError(f"Could not find config/generation/{self.model}.json in project tree")

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate a colorful cover image.

        Args:
            prompt: Text description of the cover
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility
            workflow_params: Optional workflow params from theme config

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

        self._retrieve_workflow(cover=True)

        if self.workflow is None:
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Failed to load workflow",
                actionable_hint="Check workflow JSON file",
                context={"provider": "comfy", "model": self.model},
            )

        self.workflow["25"]["inputs"]["noise_seed"] = seed
        self.workflow["6"]["inputs"]["text"] = prompt

        # Inject workflow params (e.g., negative prompt in node 47)
        # if workflow_params and "47" in workflow_params:
        #     self.workflow["47"]["inputs"]["text"] = workflow_params["negative"]

        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{self.comfy_url}/ws?clientId={self.client_id}")
            images = self.get_images(ws, self.workflow)

            result_bytes = None

            for node_id in images:
                for image_data in images[node_id]:
                    import io

                    from PIL import Image

                    # buffer = BytesIO()
                    result_bytes = image_data
                    # save image
                    image = Image.open(io.BytesIO(image_data))
                    image.save(f"/tmp/test-{node_id}-{seed}.png")

            logger.info(f"✅ Generated cover (COMFY): {len(result_bytes)} bytes")
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
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate a content page (coloring page).

        Args:
            prompt: Text description of the page
            spec: ImageSpec specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility
            workflow_params: Optional workflow params from theme config

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

        self._retrieve_workflow(cover=False)

        if self.workflow is None:
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Failed to load workflow",
                actionable_hint="Check workflow JSON file",
                context={"provider": "comfy", "model": self.model},
            )

        self.workflow["25"]["inputs"]["noise_seed"] = seed

        # put the seed for random prompts
        prompt_seed = random.randint(0, 2048)
        self.workflow["63"]["inputs"]["seed"] = prompt_seed

        # Coloring page workflow dual clip random prompts (clip_l and t5xxl)

        # self.workflow["63"]["inputs"]["text"] = workflow_params["prompt"]
        self.workflow["63"]["inputs"]["text"] = prompt
        # self.workflow["51"]["inputs"]["text"] = workflow_params["prompt_2"]

        # Inject workflow params (e.g., negative prompt in node 47)
        # if workflow_params and "47" in workflow_params:
        #     self.workflow["47"]["inputs"]["text"] = workflow_params["negative"]

        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{self.comfy_url}/ws?clientId={self.client_id}")
            images = self.get_images(ws, self.workflow)

            result_bytes = None

            for node_id in images:
                for image_data in images[node_id]:
                    import io
                    from PIL import Image

                    result_bytes = image_data
                    # save image
                    image = Image.open(io.BytesIO(image_data))
                    image.save(f"/tmp/test-{node_id}-{seed}.png")

            logger.info(f"✅ Generated page (COMFY): {len(result_bytes)} bytes")
            return result_bytes

        except Exception as e:
            logger.error(f"❌ Comfy generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Comfy generation failed: {str(e)}",
                actionable_hint="Check system resources (RAM/GPU memory) and model availability",
                context={"provider": "comfy", "model": self.model, "error": str(e)},
            ) from e

    async def remove_text_from_cover(self,
                                     image_bytes: bytes,
                                     barcode_width_inches: float = 2.0,
                                     barcode_height_inches: float = 1.2,
                                     barcode_margin_inches: float = 0.25) -> bytes:

        logger.info("🗑️  Removing text from cover (COMFY): returning cover without text elements ...")

        return await self.edit_image(image_bytes,
                                     barcode_width_inches=barcode_width_inches,
                                     barcode_height_inches=barcode_height_inches,
                                     barcode_margin_inches=barcode_margin_inches)

    async def edit_image(
        self,
        image_bytes: bytes,
        edit_prompt: str = None,
        spec: ImageSpec = None,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.5,
        barcode_margin_inches: float = 0.25
    ) -> bytes:
        """Edit an image with a prompt.

        For Comfy, we just return the cover without text.
        If edit_prompt is None then it will remove text from the input image.
        The barcode space will be added later during KDP export assembly, not here.

        Args:
            image_bytes: Original cover image (with text)
            edit_prompt: if present, use this prompt to edit input image (e.g., "replace 5 toes with 3"),
                         otherwise, it will remove all text elements from the given image.
            spec: Image specifications (dimensions, format, etc.).
            barcode_width_inches: Unused (kept for interface compatibility).
            barcode_height_inches: Unused (kept for interface compatibility).
            barcode_margin_inches: Unused (kept for interface compatibility).

        Returns:
            Edited image data as bytes (barcode space will be added during KDP export)

        Raises:
            DomainError: If transformation fails
        """
        if edit_prompt:
            logger.info(f"Edit the given image (COMFY) with this prompt: \n*****\n{edit_prompt}\n******")

        if not self.is_available():
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Comfy provider not available",
                actionable_hint="Run comfy",
                context={"provider": "comfy", "model": self.model},
            )

        self._retrieve_workflow(True, edit=True)

        if self.workflow is None:
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Failed to load workflow",
                actionable_hint="Check workflow JSON file",
                context={"provider": "comfy", "model": self.model},
            )

        # 1. Convert cover bytes to base64
        cover_b64 = base64.b64encode(image_bytes).decode()
        self.workflow["67"]["inputs"]["image"] = cover_b64

        # 2. Generate seed
        seed = random.randint(1, 2**31 - 1)
        self.workflow["25"]["inputs"]["noise_seed"] = seed

        # 3. Modify workflow prompt (by default "remove text") by the "editing" prompt
        #    ONLY if editing_prompt is not None
        if edit_prompt:
            self.workflow["6"]["inputs"]["text"] = edit_prompt

        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{self.comfy_url}/ws?clientId={self.client_id}")
            images = self.get_images(ws, self.workflow)

            result_bytes = None

            for node_id in images:
                for image_data in images[node_id]:
                    import io

                    from PIL import Image

                    result_bytes = image_data

            logger.info(f"✅ Generated edited image (COMFY): {len(result_bytes)} bytes")
            return result_bytes
        except Exception as e:
            logger.error(f"❌ Comfy generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Comfy generation failed: {str(e)}",
                actionable_hint="Check system resources (RAM/GPU memory) and model availability",
                context={"provider": "comfy", "model": self.model, "error": str(e)},
            ) from e


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
