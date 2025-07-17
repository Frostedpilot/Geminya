import yaml
import json
import os

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

language = config.get("language", "en")
lang_dir = "lang"
lang_file = os.path.join(lang_dir, f"{language}.json")

if not os.path.exists(lang_file):
    raise FileNotFoundError(f"Language file '{lang_file}' does not exist.")


def load_language_file():
    with open(lang_file, "r", encoding="utf-8") as file:
        lang_data = json.load(file)

    return lang_data


def lore_book_load(bot):
    lang_data = load_language_file()
    lore_book = lang_data.get("lorebook", {})

    if not lore_book:
        raise ValueError("Lore book data is missing or empty in the language file.")

    trigger_words = {}
    example_responses = {}
    for key, value in lore_book.items():
        words = value.get("keywords", [])
        for word in words:
            if word not in trigger_words:
                trigger_words[word] = []
            trigger_words[word].append(key)

        example_responses[
            key
        ] = f"""
        {"{user}"}: {value.get("example_user")}
        Geminya: {value.get("example")}
        """

    bot.lore_book = {
        "trigger_words": trigger_words,
        "example_responses": example_responses,
        "quick_trigger_list": set(trigger_words.keys()),
    }
