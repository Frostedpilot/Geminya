"""Utility functions for the Geminya bot."""

from typing import List


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
            # If it exceeds max_len, split at the last chunk ending and add to shards
            if current_chunk:
                shards.append(current_chunk.strip())

            # After added, assign the chunk to current_chunk (may be > max_len) *a
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


def convert_tool_format(tool):
    converted_tool = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": tool.inputSchema["properties"],
                "required": tool.inputSchema["required"],
            },
        },
    }
    return converted_tool
