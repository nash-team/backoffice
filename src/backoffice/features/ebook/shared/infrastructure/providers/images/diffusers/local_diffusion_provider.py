"""Local Diffusion provider using HuggingFace diffusers (100% FREE, runs locally).

Supports SDXL with optional LoRA for high-quality line art generation (txt2img).

Configuration:
- Model params (checkpoint, lora, lora_weight) come from models.yaml
- Generation params (negative_prompt, guidance_scale, steps) come from theme YAML
"""

import asyncio
import logging
import random
import threading
from decimal import Decimal
from io import BytesIO

import torch
from PIL import Image

from backoffice.features.ebook.shared.domain.entities.generation_request import ColorMode, ImageSpec
from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.ebook.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.ebook.shared.infrastructure.utils.image_borders import (
    add_rounded_border_to_image,
)

logger = logging.getLogger(__name__)


class LocalDiffusionImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Local SDXL provider using HuggingFace diffusers (100% FREE, no API).

    Supports:
    - SDXL base or fine-tuned checkpoints (e.g., coloring book models)
    - LoRA for style customization (coloring book, line art)
    - MPS (Mac), CUDA (NVIDIA), or CPU inference
    - Post-processing for clean B&W line art

    Model config (models.yaml):
    - model: SDXL checkpoint HF ID or local path
    - lora: LoRA path or HF model ID (optional)
    - lora_weight: LoRA weight 0.0-1.0

    Generation params (theme YAML workflow_params):
    - negative_prompt: Negative prompt
    - guidance_scale: CFG scale (default: 7.5 color, 9.0 B&W)
    - steps: Inference steps (default: 25 color, 35 B&W)
    """

    # Cost: FREE (runs locally)
    COST_PER_IMAGE = Decimal("0")

    def __init__(
        self,
        model: str,
        lora: str | None = None,
        lora_weight: float = 0.7,
        device: str | None = None,
    ):
        """Initialize Local Diffusion provider.

        Args:
            model: SDXL checkpoint (HF model ID or local path) - from models.yaml
            lora: LoRA path or HF model ID (optional) - from models.yaml
            lora_weight: LoRA weight 0.0-1.0 - from models.yaml
            device: Device override (auto-detected if None)
        """
        self.model = model
        self.lora = lora
        self.lora_weight = lora_weight
        self.device = device or self._detect_device()

        # Pipeline will be lazily loaded
        self._pipeline = None
        self._lora_loaded = False

        # Thread lock for pipeline access (diffusers not officially thread-safe)
        self._lock = threading.Lock()

        logger.info(f"LocalDiffusionImageProvider: model={self.model}, device={self.device}, " f"lora={self.lora} (weight={self.lora_weight if self.lora else 'N/A'})")

    def _detect_device(self) -> str:
        """Auto-detect best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            logger.warning("No GPU detected, using CPU (will be slow)")
            return "cpu"

    def _get_torch_dtype(self) -> torch.dtype:
        """Get appropriate dtype for device."""
        if self.device == "cpu":
            return torch.float32
        elif self.device == "mps":
            # MPS (Apple Silicon) MUST use float32 to avoid NaN → black images
            return torch.float32
        # CUDA uses float16 for speed and memory efficiency
        return torch.float16

    def _load_pipeline(self):
        """Lazily load the diffusion pipeline (thread-safe)."""
        if self._pipeline is not None:
            return

        with self._lock:
            # Double-check after acquiring lock
            if self._pipeline is not None:
                return

            logger.info(f"Loading SDXL pipeline: {self.model} on {self.device}...")

            try:
                from diffusers import StableDiffusionXLPipeline

                self._pipeline = StableDiffusionXLPipeline.from_pretrained(
                    self.model,
                    torch_dtype=self._get_torch_dtype(),
                    variant="fp16" if self.device == "cuda" else None,
                    use_safetensors=True,
                )
                self._pipeline = self._pipeline.to(self.device)

                # Disable safety checker (can cause black images on some content)
                self._pipeline.safety_checker = None

                # Load LoRA if specified
                if self.lora and not self._lora_loaded:
                    self._load_lora()

                # Enable memory optimizations
                if self.device == "cuda":
                    self._pipeline.enable_model_cpu_offload()
                elif self.device == "mps":
                    # MPS (Apple Silicon) - minimal optimizations to avoid artifacts
                    # Note: Using float32 (not float16) to prevent NaN issues
                    self._pipeline.enable_attention_slicing()  # Default slicing (not "max")
                    logger.info("MPS optimizations enabled: attention_slicing (float32 mode)")

                logger.info(f"Pipeline loaded on {self.device}")

            except ImportError as e:
                raise DomainError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="Diffusers library not installed",
                    actionable_hint="Run: pip install diffusers transformers accelerate torch",
                    context={"error": str(e)},
                ) from e
            except Exception as e:
                logger.error(f"Failed to load pipeline: {e}")
                raise DomainError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message=f"Failed to load diffusion model: {e}",
                    actionable_hint="Check model path and available memory",
                    context={"model": self.model, "error": str(e)},
                ) from e

    def _load_lora(self):
        """Load LoRA weights into the pipeline (must hold lock)."""
        if not self.lora:
            return

        logger.info(f"Loading LoRA: {self.lora} (weight={self.lora_weight})...")

        try:
            self._pipeline.load_lora_weights(self.lora)
            self._pipeline.fuse_lora(lora_scale=self.lora_weight)
            self._lora_loaded = True
            logger.info(f"LoRA loaded and fused: {self.lora}")
        except Exception as e:
            logger.warning(f"Failed to load LoRA (continuing without it): {e}")

    def is_available(self) -> bool:
        """Check if provider is available (diffusers installed)."""
        try:
            import diffusers  # noqa: F401

            return True
        except ImportError:
            return False

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization."""
        return False

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate a colorful cover image.

        Args:
            prompt: Text description (from theme YAML via strategy)
            spec: Image specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility
            workflow_params: Params from theme YAML (negative_prompt, guidance_scale, steps)

        Returns:
            Cover image as bytes
        """
        return await self._generate_image(prompt, spec, seed, workflow_params)

    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Generate a content page (coloring page).

        Args:
            prompt: Text description (from theme YAML via strategy)
            spec: ImageSpec specifications (dimensions, format, color mode)
            seed: Random seed for reproducibility
            workflow_params: Params from theme YAML (negative_prompt, guidance_scale, steps)

        Returns:
            Page image as bytes
        """
        return await self._generate_image(prompt, spec, seed, workflow_params)

    async def _generate_image(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
        workflow_params: dict[str, str] | None = None,
    ) -> bytes:
        """Internal image generation logic.

        Runs the diffusion pipeline in a thread executor to avoid blocking
        the async event loop (FastAPI/Starlette).

        Args:
            prompt: Complete prompt from strategy (built from theme YAML)
            spec: Image specifications
            seed: Random seed for reproducibility
            workflow_params: Generation parameters from theme YAML

        Returns:
            Generated image as bytes
        """
        if not self.is_available():
            raise DomainError(
                code=ErrorCode.PROVIDER_UNAVAILABLE,
                message="Diffusers library not installed",
                actionable_hint="Run: pip install diffusers transformers accelerate torch",
                context={"provider": "diffusers"},
            )

        # Lazy load pipeline (thread-safe)
        self._load_pipeline()

        # Parse workflow_params from theme YAML
        params = workflow_params or {}

        # Different defaults for B&W vs Color
        is_bw = spec.color_mode == ColorMode.BLACK_WHITE

        # Default negative prompts optimized for line art vs color
        default_negative = "color, shading, gradient, gray, blurry, watermark, filled areas" if is_bw else "blurry, low quality, watermark, signature, text"
        negative_prompt = params.get("negative_prompt", default_negative)

        # Higher CFG and more steps for cleaner B&W line art
        default_cfg = "9.0" if is_bw else "7.5"
        default_steps = "35" if is_bw else "25"
        guidance_scale = float(params.get("guidance_scale", default_cfg))
        num_inference_steps = int(params.get("steps", default_steps))

        # Set seed (not for crypto, just for reproducible image generation)
        if seed is None:
            seed = random.randint(0, 2**32 - 1)  # noqa: S311

        # SDXL native size is 1024x1024 - generate at native then upscale
        # This is MUCH faster and uses less memory (critical for MPS)
        SDXL_NATIVE_SIZE = 1024
        gen_width = SDXL_NATIVE_SIZE
        gen_height = SDXL_NATIVE_SIZE
        needs_upscale = spec.width_px != SDXL_NATIVE_SIZE or spec.height_px != SDXL_NATIVE_SIZE

        logger.info(f"Generating: {gen_width}x{gen_height} → upscale to {spec.width_px}x{spec.height_px}, " f"seed={seed}, steps={num_inference_steps}, cfg={guidance_scale}, bw={is_bw}")
        logger.debug(f"Prompt: {prompt[:200]}...")

        # Run diffusion in executor with thread lock
        pipeline = self._pipeline  # Capture for closure + type narrowing

        def _run_diffusion() -> Image.Image:
            if pipeline is None:
                raise RuntimeError("Pipeline not loaded")
            # MPS bug: Generator on MPS causes black images, use CPU generator instead
            gen_device = "cpu" if self.device == "mps" else self.device
            generator = torch.Generator(device=gen_device).manual_seed(seed)
            with self._lock:
                result = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=gen_width,
                    height=gen_height,
                    guidance_scale=guidance_scale,
                    num_inference_steps=num_inference_steps,
                    generator=generator,
                )
            return result.images[0]

        try:
            loop = asyncio.get_running_loop()
            image: Image.Image = await loop.run_in_executor(None, _run_diffusion)

            # Upscale to final dimensions (from 1024x1024 to spec.width_px x spec.height_px)
            if needs_upscale:
                logger.info(f"Upscaling {image.width}x{image.height} → {spec.width_px}x{spec.height_px}")
                image = image.resize((spec.width_px, spec.height_px), Image.Resampling.LANCZOS)

            # Debug: log image info before any post-processing
            logger.info(f"[DEBUG] Raw SDXL output: mode={image.mode}, size={image.size}, " f"min/max pixel={(min(image.getdata()), max(image.getdata())) if image.mode == 'L' else 'N/A (RGB)'}")

            # DEBUG: Save raw image to /tmp for inspection
            if is_bw:
                debug_path = "/tmp/debug_raw_sdxl.png"
                image.save(debug_path)
                logger.info(f"[DEBUG] Saved raw SDXL image to {debug_path} - CHECK THIS FILE!")

            # Post-process for B&W coloring pages: convert to pure black & white
            # Can be disabled via workflow_params.skip_lineart_postprocess = "true"
            skip_postprocess = str(params.get("skip_lineart_postprocess", "false")).lower() == "true"

            if is_bw and not skip_postprocess:
                logger.info(f"[DEBUG] Before lineart: mode={image.mode}, size={image.size}")
                image = self._convert_to_lineart(image)
                logger.info(f"[DEBUG] After lineart: mode={image.mode}, size={image.size}")
            elif is_bw and skip_postprocess:
                logger.info("[DEBUG] Skipping lineart post-processing (skip_lineart_postprocess=true)")

            # Convert to bytes
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()

            # Add rounded border for coloring pages
            if is_bw:
                image_bytes = add_rounded_border_to_image(image_bytes)

            logger.info(f"Generated: {len(image_bytes)} bytes (seed={seed})")
            return image_bytes

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise DomainError(
                code=ErrorCode.PROVIDER_TIMEOUT,
                message=f"Image generation failed: {e}",
                actionable_hint="Check GPU memory and model availability",
                context={"provider": "diffusers", "model": self.model, "error": str(e)},
            ) from e

    def _convert_to_lineart(self, image: Image.Image, threshold: int = 128) -> Image.Image:
        """Convert image to pure black & white line art.

        For coloring pages: keeps dark pixels as black lines, light pixels as white.
        Threshold logic: pixels ABOVE threshold → white (background), BELOW → black (lines).

        Args:
            image: Input PIL image
            threshold: Brightness threshold (0-255). Lower = thicker lines.

        Returns:
            Pure B&W image converted back to RGB
        """
        from PIL import ImageFilter

        # 1. Grayscale
        gray = image.convert("L")

        # 2. Light blur to smooth noise
        gray = gray.filter(ImageFilter.GaussianBlur(0.5))

        # 3. INVERTED threshold: pixels > threshold → white, else → black
        # This preserves dark lines (low values) as black
        bw = gray.point(lambda x: 255 if x > threshold else 0, "L")

        # 4. Return as RGB
        return bw.convert("RGB")

    async def remove_text_from_cover(
        self,
        image_bytes: bytes,
        spec: ImageSpec,
        barcode_width_inches: float = 2.0,
        barcode_height_inches: float = 1.2,
        barcode_margin_inches: float = 0.25,
    ) -> bytes:
        """Remove text from cover (not supported - returns original).

        Use GeminiImageProvider or ComfyProvider for text removal.
        """
        logger.warning("LocalDiffusionImageProvider.remove_text_from_cover not implemented. " "Use Gemini or Comfy provider.")
        return image_bytes
