"""Usage metrics value object for provider-agnostic cost tracking."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class UsageMetrics:
    """Metrics d'usage pour un appel à un provider (Value Object).

    Provider-agnostic: chaque provider extrait ses propres métriques
    et les retourne dans ce format unifié.

    Frozen=True car c'est un Value Object immuable.
    """

    # Model utilisé (provider-specific ID)
    model: str

    # Tokens (0 pour providers sans tokens, ex: image-only)
    prompt_tokens: int
    completion_tokens: int

    # Coût réel facturé par le provider (includes all fees)
    cost: Decimal

    @property
    def total_tokens(self) -> int:
        """Total de tokens utilisés."""
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_per_token(self) -> Decimal:
        """Coût par token (0 si pas de tokens)."""
        if self.total_tokens == 0:
            return Decimal("0")
        return self.cost / self.total_tokens

    def __str__(self) -> str:
        """Représentation lisible."""
        return f"UsageMetrics({self.model}, ${self.cost:.6f}, {self.total_tokens} tokens)"
