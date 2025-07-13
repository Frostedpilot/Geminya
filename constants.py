import json

with open("secrets.json", "r") as f:
    secrets = json.load(f)

DISCORD_TOKEN = secrets.get("DISCORD_BOT_TOKEN")
OPENROUTER_API_KEY = secrets.get("OPENROUTER_API_KEY")
MODEL = "deepseek/deepseek-chat-v3-0324:free"
CHECK_MODEL = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"

SENTENCE_ENDINGS = (".", "!", "?")
MAX_HISTORY_LENGTH = 5

ACTIVE_SERVERS = ("1393258849867272325", "700261922259599420")
