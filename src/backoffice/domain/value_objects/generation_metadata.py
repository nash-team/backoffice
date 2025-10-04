"""Generation metadata value object (DDD)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class GenerationMetadata:
    """Métadonnées techniques de génération d'un ebook (Value Object).

    Immutable value object regroupant toutes les informations techniques
    liées à la génération d'un ebook (coûts, tokens, provider, durée, etc.).

    Frozen=True car c'est un Value Object immuable.
    """

    # Provider et modèle utilisés
    provider: str
    model: str

    # Métriques de coût
    cost: Decimal
    prompt_tokens: int
    completion_tokens: int

    # Performance
    duration_seconds: float

    # Timestamp
    generated_at: datetime

    @property
    def total_tokens(self) -> int:
        """Total de tokens utilisés."""
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_per_token(self) -> Decimal:
        """Coût par token (pour analyse)."""
        if self.total_tokens == 0:
            return Decimal("0")
        return self.cost / self.total_tokens

    def __str__(self) -> str:
        """Représentation lisible."""
        return (
            f"GenerationMetadata({self.provider}/{self.model}, "
            f"${self.cost:.4f}, {self.duration_seconds:.1f}s)"
        )
