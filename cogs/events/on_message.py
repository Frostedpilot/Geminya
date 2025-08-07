import discord
import re
from discord.ext import commands

from cogs.base_event import BaseEventHandler
from services.container import ServiceContainer
from utils.utils import split_response


class OnMessage(BaseEventHandler):
    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)
        self.message_logger = services.get_message_logger()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages for AI responses."""

        # Skip this own bot messages (keep other bots messages)
        if message.author.id == self.bot.user.id:
            return

        # Skip DMs for now (could be extended later)
        if not message.guild:
            return

        # Skip if in restricted servers mode and this server isn't allowed
        if (
            self.config.active_servers
            and str(message.guild.id) not in self.config.active_servers
        ):
            return

        self.message_logger.info(
            f"Processing message from {message.author} in {message.guild}: '{message.content}'"
        )

        try:
            # Process the message content (resolve mentions)
            processed_content = self._process_message_content(message)

            # Add to conversation history
            self._add_to_history(message, processed_content)

            # Determine if bot should respond
            should_respond = await self._should_respond(message, processed_content)

            if should_respond:
                await self._generate_and_send_response(message)

        except Exception as e:
            self.logger.error(f"Error processing message from {message.author}: {e}")
            self.services.get_error_logger().error(
                f"Message processing error: {e}", exc_info=True
            )

    def _process_message_content(self, message: discord.Message) -> str:
        """Process message content to resolve mentions and clean up text.

        Args:
            message: Discord message to process

        Returns:
            str: Processed message content
        """
        content = message.content

        # Replace user mentions with readable names
        for mention in message.mentions:
            try:
                # Try to get nickname first, fall back to username
                display_name = getattr(mention, "nick", None) or mention.name
                content = content.replace(f"<@{mention.id}>", f"@{display_name}")
                content = content.replace(f"<@!{mention.id}>", f"@{display_name}")
            except Exception as e:
                self.logger.warning(f"Error processing mention for {mention}: {e}")
                content = content.replace(f"<@{mention.id}>", f"@{mention.name}")
                content = content.replace(f"<@!{mention.id}>", f"@{mention.name}")

        return content.strip()

    def _add_to_history(self, message: discord.Message, processed_content: str) -> None:
        """Add message to conversation history.

        Args:
            message: Discord message
            processed_content: Processed message content
        """
        author = message.author
        nick = getattr(author, "nick", None)

        # Add to state manager
        self.state_manager.add_message(
            channel_id=message.channel.id,
            author_id=author.id,
            author_name=f"{author.name}#{author.discriminator}",
            nick=nick,
            content=processed_content,
        )

    async def _should_respond(self, message: discord.Message, content: str) -> bool:
        """Determine if the bot should respond to this message.

        Args:
            message: Discord message
            content: Processed message content

        Returns:
            bool: True if bot should respond
        """
        # Direct mentions always get a response
        if self.bot.user and self.bot.user.mentioned_in(message):
            self.logger.debug(f"Responding to direct mention from {message.author}")
            return True

        # Return here for now TODO: Implement more complex logic based on bot nicknames
        return False

        # Check for bot name in message (case insensitive)
        if "geminya" in content.lower():
            # Use AI to determine if this warrants a response
            should_respond = await self._check_if_should_respond(message)
            if should_respond:
                self.logger.debug(f"AI determined response needed for {message.author}")
                return True

        return False

    async def _check_if_should_respond(self, message: discord.Message) -> bool:
        """Use AI to check if bot should respond to a message mentioning its name.

        Args:
            message: Discord message to check

        Returns:
            bool: True if should respond
        """
        try:
            # Build context for the check
            history = self.state_manager.get_history(message.channel.id)

            check_prompt = (
                "In the following conversation, is the user asking for a response from Geminya? "
                "Respond with 'yes' or 'no'.\n\n"
            )

            # Add recent history for context
            for entry in history[-3:]:  # Last 3 messages for context
                nick_part = f" (aka {entry['nick']})" if entry["nick"] else ""
                check_prompt += (
                    f"From: {entry['name']}{nick_part}\n{entry['content']}\n\n"
                )

            # Get AI response
            response = await self.llm_manager.get_response(
                message=check_prompt,
                server_id=str(message.guild.id) if message.guild else "DM",
                is_check=True,  # Indicate this is a check
            )

            return "yes" in response.lower()

        except Exception as e:
            self.logger.error(f"Error in response check: {e}")
            # Default to not responding if check fails
            return False

    async def _generate_and_send_response(self, message: discord.Message) -> None:
        """Generate and send AI response to the message.

        Args:
            message: Discord message to respond to
        """
        server_id = str(message.guild.id) if message.guild else "DM"

        try:
            async with message.channel.typing():
                # Generate response using LLM Manager
                response = await self.llm_manager.get_response(
                    message=message,
                    server_id=server_id,
                )

                if not response:
                    self.logger.warning(
                        f"Empty response generated for {message.author}"
                    )
                    return

                # Add bot's response to history
                bot_user = self.bot.user
                if bot_user:
                    self.state_manager.add_message(
                        channel_id=message.channel.id,
                        author_id=bot_user.id,
                        author_name=bot_user.name,
                        nick=getattr(bot_user, "nick", None),
                        content=response,
                    )

                # Split response if too long
                chunks = split_response(response, self.config.max_response_length)

                self.logger.info(
                    f"Sending response to {message.author} in {len(chunks)} chunk(s)"
                )

                # Send response chunks
                for chunk in chunks:
                    if chunk.strip():
                        await message.channel.send(chunk)

                self.message_logger.info(
                    f"Response sent to {message.author} ({len(response)} chars, {len(chunks)} chunks)"
                )

        except Exception as e:
            self.logger.error(f"Error generating response for {message.author}: {e}")

            # Send fallback message
            try:
                await message.channel.send(
                    "Nya! Something went wrong while generating my response. Please try again later! (´･ω･`)"
                )
            except Exception as send_error:
                self.logger.error(f"Failed to send error message: {send_error}")


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(OnMessage(bot, bot.services))
