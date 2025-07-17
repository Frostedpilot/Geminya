"""Centralized error handling service for the Geminya bot."""

import logging
import traceback
from typing import Optional, Any
from discord.ext import commands
import discord

from config import Config


class ErrorHandler:
    """Centralized error handling service."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.error_count = 0

    def handle_api_error(self, error: Exception, context: str = "") -> str:
        """Handle API-related errors.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            str: User-friendly error message
        """
        self.error_count += 1

        error_msg = f"API error{f' in {context}' if context else ''}: {error}"
        self.logger.error(error_msg)

        if self.config.debug:
            self.logger.debug(f"API error traceback:\n{traceback.format_exc()}")

        # Return user-friendly message
        return "Nya! Something went wrong with the AI service, please try again later."

    def handle_discord_error(self, error: Exception, context: str = "") -> str:
        """Handle Discord API errors.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            str: User-friendly error message
        """
        self.error_count += 1

        error_msg = f"Discord error{f' in {context}' if context else ''}: {error}"
        self.logger.error(error_msg)

        if isinstance(error, discord.Forbidden):
            return "Nya! I don't have permission to do that. Please check my server permissions."
        elif isinstance(error, discord.NotFound):
            return "Nya! I couldn't find what you're looking for."
        elif isinstance(error, discord.HTTPException):
            return "Nya! There was a problem communicating with Discord."
        else:
            return "Nya! Something went wrong, please try again later."

    async def handle_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Handle command errors with user feedback.

        Args:
            ctx: Command context
            error: Command error
        """
        self.error_count += 1

        self.logger.error(f"Command error in {ctx.command}: {error}")

        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"{ctx.author.mention} You don't have permission to use this command, nya! (´･ω･`)"
            )
        elif isinstance(error, commands.NotOwner):
            await ctx.send(
                f"{ctx.author.mention} Only my owner can use this command, nya! (｡•́︿•̀｡)"
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"{ctx.author.mention} This command is on cooldown, please wait "
                f"{error.retry_after:.1f} seconds, nya!"
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{ctx.author.mention} You're missing a required argument: `{error.param}`, nya!"
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"{ctx.author.mention} Invalid argument provided, nya! Please check the command usage."
            )
        elif isinstance(error, commands.CommandNotFound):
            # Ignore - handled by Discord's slash command system
            pass
        else:
            await ctx.send("Something went wrong, nya! Please try again later. (´･ω･`)")

            if self.config.debug:
                self.logger.error(
                    f"Unhandled command error traceback:\n{traceback.format_exc()}"
                )

    def handle_generic_error(
        self, error: Exception, context: str = "", reraise: bool = False
    ) -> str:
        """Handle generic errors.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            reraise: Whether to re-raise the exception after logging

        Returns:
            str: User-friendly error message

        Raises:
            Exception: If reraise is True
        """
        self.error_count += 1

        error_msg = f"Generic error{f' in {context}' if context else ''}: {error}"
        self.logger.error(error_msg)

        if self.config.debug:
            self.logger.debug(f"Error traceback:\n{traceback.format_exc()}")

        if reraise:
            raise type(error)(str(error)) from error

        return "Nya! An unexpected error occurred, please try again later."

    def get_error_stats(self) -> dict:
        """Get error statistics.

        Returns:
            dict: Error statistics
        """
        return {"total_errors": self.error_count, "debug_mode": self.config.debug}

    def reset_error_count(self) -> None:
        """Reset the error counter."""
        self.error_count = 0
        self.logger.info("Error counter reset")
