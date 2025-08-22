"""Utility functions for the Geminya bot."""

from typing import List, Tuple, Optional
import re
import aiohttp
import asyncio
import io
import os
from urllib.parse import urlparse


def split_response(response: str, max_len: int = 1999) -> Tuple[List[str], List[str]]:
    """Split a response into chunks that fit Discord's message limit.

    Args:
        response: The response text to split
        max_len: Maximum length per chunk

    Returns:
        List[str]: List of response chunks
    """
    if not response or not response.strip():
        return [], []

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

    links = extract_image_links(response)

    return [shard for shard in shards if shard.strip()], links


def extract_image_links(response: str) -> List[str]:
    """Extract image links from a response string.
    supported image types: jpg, jpeg, png, gif, webp, bmp

    Args:
        response: The response text to extract image links from.

    Returns:
        List[str]: A list of extracted image links.
    """
    image_links_pttn = r"https?://\S+\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?\S*)?"
    lst = re.findall(image_links_pttn, response, re.IGNORECASE)

    out = []

    for match in lst:
        res = match.strip()
        if res[-1] == ")":
            res = res[
                :-1
            ]  # Remove trailing parenthesis if present. This is due to the regex pattern limitation.
        out.append(res)

    return out


def convert_tool_format(tool):
    """Convert MCP tool to OpenAI function format with error handling."""
    try:
        # Extract properties and required fields safely
        properties = {}
        required = []

        if hasattr(tool, "inputSchema") and tool.inputSchema:
            if "properties" in tool.inputSchema:
                properties = tool.inputSchema["properties"]
            if "required" in tool.inputSchema:
                required_field = tool.inputSchema["required"]
                # Handle both list and string cases
                if isinstance(required_field, list):
                    required = required_field
                elif isinstance(required_field, str):
                    required = [required_field]
                else:
                    required = []

        converted_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
        return converted_tool

    except Exception:
        # Fallback to basic tool format
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": getattr(tool, "description", ""),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }


async def download_image_from_url(
    url: str, max_size: int = 8 * 1024 * 1024
) -> Optional[Tuple[io.BytesIO, str]]:
    """Download an image from URL and return it as BytesIO with filename.

    Args:
        url: The URL of the image to download
        max_size: Maximum file size in bytes (default 8MB for Discord limit)

    Returns:
        Tuple of (BytesIO buffer, filename) if successful, None if failed
    """
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if not content_type.startswith("image/"):
                    return None

                # Check content length if provided
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_size:
                    return None

                # Read the content
                content = await response.read()
                if len(content) > max_size:
                    return None

                # Generate filename from URL
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                if not filename or "." not in filename:
                    # Fallback filename based on content type
                    ext_map = {
                        "image/jpeg": ".jpg",
                        "image/png": ".png",
                        "image/gif": ".gif",
                        "image/webp": ".webp",
                        "image/bmp": ".bmp",
                    }
                    ext = ext_map.get(content_type, ".jpg")
                    filename = f"image{ext}"

                # Create BytesIO buffer
                buffer = io.BytesIO(content)
                buffer.seek(0)

                return buffer, filename

    except Exception:
        return None


async def download_images_from_urls(
    urls: List[str], max_images: int = 10
) -> List[Tuple[io.BytesIO, str]]:
    """Download multiple images from URLs concurrently.

    Args:
        urls: List of image URLs to download
        max_images: Maximum number of images to download

    Returns:
        List of (BytesIO buffer, filename) tuples for successfully downloaded images
    """
    if not urls:
        return []

    # Limit the number of images
    urls = urls[:max_images]

    # Download images concurrently
    tasks = [download_image_from_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failed downloads and exceptions
    downloaded_images = []
    for result in results:
        if isinstance(result, tuple) and result is not None:
            downloaded_images.append(result)

    return downloaded_images
