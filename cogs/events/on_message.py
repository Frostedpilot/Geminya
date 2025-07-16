import discord
import logging
import re
from discord.ext import commands
from constants import MAX_HISTORY_LENGTH

from utils.ai_utils import get_response, get_check_response
from utils.utils import split_response, get_prompt


class OnMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.max_history_length = MAX_HISTORY_LENGTH

    async def get_response(self, message, logger):
        prompt = message.content

        for mention in message.mentions:
            try:
                mention_nick = mention.nick
            except AttributeError:
                logger.error(f"AttributeError: {mention} has no attribute 'nick'")
                mention_nick = None
            except Exception as e:
                logger.error(f"Error getting nick for {mention}: {e}")
                mention_nick = None

            prompt = prompt.replace(
                f"<@{mention.id}>", f"@{mention_nick if mention_nick else mention.name}"
            )

        print(f"Nya! Got a prompt from {message.author}: '{prompt}'")

        prompt = get_prompt(prompt)

        try:
            nick = message.author.nick
        except AttributeError:
            logger.error(f"AttributeError: {message.author} has no attribute 'nick'")
            nick = None
        except Exception as e:
            logger.error(f"Error getting nick for {message.author}: {e}")
            nick = None

        prompt = f"From: {message.author.name}#{message.author.discriminator} {'(aka ' + nick + ')' if nick else ''}\n{prompt}"

        server_id = str(message.guild.id) if message.guild else "DM"

        async with message.channel.typing():
            response = await get_response(
                prompt, self.bot.model[server_id], self.bot.history[message.channel.id]
            )

            if response:
                self.bot.history[message.channel.id].append(
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
        logging.basicConfig(filename="logs/on_message.log", level=logging.INFO)
        logger = logging.getLogger("geminya.on_message")

        logger.info(f"Received message: {message.content} from {message.author}")
        author = message.author
        try:
            nick = author.nick
        except AttributeError:
            logger.error(f"AttributeError: {author} has no attribute 'nick'")
            nick = None
        except Exception as e:
            logger.error(f"Error getting nick for {author}: {e}")
            nick = None
        last_message = (
            self.bot.history[message.channel.id][-1]
            if message.channel.id in self.bot.history
            and self.bot.history[message.channel.id]
            else None
        )
        if (
            last_message
            and last_message["role"] == "user"
            and re.search(
                rf"From: {re.escape(author.name)}#{re.escape(author.discriminator)}",
                last_message["content"],
                re.IGNORECASE,
            )
        ):
            # Same author as last message, append to last message
            self.bot.history[message.channel.id][-1][
                "content"
            ] += f"\n{message.content}"
            logger.info(
                f"Appending to last message from {author.name}#{author.discriminator}"
            )
        else:
            self.bot.history[message.channel.id].append(
                {
                    "role": "user",
                    "content": f"From: {message.author.name}#{message.author.discriminator} {'(aka ' + nick+')' if nick else ''}\n{message.content}",
                }
            )
            logger.info(f"Adding new message from {author.name}#{author.discriminator}")

        if len(self.bot.history[message.channel.id]) > self.max_history_length:
            self.bot.history[message.channel.id] = self.bot.history[message.channel.id][
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
            await self.get_response(message, logger=logger)

        elif flag == "check":
            print(
                f"Nya! Got a prompt from {message.author}, checking if Geminya should respond..."
            )
            check_prompt = "In the following message, is the user asking for a response from Geminya? Respond with 'yes' or 'no'.\n\n"

            for line in self.bot.history[message.channel.id]:
                check_prompt += f"{line["content"]}\n"

            check_result = await get_check_response(check_prompt)

            if "yes" in check_result:
                print("Nya! User is asking for a response, generating...")
                await self.get_response(message, logger=logger)


async def setup(bot):
    await bot.add_cog(OnMessage(bot))
