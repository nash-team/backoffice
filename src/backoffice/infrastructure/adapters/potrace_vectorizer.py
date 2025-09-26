import asyncio
import logging
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from backoffice.domain.ports.vectorization_port import VectorizationPort

logger = logging.getLogger(__name__)


class VectorizationError(Exception):
    pass


class PotraceVectorizer(VectorizationPort):
    """Potrace-based image vectorization adapter implementing VectorizationPort"""

    def __init__(self):
        logger.info("PotraceVectorizer initialized")

    def is_available(self) -> bool:
        """Check if Potrace is available on the system"""
        try:
            result = subprocess.run(
                ["potrace", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            logger.warning("Potrace not available on system")
            return False

    async def vectorize_image(self, image_data: bytes) -> str:
        """Convert raster image to SVG using Potrace"""
        try:
            logger.info("Starting image vectorization with Potrace")

            # Preprocess the image for better vectorization
            processed_image = await self._preprocess_for_vectorization(image_data)

            if not self.is_available():
                logger.warning("Potrace not available, using fallback SVG generation")
                return await self._create_fallback_svg()

            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_png:
                temp_png.write(processed_image)
                temp_png_path = temp_png.name

            temp_svg_path = temp_png_path.replace(".png", ".svg")

            try:
                # Run Potrace to convert PNG to SVG
                cmd = [
                    "potrace",
                    "--svg",
                    "--output",
                    temp_svg_path,
                    "--turdsize",
                    "2",  # Suppress small speckles
                    "--turnpolicy",
                    "minority",  # Resolve ambiguities
                    "--alphamax",
                    "1.0",  # Corner sharpness
                    temp_png_path,
                ]

                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await result.communicate()

                if result.returncode != 0:
                    logger.error(f"Potrace failed: {stderr.decode()}")
                    return await self._create_fallback_svg()

                # Read the generated SVG
                svg_path = Path(temp_svg_path)
                if svg_path.exists():
                    svg_content = svg_path.read_text()
                    return await self.optimize_for_coloring(svg_content)
                else:
                    logger.error("Potrace did not generate SVG file")
                    return await self._create_fallback_svg()

            finally:
                # Cleanup temporary files
                Path(temp_png_path).unlink(missing_ok=True)
                Path(temp_svg_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Error vectorizing image: {str(e)}")
            return await self._create_fallback_svg()

    async def optimize_for_coloring(self, svg_content: str) -> str:
        """Optimize SVG for coloring book use"""
        try:
            logger.info("Optimizing SVG for coloring book")

            # Parse the SVG
            root = ET.fromstring(svg_content)

            # Define namespace
            ns = {"svg": "http://www.w3.org/2000/svg"}

            # Set SVG attributes for better coloring book format
            root.set("width", "100%")
            root.set("height", "100%")
            root.set("viewBox", "0 0 1024 1024")

            # Find all paths and optimize them
            for path in root.findall(".//svg:path", ns):
                # Set stroke properties for coloring book style
                path.set("stroke", "black")
                path.set("stroke-width", "3")
                path.set("fill", "none")  # No fill so it can be colored
                path.set("stroke-linecap", "round")
                path.set("stroke-linejoin", "round")

            # Add a white background rectangle
            background = ET.Element("rect")
            background.set("x", "0")
            background.set("y", "0")
            background.set("width", "100%")
            background.set("height", "100%")
            background.set("fill", "white")
            root.insert(0, background)

            # Convert back to string
            optimized_svg = ET.tostring(root, encoding="unicode")

            # Add XML declaration if missing
            if not optimized_svg.startswith("<?xml"):
                optimized_svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + optimized_svg

            return optimized_svg

        except Exception as e:
            logger.error(f"Error optimizing SVG: {str(e)}")
            # Return original content if optimization fails
            return svg_content

    async def _preprocess_for_vectorization(self, image_data: bytes) -> bytes:
        """Preprocess image to improve vectorization results"""
        try:
            # Load image
            image = Image.open(BytesIO(image_data))

            # Convert to grayscale for better edge detection
            if image.mode != "L":
                grayscale_image = image.convert("L")
            else:
                grayscale_image = image

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(grayscale_image)
            enhanced_image = enhancer.enhance(2.0)

            # Apply slight blur to reduce noise before edge detection
            blurred_image = enhanced_image.filter(ImageFilter.GaussianBlur(radius=0.5))

            # Convert to black and white (binary)
            contrasted_image = ImageOps.autocontrast(blurred_image)

            # Threshold to pure black and white
            threshold = 128
            binary_image = contrasted_image.point(lambda x: 255 if x > threshold else 0, mode="1")

            # Convert back to RGB for PNG saving
            rgb_image = binary_image.convert("RGB")

            # Save to bytes
            buffer = BytesIO()
            rgb_image.save(buffer, format="PNG")
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            # Return original image data if preprocessing fails
            return image_data

    async def _create_fallback_svg(self) -> str:
        """Create a simple fallback SVG when Potrace is not available"""
        return """<?xml version="1.0" encoding="UTF-8"?>
<svg width="100%" height="100%" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="100%" height="100%" fill="white"/>

  <!-- Simple flower for coloring -->
  <g stroke="black" stroke-width="4" fill="none">
    <!-- Flower center -->
    <circle cx="512" cy="512" r="60"/>

    <!-- Petals -->
    <ellipse cx="512" cy="400" rx="40" ry="80"/>
    <ellipse cx="624" cy="512" rx="80" ry="40"/>
    <ellipse cx="512" cy="624" rx="40" ry="80"/>
    <ellipse cx="400" cy="512" rx="80" ry="40"/>

    <!-- Diagonal petals -->
    <ellipse cx="580" cy="444" rx="60" ry="60" transform="rotate(45 580 444)"/>
    <ellipse cx="580" cy="580" rx="60" ry="60" transform="rotate(45 580 580)"/>
    <ellipse cx="444" cy="580" rx="60" ry="60" transform="rotate(45 444 580)"/>
    <ellipse cx="444" cy="444" rx="60" ry="60" transform="rotate(45 444 444)"/>

    <!-- Stem -->
    <line x1="512" y1="572" x2="512" y2="800" stroke-width="8"/>

    <!-- Leaves -->
    <path d="M 480 700 Q 420 680 430 740 Q 440 780 480 760 Z"/>
    <path d="M 544 700 Q 604 680 594 740 Q 584 780 544 760 Z"/>
  </g>

  <!-- Title -->
  <text x="512" y="900" text-anchor="middle" font-family="Arial" font-size="32" fill="black">
    Coloring Page
  </text>
</svg>"""

    async def convert_png_to_svg_fallback(self, image_data: bytes) -> str:
        """Fallback method to embed PNG in SVG when vectorization fails"""
        try:
            import base64

            # Convert image to base64
            base64_data = base64.b64encode(image_data).decode()

            # Determine image dimensions
            image = Image.open(BytesIO(image_data))
            width, height = image.size

            # Create SVG with embedded PNG
            svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="100%" height="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="100%" height="100%" fill="white"/>
  <image x="0" y="0" width="{width}" height="{height}" href="data:image/png;base64,{base64_data}"/>
</svg>"""

            return svg_content

        except Exception as e:
            logger.error(f"Error creating PNG fallback SVG: {str(e)}")
            return await self._create_fallback_svg()
