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
    with open(lang_file, "r") as file:
        lang_data = json.load(file)

    return lang_data
