"""Fake implementations for testing image generation and vectorization components."""

from backoffice.domain.ports.image_generation_port import ImageGenerationPort
from backoffice.domain.ports.vectorization_port import VectorizationPort


class FakeOpenAIService:
    """Fake OpenAI service for testing."""

    def __init__(self, available: bool = True):
        self.client = FakeOpenAIClient() if available else None


class FakeOpenAIClient:
    """Fake OpenAI client for testing."""

    def __init__(self):
        self.images = FakeImagesAPI()


class FakeImagesAPI:
    """Fake images API for testing."""

    async def generate(
        self, model: str, prompt: str, size: str, quality: str, n: int, response_format: str = "url"
    ) -> "FakeImageResponse":
        return FakeImageResponse()


class FakeImageResponse:
    """Fake image response for testing."""

    def __init__(self):
        self.data = [FakeImageData()]


class FakeImageData:
    """Fake image data for testing."""

    def __init__(self):
        self.url = "https://fake-openai-image.example.com/test.png"
        # Provide base64 encoded fake image data (simple PNG header + "fake_image_data")
        import base64

        self.b64_json = base64.b64encode(b"fake_image_data").decode("utf-8")


class FakeHTTPResponse:
    """Fake HTTP response for testing."""

    def __init__(self, content: bytes = b"fake_image_data"):
        self.content = content

    def raise_for_status(self):
        pass


class FakeHTTPClient:
    """Fake HTTP client for testing."""

    def __init__(self):
        self.get_calls: list[str] = []
        self._response = FakeHTTPResponse()

    async def get(self, url: str, headers=None, follow_redirects=None) -> FakeHTTPResponse:
        self.get_calls.append(url)
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeImageGenerator(ImageGenerationPort):
    """Fake image generator for testing."""

    def __init__(self, available: bool = True):
        self._available = available
        self.generate_image_from_url_calls: list[tuple[str, str | None]] = []
        self.generate_image_from_prompt_calls: list[tuple[str, str]] = []
        self.generate_coloring_page_from_description_calls: list[str] = []

    def is_available(self) -> bool:
        return self._available

    async def generate_image_from_url(self, image_url: str, prompt: str | None = None) -> bytes:
        self.generate_image_from_url_calls.append((image_url, prompt))
        return b"fake_image_from_url"

    async def generate_image_from_prompt(self, prompt: str, size: str = "1024x1024") -> bytes:
        self.generate_image_from_prompt_calls.append((prompt, size))
        return b"fake_image_from_prompt"

    async def generate_coloring_page_from_description(self, description: str) -> bytes:
        self.generate_coloring_page_from_description_calls.append(description)
        return b"fake_coloring_page"


class FakeVectorizer(VectorizationPort):
    """Fake vectorizer for testing."""

    def __init__(self, available: bool = True):
        self._available = available
        self.vectorize_image_calls: list[bytes] = []
        self.optimize_for_coloring_calls: list[str] = []

    def is_available(self) -> bool:
        return self._available

    async def vectorize_image(self, image_data: bytes) -> str:
        self.vectorize_image_calls.append(image_data)
        return "<svg>fake_vectorized_content</svg>"

    async def optimize_for_coloring(self, svg_content: str) -> str:
        self.optimize_for_coloring_calls.append(svg_content)
        return "<svg>fake_optimized_svg</svg>"


class FakeFailingVectorizer(VectorizationPort):
    """Fake vectorizer that always fails for testing error scenarios."""

    def is_available(self) -> bool:
        return True

    async def vectorize_image(self, image_data: bytes) -> str:
        raise Exception("Fake vectorization failure")

    async def optimize_for_coloring(self, svg_content: str) -> str:
        raise Exception("Fake optimization failure")


class FakeFailingImageGenerator(ImageGenerationPort):
    """Fake image generator that always fails for testing error scenarios."""

    def is_available(self) -> bool:
        return True

    async def generate_image_from_url(self, image_url: str, prompt: str | None = None) -> bytes:
        raise Exception("Fake image generation failure")

    async def generate_image_from_prompt(self, prompt: str, size: str = "1024x1024") -> bytes:
        raise Exception("Fake prompt generation failure")

    async def generate_coloring_page_from_description(self, description: str) -> bytes:
        raise Exception("Fake coloring page failure")


class FakeUnavailableImageGenerator(ImageGenerationPort):
    """Fake image generator that is unavailable for testing fallback scenarios."""

    def is_available(self) -> bool:
        return False

    async def generate_image_from_url(self, image_url: str, prompt: str | None = None) -> bytes:
        return b"fallback_image_data"

    async def generate_image_from_prompt(self, prompt: str, size: str = "1024x1024") -> bytes:
        return b"fallback_image_data"

    async def generate_coloring_page_from_description(self, description: str) -> bytes:
        return b"fallback_image_data"
