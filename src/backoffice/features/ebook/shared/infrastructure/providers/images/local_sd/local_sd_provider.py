"""Local Stable Diffusion provider (100% FREE, runs locally, no API token needed)."""

import logging
import os
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw

from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.domain.value_objects.usage_metrics import UsageMetrics
from backoffice.features.ebook.shared.infrastructure.providers.publishing.kdp.utils.barcode_utils import (
    add_barcode_space,
)
from backoffice.features.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.shared.domain.errors.error_taxonomy import DomainError, ErrorCode

logger = logging.getLogger(__name__)


class LocalStableDiffusionProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Local Stable Diffusion provider using diffusers (100% FREE, no API).

    Model: black-forest-labs/FLUX.1-schnell (local)
    Cost: $0 (runs on your machine)
    Requirements: ~17GB disk space for model download (first run only)
    Performance: Depends on your hardware (CPU/GPU)

    Supports both:
    - Colorful covers (ColorMode.COLOR)
    - B&W coloring pages (ColorMode.BLACK_WHITE)
    """

    # Model configurations
    FLUX_SCHNELL = "black-forest-labs/FLUX.1-schnell"
    SDXL_TURBO = "stabilityai/sdxl-turbo"  # Faster alternative (2.5GB)

    # Cost: FREE (runs locally)
    COST_PER_IMAGE = Decimal("0")  # Gratuit!

    def __init__(
        self,
        model: str | None = None,
        lora_id: str | None = None,
        controlnet_id: str | None = None,
        use_cpu: bool = False,
    ):
        """Initialize Local Stable Diffusion provider.

        Args:
            model: Specific model to use (defaults to env var or FLUX.1-schnell)
            lora_id: Optional LoRA adapter (e.g., artificialguybr/ColoringBookRedmond-V2)
            controlnet_id: Optional ControlNet model (e.g., lllyasviel/control_v11p_sd15_lineart)
            use_cpu: Force CPU usage (slower but works without GPU)
        """
        # Read model from env var or use provided/default
        env_model = os.getenv("LOCAL_SD_MODEL")
        self.model = model or env_model or self.FLUX_SCHNELL

        # Store LoRA ID for loading later
        self.lora_id = lora_id

        # Store ControlNet ID for loading later
        self.controlnet_id = controlnet_id

        # Debug: Log LoRA configuration
        if lora_id:
            logger.info(f"🎨 LocalSDProvider initialized WITH LoRA: {lora_id}")
        else:
            logger.info("⚠️ LocalSDProvider initialized WITHOUT LoRA (lora_id is None)")

        # Debug: Log ControlNet configuration
        if controlnet_id:
            logger.info(f"🎮 LocalSDProvider initialized WITH ControlNet: {controlnet_id}")

        # Read CPU usage from env var
        env_use_cpu = os.getenv("LOCAL_SD_USE_CPU", "false").lower() == "true"
        self.use_cpu = use_cpu or env_use_cpu

        # Get HF token for gated models (FLUX.1-schnell requires it)
        self.hf_token = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")

        self.pipeline = None
        self.controlnet = None
        self._model_loaded = False

        # Check if diffusers is available
        try:
            import torch  # noqa: F401
            from diffusers import AutoPipelineForText2Image  # noqa: F401

            logger.info(f"LocalStableDiffusionProvider initialized: {self.model}")
        except ImportError as e:
            logger.error(
                "diffusers/torch not installed: pip install diffusers torch transformers accelerate"
            )
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Local SD packages not installed",
                actionable_hint="Run: pip install diffusers torch transformers accelerate",
                context={"error": str(e)},
            ) from e

    def is_available(self) -> bool:
        """Check if provider is available."""
        try:
            import torch  # noqa: F401
            from diffusers import AutoPipelineForText2Image  # noqa: F401

            return True
        except ImportError:
            return False

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization.

        Returns:
            False - Local SD generates raster images (PNG)
        """
        return False

    def _load_model(self):
        """Load the Stable Diffusion model (lazy loading).

        Downloads model on first run (~17GB for FLUX.1-schnell).
        """
        if self._model_loaded:
            return

        logger.info(f"🔄 Loading local model: {self.model} (this may take a while on first run)...")

        try:
            import torch

            # Determine device (prioritize MPS for Apple Silicon Macs)
            if self.use_cpu:
                device = "cpu"
                dtype = torch.float32
                logger.info("⚙️ Using CPU (force mode)")
            elif torch.backends.mps.is_available():
                device = "mps"  # Apple Silicon GPU with unified memory
                dtype = torch.float16
                logger.info("🍎 Using Apple Silicon GPU (MPS) with unified memory - fast!")
            elif torch.cuda.is_available():
                device = "cuda"  # NVIDIA GPU
                dtype = torch.float16
                logger.info("🚀 Using NVIDIA GPU (CUDA)")
            else:
                device = "cpu"
                dtype = torch.float32
                logger.info("⚙️ Using CPU (no GPU detected)")

            # Load ControlNet if specified (must be loaded before pipeline)
            if self.controlnet_id:
                from diffusers import ControlNetModel

                logger.info(f"🎮 Loading ControlNet model: {self.controlnet_id}")
                self.controlnet = ControlNetModel.from_pretrained(
                    self.controlnet_id,
                    torch_dtype=dtype,
                    token=self.hf_token,
                )
                self.controlnet = self.controlnet.to(device)
                logger.info("✅ ControlNet loaded successfully")

            # Load pipeline (auto-detect model type and ControlNet support)
            # Pass HF token for gated models (FLUX.1-schnell)
            if self.controlnet_id:
                # Use ControlNet-enabled pipeline
                from diffusers import StableDiffusionXLControlNetPipeline

                logger.info("Loading SDXL pipeline with ControlNet support...")
                self.pipeline = StableDiffusionXLControlNetPipeline.from_pretrained(
                    self.model,
                    controlnet=self.controlnet,
                    torch_dtype=dtype,
                    token=self.hf_token,
                )
            else:
                # Use standard pipeline
                from diffusers import AutoPipelineForText2Image

                self.pipeline = AutoPipelineForText2Image.from_pretrained(
                    self.model,
                    torch_dtype=dtype,
                    token=self.hf_token,  # Required for gated models
                )

            self.pipeline = self.pipeline.to(device)

            # Load LoRA weights if specified
            if self.lora_id:
                logger.info(f"📚 Loading LoRA adapter: {self.lora_id}")
                self.pipeline.load_lora_weights(self.lora_id)
                logger.info("✅ LoRA loaded successfully")

            # Memory optimizations disabled for max speed
            # (SDXL-turbo is lightweight enough, no need to sacrifice performance)
            logger.info("⚡ Memory optimizations disabled - running at max speed")

            self._model_loaded = True
            logger.info(f"✅ Model loaded successfully on {device}")

        except Exception as e:
            logger.error(f"❌ Failed to load model: {str(e)}")
            raise DomainError(
                code=ErrorCode.MODEL_UNAVAILABLE,
                message=f"Failed to load local model: {str(e)}",
                actionable_hint="Check disk space (~17GB) and internet for first download",
                context={"provider": "local_sd", "model": self.model, "error": str(e)},
            ) from e

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
                code=ErrorCode.MODEL_UNAVAILABLE,
                message="Local SD provider not available",
                actionable_hint="Install: pip install diffusers torch transformers accelerate",
                context={"provider": "local_sd", "model": self.model},
            )

        # Load model if not already loaded
        self._load_model()

        # Build prompt based on color mode
        if spec.color_mode == ColorMode.BLACK_WHITE:
            # B&W coloring page style
            # Add ColoringBook LoRA trigger tags if using ColoringBook.Redmond
            lora_prefix = ""
            if self.lora_id and "ColoringBook" in self.lora_id:
                lora_prefix = "ColoringBookAF, Coloring Book, "
                logger.info("🎨 Using ColoringBook LoRA trigger tags")

            # Clean prompt: remove redundant text from PromptTemplateEngine to save tokens
            clean_prompt = prompt.replace("Line art coloring page of a ", "")
            clean_prompt = clean_prompt.split("Bold clean outlines")[
                0
            ].strip()  # Remove quality_settings

            full_prompt = (
                f"{lora_prefix}"
                f"cute simple cartoon style for young kids, "
                f"{clean_prompt}, "
                f"thick outlines, simple shapes"
            )
        else:
            # Colorful cover style
            full_prompt = (
                f"Create a vibrant, colorful cover illustration perfect for a children's book. "
                f"IMPORTANT: The illustration must fill the ENTIRE frame edge-to-edge "
                f"with NO white margins or borders. "
                f"Full-bleed design - the main subject should extend to all edges of the image. "
                f"Rich colors, engaging composition. "
                f"Content: {prompt}"
            )

        logger.info(f"Generating cover via Local SD: {full_prompt[:100]}...")

        try:
            import torch

            assert self.pipeline is not None  # _load_model() ensures this

            # Set seed for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.pipeline.device).manual_seed(seed)

            # Generate image (adapt params based on model type)
            model_lower = self.model.lower()

            if "flux" in model_lower:
                # FLUX.1-schnell: optimized for 4 steps
                num_steps = 4
                guidance = 0.0
                logger.info("Using FLUX optimized params: 4 steps, guidance=0.0")
            elif "turbo" in model_lower:
                # SDXL-turbo: optimized for 1-4 steps, but can push to 6-8 for better quality
                # Allow override via env var for quality tuning
                num_steps = int(os.getenv("SDXL_TURBO_STEPS", "6"))  # Default: 6 (balance)
                guidance = float(os.getenv("SDXL_TURBO_GUIDANCE", "0.0"))  # Turbo works best at 0.0
                logger.info(f"Using SDXL-turbo params: {num_steps} steps, guidance={guidance}")
            elif "sdxl" in model_lower or "stable-diffusion-xl" in model_lower:
                # SDXL base: better quality with more steps
                num_steps = 30
                guidance = 7.5
                logger.info("Using SDXL base params: 30 steps, guidance=7.5 (better quality)")
            else:
                # Other models: default params
                num_steps = 20
                guidance = 7.5
                logger.info("Using default params: 20 steps, guidance=7.5")

            # Prepare ControlNet image if using ControlNet
            control_image = None
            if self.controlnet_id:
                control_image = self._preprocess_for_controlnet(spec)

            # Auto-downscale if requested size is too large for SDXL memory
            # SDXL works best with sizes up to 1024x1280
            MAX_SDXL_DIM = 1280
            target_width = spec.width_px
            target_height = spec.height_px
            needs_upscaling = False

            if spec.width_px > MAX_SDXL_DIM or spec.height_px > MAX_SDXL_DIM:
                # Calculate optimal generation size (preserve aspect ratio)
                aspect_ratio = spec.width_px / spec.height_px
                if spec.height_px > spec.width_px:
                    # Portrait orientation (like KDP 8x10)
                    gen_height = MAX_SDXL_DIM
                    gen_width = int(gen_height * aspect_ratio)
                else:
                    # Landscape or square
                    gen_width = MAX_SDXL_DIM
                    gen_height = int(gen_width / aspect_ratio)

                logger.info(
                    f"📐 Auto-downscaling for generation: "
                    f"{spec.width_px}x{spec.height_px} → {gen_width}x{gen_height} "
                    f"(will upscale to KDP specs after)"
                )
                needs_upscaling = True
            else:
                gen_width = spec.width_px
                gen_height = spec.height_px

            # Build pipeline parameters
            pipeline_params = {
                "prompt": full_prompt,
                "height": gen_height,
                "width": gen_width,
                "num_inference_steps": num_steps,
                "guidance_scale": guidance,
                "generator": generator,
            }

            # Add ControlNet image if available
            if control_image is not None:
                pipeline_params["image"] = control_image
                pipeline_params["controlnet_conditioning_scale"] = 1.0
                logger.info("🎮 Using ControlNet for guided generation")

            result = self.pipeline(**pipeline_params)

            pil_image = result.images[0]

            # Upscale to target KDP specs if needed (high-quality LANCZOS)
            if needs_upscaling:
                logger.info(f"🔍 Upscaling to KDP specs: {target_width}x{target_height}")
                pil_image = pil_image.resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                )

            # Convert to bytes
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            result_bytes = buffer.getvalue()

            # Add rounded border for B&W coloring pages
            if spec.color_mode == ColorMode.BLACK_WHITE:
                logger.info("Adding rounded black border to coloring page...")
                result_bytes = self._add_rounded_border_to_image(result_bytes)

            logger.info(f"✅ Generated cover (LOCAL): {len(result_bytes)} bytes")
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
        return await self.generate_cover(prompt, spec, seed)

    async def remove_text_from_cover(
        self,
        cover_bytes: bytes,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.5,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover to create back cover.

        Note: Local SD doesn't have a text removal model yet.
        We'll use a simple PIL-based solution with KDP-compliant barcode space.

        Args:
            cover_bytes: Original cover image (with text)
            barcode_width_inches: KDP barcode width in inches (default: 2.0)
            barcode_height_inches: KDP barcode height in inches (default: 1.5)
            barcode_margin_inches: KDP barcode margin in inches (default: 0.25)

        Returns:
            Same image with KDP-compliant barcode space (for back cover)

        Raises:
            DomainError: If transformation fails
        """
        logger.info("🗑️  Removing text from cover (Local SD: PIL-based fallback)...")

        try:
            # Add KDP barcode space using centralized utility
            logger.info("📦 Adding KDP barcode space...")
            final_bytes = add_barcode_space(
                cover_bytes,
                barcode_width_inches=barcode_width_inches,
                barcode_height_inches=barcode_height_inches,
                barcode_margin_inches=barcode_margin_inches,
            )

            logger.info(f"✅ KDP barcode space added (LOCAL): {len(final_bytes)} bytes")
            return final_bytes

        except Exception as e:
            logger.error(f"❌ Local SD text removal failed: {str(e)}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Local SD text removal failed: {str(e)}",
                actionable_hint="Check image format",
                context={"provider": "local_sd", "error": str(e)},
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
