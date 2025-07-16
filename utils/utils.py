from constants import SENTENCE_ENDINGS
from utils.config_load import load_language_file
import discord

lang_data = load_language_file()


def get_sys_prompt():
    personality = lang_data.get("personality")
    sys_prompt = personality.get("Geminya_Exp")
    return sys_prompt


def get_prompt(prompt):
    sys_prompt = lang_data.get("system_prompt")
    return sys_prompt + "\n" + prompt


def split_response(response: str, max_len=1999) -> list[str]:
    chunks = response.split("\n")
    shards = []

    for chunk in chunks:
        if len(chunk) < max_len:
            shards.append(chunk)
            continue

        # Search backwards from the character limit until we found a sentence ending marker
        while len(chunk) > max_len:
            current_shard = chunk[:max_len]
            for i in range(max_len - 1, -1, -1):
                if chunk[i] in SENTENCE_ENDINGS:
                    current_shard = chunk[: i + 1]
                    break
            if current_shard:
                shards.append(current_shard)
                chunk = chunk[len(current_shard) :]

        if chunk:
            shards.append(chunk)

    return shards
