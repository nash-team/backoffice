"""Utility to detect provider from model name."""


def detect_provider_from_model(model_name: str) -> str:
    """Detect provider from model name.

    Args:
        model_name: Model identifier (e.g., "gemini-2.5-flash", "black-forest-labs/flux-schnell")

    Returns:
        Provider name ("gemini", "replicate", "openrouter", "local", or "unknown")

    Examples:
        >>> detect_provider_from_model("gemini-2.5-flash")
        'gemini'
        >>> detect_provider_from_model("black-forest-labs/flux-schnell")
        'replicate'
        >>> detect_provider_from_model("google/gemini-2.0-flash-001")
        'openrouter'
        >>> detect_provider_from_model("sdxl-turbo")
        'local'
    """
    model_lower = model_name.lower()

    # Priority order matters!
    if "gemini" in model_lower and "openrouter" not in model_lower and "google/" not in model_lower:
        return "gemini"
    elif "flux" in model_lower or "replicate" in model_lower or "black-forest" in model_lower:
        return "replicate"
    elif "openrouter" in model_lower or "google/" in model_lower:
        return "openrouter"
    elif "sdxl" in model_lower or "stable-diffusion" in model_lower:
        return "local"
    else:
        return "unknown"
