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

    def _retrieve_workflow(self, cover: bool, back_cover: bool = False):
        # Find project root by looking for config/ directory

        current = Path(__file__).resolve()
        while current.parent != current:
            config_dir = current / "config"
            if config_dir.exists() and (config_dir / "generation").exists():
                if not back_cover:
                    config_path = config_dir / "generation" / "comfy" / f"{self.model}"
                else:
                    config_path = config_dir / "generation" / "comfy" / "remove_text_from_cover_qwen.json"

                with open(config_path, encoding="utf-8") as f:
                    workflow_data = f.read()

                self.workflow = json.loads(workflow_data)
                break
            current = current.parent
        else:
            raise FileNotFoundError(f"Could not find config/generation/{self.model}.json in project tree")

    def _load_workflow(self, spec: ImageSpec, cover: bool):
        self._retrieve_workflow(cover)

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

        self._load_workflow(spec, True)

        if self.workflow is None:
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Failed to load workflow",
                actionable_hint="Check workflow JSON file",
                context={"provider": "comfy", "model": self.model},
            )

        self.workflow["31"]["inputs"]["seed"] = seed
        self.workflow["54"]["inputs"]["text"] = workflow_params["prompt"]

        # Inject workflow params (e.g., negative prompt in node 47)
        if workflow_params and "47" in workflow_params:
            self.workflow["47"]["inputs"]["text"] = workflow_params["negative"]

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

        self._load_workflow(spec, False)

        if self.workflow is None:
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Failed to load workflow",
                actionable_hint="Check workflow JSON file",
                context={"provider": "comfy", "model": self.model},
            )

        self.workflow["31"]["inputs"]["seed"] = seed

        # Coloring page workflow dual clip random prompts (clip_l and t5xxl)

        self.workflow["50"]["inputs"]["text"] = workflow_params["prompt_1"]
        self.workflow["51"]["inputs"]["text"] = workflow_params["prompt_2"]

        # Inject workflow params (e.g., negative prompt in node 47)
        if workflow_params and "47" in workflow_params:
            self.workflow["47"]["inputs"]["text"] = workflow_params["negative"]

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

    async def remove_text_from_cover(
        self,
        cover_bytes: bytes,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.5,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover to create back cover.

        For Comfy, we just return the cover without text.
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
        logger.info("🗑️  Removing text from cover (COMFY): returning cover as-is)...")

        if not self.is_available():
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Comfy provider not available",
                actionable_hint="Run comfy",
                context={"provider": "comfy", "model": self.model},
            )

        self._retrieve_workflow(True, back_cover=True)

        if self.workflow is None:
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Failed to load workflow",
                actionable_hint="Check workflow JSON file",
                context={"provider": "comfy", "model": self.model},
            )



        # 1. Convert cover bytes to base64
        cover_b64 = base64.b64encode(cover_bytes).decode()

        self.workflow["103"]["inputs"]["image"] = cover_b64

        # 2. Generate seed
        seed = random.randint(1, 2**31 - 1)
        self.workflow["3"]["inputs"]["seed"] = seed

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
                    # image = Image.open(io.BytesIO(image_data))
                    # image.save(f"/tmp/test-{back}-{seed}.png")


            logger.info(f"✅ Generated back cover (COMFY): {len(result_bytes)} bytes")
            return result_bytes
        except Exception as e:
            logger.error(f"❌ Comfy generation failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Comfy generation failed: {str(e)}",
                actionable_hint="Check system resources (RAM/GPU memory) and model availability",
                context={"provider": "comfy", "model": self.model, "error": str(e)},
            ) from e

        # Just return the cover - barcode space will be added during KDP export
        # not during back cover generation
        logger.info(f"✅ Back cover ready (no barcode space): {len(cover_bytes)} bytes")
        return cover_bytes

    async def edit_image(
        self,
        image: bytes,
        edit_prompt: str,
        spec: ImageSpec,
    ) -> bytes:
        """Edit an existing image based on text instructions using Qwen Image Edit 2509.

        Uploads the image to ComfyUI, loads Qwen edit workflow, and applies corrections.

        Args:
            image: Original image data as bytes (PNG format)
            edit_prompt: Text instructions for editing (e.g., "replace 5 toes with 3")
            spec: Image specifications (dimensions, format, etc.)

        Returns:
            Edited image data as bytes

        Raises:
            DomainError: If editing fails
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.COMFY_UNAVAILABLE,
                message="Comfy provider not available",
                actionable_hint="Start ComfyUI server at http://127.0.0.1:8188",
                context={"provider": "comfy", "comfy_url": self.comfy_url},
            )

        logger.info(f"Editing image via ComfyUI (Qwen): {edit_prompt[:100]}...")

        try:
            # Upload image to ComfyUI
            image_name = self._upload_image_to_comfy(image)

            # Load Qwen edit workflow (assuming model contains "edit" for edit workflows)
            # TODO: This needs a dedicated Qwen edit workflow JSON file
            # For now, we'll assume the workflow is named something like "qwen-edit-workflow.json"
            edit_workflow_model = "qwen-edit-workflow.json"

            # Store original model and temporarily switch to edit workflow
            original_model = self.model
            self.model = edit_workflow_model

            try:
                self._retrieve_workflow(cover=False)
            except FileNotFoundError:
                raise DomainError(
                    code=ErrorCode.COMFY_UNAVAILABLE,
                    message=f"Qwen edit workflow not found: {edit_workflow_model}",
                    actionable_hint="Create config/generation/comfy/qwen-edit-workflow.json for image editing",
                    context={"provider": "comfy", "workflow": edit_workflow_model},
                )
            finally:
                # Restore original model
                self.model = original_model

            if self.workflow is None:
                raise DomainError(
                    code=ErrorCode.COMFY_UNAVAILABLE,
                    message="Failed to load Qwen edit workflow",
                    actionable_hint="Check config/generation/comfy/qwen-edit-workflow.json exists and is valid",
                    context={"provider": "comfy", "workflow": edit_workflow_model},
                )

            # Inject image and edit prompt into workflow
            # Node 1: LoadImage - set uploaded image name
            if "1" in self.workflow:
                self.workflow["1"]["inputs"]["image"] = image_name
                logger.info(f"Set input image to node 1: {image_name}")

            # Node 2: CLIPTextEncode - set edit prompt
            if "2" in self.workflow:
                self.workflow["2"]["inputs"]["text"] = edit_prompt
                logger.info(f"Set edit prompt to node 2: {edit_prompt[:50]}...")

            # Execute workflow
            ws = websocket.WebSocket()
            ws.connect(f"ws://{self.comfy_url}/ws?clientId={self.client_id}")
            images = self.get_images(ws, self.workflow)

            # Extract edited image
            result_bytes = None
            for node_id in images:
                for image_data in images[node_id]:
                    result_bytes = image_data
                    break
                if result_bytes:
                    break

            if not result_bytes:
                raise DomainError(
                    code=ErrorCode.PROVIDER_TIMEOUT,
                    message="No edited image returned from Qwen workflow",
                    actionable_hint="Check workflow configuration and node IDs",
                    context={"provider": "comfy", "workflow": edit_workflow_model},
                )

            logger.info(f"✅ Edited image (ComfyUI Qwen): {len(result_bytes)} bytes")
            return result_bytes

        except DomainError:
            raise
        except Exception as e:
            logger.error(f"❌ ComfyUI image editing failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"ComfyUI image editing failed: {str(e)}",
                actionable_hint="Check ComfyUI server is running and Qwen workflow is configured",
                context={"provider": "comfy", "error": str(e)},
            ) from e

    def _upload_image_to_comfy(self, image_bytes: bytes) -> str:
        """Upload an image to ComfyUI and return the uploaded filename.

        Args:
            image_bytes: Image data as bytes

        Returns:
            Uploaded image filename on ComfyUI server

        Raises:
            DomainError: If upload fails
        """
        try:
            import io

            # Generate unique filename
            import time

            filename = f"edit_input_{int(time.time() * 1000)}.png"

            # Prepare multipart form data
            files = {"image": (filename, io.BytesIO(image_bytes), "image/png")}
            data = {"subfolder": "edit_inputs", "type": "input", "overwrite": "true"}

            # Upload via HTTP POST
            import urllib.request

            # Create multipart form data manually
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            body = b""

            # Add regular fields
            for key, value in data.items():
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
                body += f"{value}\r\n".encode()

            # Add file
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode()
            body += b"Content-Type: image/png\r\n\r\n"
            body += image_bytes
            body += b"\r\n"
            body += f"--{boundary}--\r\n".encode()

            # Send request
            req = urllib.request.Request(
                f"http://{self.comfy_url}/upload/image",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
                uploaded_name: str = result.get("name", filename)
                logger.info(f"Uploaded image to ComfyUI: {uploaded_name}")
                return uploaded_name

        except Exception as e:
            logger.error(f"❌ Failed to upload image to ComfyUI: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Failed to upload image to ComfyUI: {str(e)}",
                actionable_hint="Check ComfyUI server is running and accessible",
                context={"comfy_url": self.comfy_url, "error": str(e)},
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
