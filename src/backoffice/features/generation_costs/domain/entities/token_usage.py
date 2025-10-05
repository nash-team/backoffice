"""Token usage entity for generation costs bounded context."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class TokenUsage:
    """Single token usage record for API call tracking.

    Represents a single API call's token consumption and cost within the
    generation costs bounded context. This is specific to cost tracking
    and may differ from token representations in other contexts.

    Attributes:
        model: Model ID used for the API call
        prompt_tokens: Number of input tokens consumed
        completion_tokens: Number of output tokens generated
        cost: Calculated cost in USD (Decimal for precision)
    """

    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens consumed.

        Returns:
            Sum of prompt and completion tokens
        """
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ImageUsage:
    """Single image usage record for vision/generation models.

    Represents image-based API calls where billing is per image rather
    than per token. Specific to the generation costs bounded context.

    Attributes:
        model: Model ID used for the API call
        input_images: Number of images sent as input (for vision models)
        output_images: Number of images generated as output
        cost: Calculated cost in USD (Decimal for precision)
    """

    model: str
    input_images: int
    output_images: int
    cost: Decimal

    @property
    def total_images(self) -> int:
        """Calculate total images processed.

        Returns:
            Sum of input and output images
        """
        return self.input_images + self.output_images
