import discord
import aiohttp
from discord.ext import commands
from typing import Optional, List, Dict
import asyncio

from cogs.base_command import BaseCommand
from services.container import ServiceContainer


class CurrencyCog(BaseCommand):
    """
    Currency exchange command cog for converting between different currencies.

    This cog provides currency conversion with intelligent autocomplete that supports
    both currency codes (USD) and full names (US Dollar).

    Uses the free currency exchange API from fawazahmed0/exchange-api
    which supports 200+ currencies including cryptocurrencies and metals.
    """

    # Constants
    BASE_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1"
    FALLBACK_URL = "https://latest.currency-api.pages.dev/v1"
    ERROR_MESSAGE = "Failed to retrieve currency exchange rates, nya! (｡•́︿•̀｡)"
    INVALID_CURRENCY_MESSAGE = "Invalid currency code provided, nya! (´･ω･`)"

    def __init__(self, bot: commands.Bot, services: ServiceContainer):
        super().__init__(bot, services)

        # Currency data cache
        self.currencies_data: Dict[str, str] = {}
        self.currency_translations: Dict[str, str] = (
            {}
        )  # Maps names/codes to official codes
        self.currency_choices: List[str] = []  # List for autocomplete
        self._currencies_loaded = False

        # Pre-fetch currencies when cog loads
        self._currency_task = asyncio.create_task(self._load_currencies())

    async def _load_currencies(self):
        """Load and cache all available currencies with translation mappings."""
        try:
            self.logger.info("Loading currency data for autocomplete...")
            currencies = await self._fetch_available_currencies()

            if not currencies:
                self.logger.warning("Failed to load currency data")
                return

            self.currencies_data = currencies
            self._build_translation_dict()
            self._currencies_loaded = True
            self.logger.info(
                f"Loaded {len(currencies)} currencies with autocomplete support"
            )

        except Exception as e:
            self.logger.error(f"Error loading currencies: {e}")

    def _build_translation_dict(self):
        """Build translation dictionary for currency codes and names."""
        self.currency_translations = {}
        self.currency_choices = []

        for code, name in self.currencies_data.items():
            # Add code -> code mapping (e.g., "usd" -> "usd")
            self.currency_translations[code.lower()] = code.lower()

            # Add name -> code mapping (e.g., "us dollar" -> "usd")
            self.currency_translations[name.lower()] = code.lower()

            # Create display choices for autocomplete
            self.currency_choices.append(f"{code.upper()} - {name}")

        # Sort choices for better UX
        self.currency_choices.sort()

    def _resolve_currency(self, currency_input: str) -> Optional[str]:
        """Resolve currency input to official code."""
        if not self._currencies_loaded:
            return None

        # Try exact match first (case insensitive)
        normalized_input = currency_input.lower().strip()

        # Direct translation lookup
        if normalized_input in self.currency_translations:
            return self.currency_translations[normalized_input]

        # Try to extract code from autocomplete format "USD - US Dollar"
        if " - " in currency_input:
            code_part = currency_input.split(" - ")[0].lower()
            if code_part in self.currency_translations:
                return self.currency_translations[code_part]

        return None

    async def _currency_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[str]]:
        """Autocomplete function for currency parameters."""
        if not self._currencies_loaded:
            return []

        # Filter choices based on current input
        current_lower = current.lower()
        matches = []

        for choice in self.currency_choices:
            if (
                current_lower in choice.lower() and len(matches) < 25
            ):  # Discord limit is 25
                matches.append(discord.app_commands.Choice(name=choice, value=choice))

        return matches

    @commands.hybrid_command(
        name="currency",
        description="Convert currency between different currencies (e.g., /currency 100 USD EUR)",
    )
    @discord.app_commands.autocomplete(from_currency=_currency_autocomplete)
    @discord.app_commands.autocomplete(to_currency=_currency_autocomplete)
    async def currency(
        self, ctx: commands.Context, amount: float, from_currency: str, to_currency: str
    ):
        """Convert currency from one to another."""
        # Validate amount
        if amount <= 0:
            await ctx.send("Amount must be greater than 0, nya! (´･ω･`)")
            return

        # Resolve currency inputs to official codes
        from_code = self._resolve_currency(from_currency)
        to_code = self._resolve_currency(to_currency)

        if from_code is None:
            embed = discord.Embed(
                title="❌ Invalid From Currency",
                description=f"Sorry, I couldn't find a currency matching '{from_currency}', nya! (´･ω･`)\n\n"
                "Try using the autocomplete suggestions when typing the command!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return

        if to_code is None:
            embed = discord.Embed(
                title="❌ Invalid To Currency",
                description=f"Sorry, I couldn't find a currency matching '{to_currency}', nya! (´･ω･`)\n\n"
                "Try using the autocomplete suggestions when typing the command!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
            return

        # Get exchange rate
        exchange_rate = await self._get_exchange_rate(from_code, to_code)

        if exchange_rate is None:
            await ctx.send(self.INVALID_CURRENCY_MESSAGE)
            return

        if exchange_rate == -1:
            await ctx.send(self.ERROR_MESSAGE)
            return

        # Calculate converted amount
        converted_amount = amount * exchange_rate

        # Get display names for currencies
        from_name = self.currencies_data.get(from_code, from_code.upper())
        to_name = self.currencies_data.get(to_code, to_code.upper())

        # Create embed
        embed = discord.Embed(
            title="💱 Currency Exchange",
            color=0x03A64B,
        )

        embed.add_field(
            name="From",
            value=f"{amount:,.2f} {from_code.upper()}\n*{from_name}*",
            inline=True,
        )

        embed.add_field(
            name="To",
            value=f"{converted_amount:,.2f} {to_code.upper()}\n*{to_name}*",
            inline=True,
        )

        embed.add_field(
            name="Exchange Rate",
            value=f"1 {from_code.upper()} = {exchange_rate:.6f} {to_code.upper()}",
            inline=False,
        )

        embed.set_footer(
            text="Exchange rates are updated daily • Powered by currency-api"
        )

        await ctx.send(embed=embed)
        self.logger.info(
            f"Currency conversion: {amount} {from_code.upper()} -> "
            f"{converted_amount:.2f} {to_code.upper()} for user {ctx.author}"
        )

    async def _fetch_available_currencies(self) -> Optional[Dict[str, str]]:
        """Fetch list of all available currencies from API."""
        url = f"{self.BASE_URL}/currencies.min.json"
        fallback_url = f"{self.FALLBACK_URL}/currencies.min.json"

        async with aiohttp.ClientSession() as session:
            # Try primary URL first
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
            except aiohttp.ClientError as e:
                self.logger.warning(f"Primary currencies API failed: {e}")

            # Try fallback URL
            try:
                async with session.get(fallback_url) as response:
                    if response.status == 200:
                        return await response.json()
            except aiohttp.ClientError as e:
                self.logger.error(f"Fallback currencies API also failed: {e}")

        return None

    async def _get_exchange_rate(
        self, from_currency: str, to_currency: str
    ) -> Optional[float]:
        """Get exchange rate between two currencies."""
        url = f"{self.BASE_URL}/currencies/{from_currency}.min.json"
        fallback_url = f"{self.FALLBACK_URL}/currencies/{from_currency}.min.json"

        async with aiohttp.ClientSession() as session:
            # Try primary URL first
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_rate(data, from_currency, to_currency)
                    elif response.status == 404:
                        # Invalid currency code
                        return None
            except aiohttp.ClientError as e:
                self.logger.warning(f"Primary API failed: {e}")

            # Try fallback URL
            try:
                async with session.get(fallback_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_rate(data, from_currency, to_currency)
                    elif response.status == 404:
                        # Invalid currency code
                        return None
            except aiohttp.ClientError as e:
                self.logger.error(f"Fallback API also failed: {e}")
                return -1

        return -1

    def _extract_rate(
        self, data: dict, from_currency: str, to_currency: str
    ) -> Optional[float]:
        """Extract exchange rate from API response."""
        try:
            rates = data.get(from_currency, {})
            rate = rates.get(to_currency)

            if rate is None:
                # Currency not found in rates
                return None

            return float(rate)
        except (KeyError, ValueError, TypeError):
            return None

    @currency.error
    async def currency_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle currency command errors."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Arguments",
                description="Please provide all required arguments, nya!\n\n"
                "**Usage:** `/currency <amount> <from_currency> <to_currency>`\n"
                "**Example:** `/currency 100 USD EUR`\n\n"
                "💡 Use autocomplete to select currencies easily!",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="❌ Invalid Arguments",
                description="Please provide a valid amount (number), nya!\n\n"
                "**Example:** `/currency 100 USD EUR`",
                color=0xFF6B6B,
            )
            await ctx.send(embed=embed)
        else:
            # Let the base class handle other errors
            await super().cog_command_error(ctx, error)

    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        if hasattr(self, "_currency_task") and not self._currency_task.done():
            self._currency_task.cancel()


async def setup(bot: commands.Bot):
    # Get services from bot instance
    await bot.add_cog(CurrencyCog(bot, bot.services))
