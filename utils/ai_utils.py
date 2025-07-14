import asyncio
from openai import AsyncOpenAI
from constants import OPENROUTER_API_KEY, CHECK_MODEL
from utils.utils import get_sys_prompt

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


async def get_response(prompt, model, history=None):
    if history:
        messages = [
            {"role": "system", "content": get_sys_prompt()},
            *history,
            {"role": "user", "content": prompt},
        ]
    else:
        messages = [
            {"role": "system", "content": get_sys_prompt()},
            {"role": "user", "content": prompt},
        ]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as e:
        print(f"Error getting response: {e}")
        return "Nya! I couldn't come up with a response, nya! (｡•́︿•̀｡)"

    if len(response.choices) != 0 and response.choices[0].message.content:
        response_text = response.choices[0].message.content.strip()
    else:
        response_text = "Nya! I couldn't come up with a response, nya! (｡•́︿•̀｡)"

    return response_text


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
