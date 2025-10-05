"""Utility to detect provider from model name."""


def detect_provider_from_model(model_name: str) -> str:
    """Detect provider from model name.

    Args:
        model_name: Model identifier (e.g., "gemini-2.5-flash", "black-forest-labs/flux-schnell")

    Returns:
        Provider name ("gemini", "openrouter", "local", or "unknown")

    Examples:
        >>> detect_provider_from_model("gemini-2.5-flash")
        'gemini'
        >>> detect_provider_from_model("google/gemini-2.0-flash-001")
        'openrouter'
    """
    model_lower = model_name.lower()

    # Priority order matters!
    if "gemini" in model_lower and "openrouter" not in model_lower and "google/" not in model_lower:
        return "gemini"
    elif "openrouter" in model_lower or "google/" in model_lower:
        return "openrouter"
    else:
        return "unknown"
