from constants import SENTENCE_ENDINGS
from utils.config_load import load_language_file
import discord

lang_data = load_language_file()


def get_sys_prompt():
    personality = lang_data.get("personality")
    sys_prompt = personality.get("Geminya_Exp")
    return sys_prompt


def split_response(response: str, max_len=1999) -> list[str]:
    chunks = response.split("\n")
    shards = []
    current_chunk = ""

    for chunk in chunks:
        tmp = current_chunk + chunk + "\n"

        # First, check the combined chunk length
        if len(tmp) > max_len:
            # If it exceeds max_len, split at the last sentence ending and add to shards, this requires current_chunk to be less than max_len
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

            # Split current_chunk into smaller chunks by searching backwards for sentence endings from the max_len point
            while len(current_chunk) > max_len:
                current_shard = current_chunk[:max_len]
                for i in range(max_len - 1, -1, -1):
                    if current_chunk[i] in SENTENCE_ENDINGS:
                        current_shard = current_chunk[: i + 1]
                        break
                if current_shard:
                    shards.append(current_shard)
                    current_chunk = current_chunk[len(current_shard) :]

    # Add any remaining current_chunk to shards
    if current_chunk:
        shards.append(current_chunk.strip())

    return shards
