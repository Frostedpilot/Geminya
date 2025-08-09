"""Utility functions for model management."""

from typing import Dict, Optional, List, Tuple
from config.models import MODEL_INFOS, ModelInfo


def get_model_name_by_id(model_id: str) -> Optional[str]:
    """Get the display name of a model by its ID.

    Args:
        model_id: The model ID to look up

    Returns:
        The display name of the model, or None if not found
    """
    for display_name, model_info in MODEL_INFOS.items():
        if model_info.id == model_id:
            return display_name
    return None


def get_models_by_provider(provider: str) -> Dict[str, ModelInfo]:
    """Get all models for a specific provider.

    Args:
        provider: The provider name

    Returns:
        Dictionary of display_name -> ModelInfo for the provider
    """
    return {
        display_name: model_info
        for display_name, model_info in MODEL_INFOS.items()
        if model_info.provider == provider
    }


def get_all_providers() -> List[str]:
    """Get list of all available providers.

    Returns:
        List of provider names
    """
    providers = set()
    for model_info in MODEL_INFOS.values():
        providers.add(model_info.provider)
    return sorted(list(providers))


def get_provider_stats() -> List[Tuple[str, int, int]]:
    """Get statistics for each provider.

    Returns:
        List of tuples: (provider_name, model_count, tools_supported_count)
    """
    provider_stats = {}

    for model_info in MODEL_INFOS.values():
        provider = model_info.provider
        if provider not in provider_stats:
            provider_stats[provider] = {"total": 0, "tools": 0}

        provider_stats[provider]["total"] += 1
        if model_info.supports_tools:
            provider_stats[provider]["tools"] += 1

    return [
        (provider, stats["total"], stats["tools"])
        for provider, stats in sorted(provider_stats.items())
    ]
