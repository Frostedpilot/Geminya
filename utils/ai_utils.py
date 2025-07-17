import asyncio
import discord
from openai import AsyncOpenAI
from constants import OPENROUTER_API_KEY, CHECK_MODEL
from utils.utils import get_sys_prompt

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


async def get_response(message: discord.Message, model, history=None, lore_book=None):
    assert isinstance(
        message, discord.Message
    ), "message must be a discord.Message instance"
    prompt = build_prompt(message, history, lore_book)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        if len(response.choices) == 0 or not response.choices[0].message.content:
            print("No response from model, returning empty string.")
            return "Nya! Something went wrong, please try again later."
        response_text = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error getting response from model {model}: {e}")
        response_text = "Nya! Something went wrong, please try again later."

    return response_text


def build_prompt(message: discord.Message, history=None, lore_book=None):
    assert isinstance(
        message, discord.Message
    ), "message must be a discord.Message instance"
    # Prepare the main prompt
    author = message.author
    author_name = author.name

    # The personality system prompt
    personality_prompt = get_sys_prompt()

    # Prepare the history
    history_prompt = ""
    if history:
        for entry in history:
            line = f"From: {entry['name']} {'(aka ' + entry['nick'] + ')' if entry['nick'] else ''}\n{entry['content']}\n\n"
            history_prompt += line
    history_prompt = history_prompt.strip()

    # Prepare the lore book
    lore_prompt = ""
    if lore_book:
        word_list = set(message.content.split())

        overlap = word_list.intersection(lore_book["quick_trigger_list"])
        if overlap:
            lore_list = set()
            for word in overlap:
                if word in lore_book["trigger_words"]:
                    lore_list.update(lore_book["trigger_words"][word])

            for lore in lore_list:
                if lore in lore_book["example_responses"]:
                    example = lore_book["example_responses"][lore]
                    lore_prompt += f"\n\n{example}"

    # Get all authors in the history
    authors = set()
    authors.add(author_name)
    if history:
        for entry in history:
            authors.add(entry["name"])

    # Now combine everything into the final response text
    final_prompt = f"""
Write Geminya's next reply in a fictional chat between Sakana and {message.author.name}.
{personality_prompt}
{lore_prompt}
[Start a new group chat. Group members: Geminya, {', '.join(authors)}]
{history_prompt}
[Write the next reply only as Geminya.]
"""

    return final_prompt


async def get_check_response(prompt: str):
    while True:
        n = 1

        try:
            response = await client.chat.completions.create(
                model=CHECK_MODEL,
                messages=[
                    {"role": "system", "content": get_sys_prompt()},
                    {"role": "user", "content": prompt},
                ],
            )

            if len(response.choices) == 0 or not response.choices[0].message.content:
                print("No response from check model, retrying...")
                await asyncio.sleep(2**n)
                n += 1
                continue

            return response.choices[0].message.content.strip().lower()

        except Exception as e:
            print(f"Error getting check response: {e}")

            # Back off exponentially
            await asyncio.sleep(2**n)
            n += 1

            if n > 5:
                return "no"
