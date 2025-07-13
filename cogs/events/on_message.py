import discord
from discord.ext import commands
from constants import MAX_HISTORY_LENGTH

from utils.ai_utils import get_response, get_check_response
from utils.utils import split_response, get_prompt


class OnMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.history = {}
        self.max_history_length = MAX_HISTORY_LENGTH
        for channel in bot.get_all_channels():
            if isinstance(channel, discord.TextChannel):
                self.history[channel.id] = []

    async def get_response(self, message):
        prompt = message.content.replace(f"<@{self.bot.user.id}>", "Geminya").strip()

        print(f"Nya! Got a prompt from {message.author}: '{prompt}'")

        prompt = get_prompt(prompt)

        response = await get_response(prompt, self.history[message.channel.id])

        if response:
            self.history[message.channel.id].append(
                {
                    "role": "assistant",
                    "content": f"Geminya: {response}",
                }
            )

            chunks = split_response(response)
            for chunk in chunks:
                if chunk:
                    await message.channel.send(chunk)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        self.history[message.channel.id].append(
            {
                "role": "user",
                "content": f"From: {message.author.name}#{message.author.discriminator} ({message.author.id})\n{message.content}",
            }
        )
        if len(self.history[message.channel.id]) > self.max_history_length:
            self.history[message.channel.id] = self.history[message.channel.id][
                -self.max_history_length :
            ]

        if message.author == self.bot.user:
            return

        flag = "None"

        if "geminya" in message.content.lower():
            flag = "check"

        if self.bot.user.mentioned_in(message):
            flag = "mention"

        if flag == "mention":
            await self.get_response(message)

        elif flag == "check":
            print(
                f"Nya! Got a prompt from {message.author}, checking if Geminya should respond..."
            )
            check_prompt = "In the following message, is the user asking for a response from Geminya? Respond with 'yes' or 'no'.\n\n"

            for line in self.history[message.channel.id]:
                check_prompt += f"{line["content"]}\n"

            check_result = await get_check_response(check_prompt)

            if "yes" in check_result:
                print("Nya! User is asking for a response, generating...")
                await self.get_response(message)


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
