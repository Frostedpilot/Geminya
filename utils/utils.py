"""Utility functions for the Geminya bot."""

from typing import List
import warnings

# Issue deprecation warning for direct imports
warnings.warn(
    "Direct imports from utils.utils are deprecated. Use the service layer instead.",
    DeprecationWarning,
    stacklevel=2,
)


# Keep existing functions for backward compatibility
def get_sys_prompt() -> str:
    """Get system prompt from language file.

    DEPRECATED: Use ai_service._get_personality_prompt() instead.
    """
    try:
        from utils.config_load import load_language_file

        lang_data = load_language_file()
        personality = lang_data.get("personality", {})
        return personality.get(
            "Geminya_Exp", "You are Geminya, a helpful AI assistant."
        )
    except Exception:
        return "You are Geminya, a helpful AI assistant."


def split_response(response: str, max_len: int = 1999) -> List[str]:
    """Split a response into chunks that fit Discord's message limit.

    Args:
        response: The response text to split
        max_len: Maximum length per chunk

    Returns:
        List[str]: List of response chunks
    """
    if not response or not response.strip():
        return []

    # Default sentence endings
    sentence_endings = (".", "!", "?")

    chunks = response.split("\n")
    shards = []
    current_chunk = ""

    for chunk in chunks:
        tmp = current_chunk + chunk + "\n"

        # First, check the combined chunk length
        if len(tmp) > max_len:
            # If it exceeds max_len, split at the last sentence ending and add to shards
            if current_chunk:
                shards.append(current_chunk.strip())

            # After added, assign the chunk to current_chunk (may be > max_len)
            current_chunk = chunk + "\n"
        else:
            # If it fits, assign it to current_chunk (always less than max_len)
            current_chunk = tmp

        # Need to solve the problem of current_chunk being longer than max_len
        if len(current_chunk) > max_len:
            # Should only happen with flow after *a, meaning chunk is longer than max_len

            # Split current_chunk into smaller chunks by searching backwards for sentence endings
            while len(current_chunk) > max_len:
                current_shard = current_chunk[:max_len]
                for i in range(max_len - 1, -1, -1):
                    if current_chunk[i] in sentence_endings:
                        current_shard = current_chunk[: i + 1]
                        break
                if current_shard:
                    shards.append(current_shard)
                    current_chunk = current_chunk[len(current_shard) :]

    # Add any remaining current_chunk to shards
    if current_chunk:
        shards.append(current_chunk.strip())

    return [shard for shard in shards if shard.strip()]
