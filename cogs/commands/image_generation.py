"""Image generation command cog."""

import base64
import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import re

import io

from cogs.base_command import BaseCommand
from services.container import ServiceContainer
from services.llm.types import LLMRequest, ImageRequest
from config.models import MODEL_INFOS
from utils.model_utils import get_model_name_by_id


class ImageSize(Enum):
    """Supported image sizes."""

    SQUARE_1024 = "1024x1024"
    PORTRAIT_1024 = "1024x1792"
    LANDSCAPE_1792 = "1792x1024"
    SQUARE_512 = "512x512"


class ImageStyle(Enum):
    """Image generation styles."""

    VIVID = "vivid"
    NATURAL = "natural"
    ANIME = "anime"
    REALISTIC = "realistic"


class ImageQuality(Enum):
    """Image quality settings."""

    STANDARD = "standard"
    HD = "hd"


@dataclass
class ImageGenerationRequest:
    """Request for image generation."""

    prompt: str
    model: str
    size: ImageSize = ImageSize.SQUARE_512
    quality: ImageQuality = ImageQuality.STANDARD
    style: Optional[ImageStyle] = None


class ImageGenerationCog(BaseCommand):
    """Generate AI images using various models."""

    def __init__(self, bot, services: ServiceContainer):
        super().__init__(bot, services)

    def _get_available_image_models(self) -> Dict[str, str]:
        """Get available image generation models."""
        image_models = {}
        for display_name, model_info in MODEL_INFOS.items():
            if getattr(model_info, "image_gen", False):
                image_models[display_name] = model_info.id
        return image_models

    async def _model_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for image generation models."""
        image_models = self._get_available_image_models()

        # Filter models based on current input
        matching_models = []
        current_lower = current.lower()

        for display_name in image_models.keys():
            if current_lower in display_name.lower():
                matching_models.append(display_name)

        # Sort by relevance (exact matches first, then contains)
        exact_matches = [
            m for m in matching_models if m.lower().startswith(current_lower)
        ]
        contains_matches = [m for m in matching_models if m not in exact_matches]
        sorted_matches = exact_matches + contains_matches

        # Convert to choices (limit to 25)
        choices = []
        for model_name in sorted_matches[:25]:
            choices.append(app_commands.Choice(name=model_name, value=model_name))

        return choices

    async def _size_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for image sizes."""
        sizes = [
            ("Square 1024x1024", "1024x1024"),
            ("Portrait 1024x1792", "1024x1792"),
            ("Landscape 1792x1024", "1792x1024"),
            ("Square 512x512", "512x512"),
        ]

        current_lower = current.lower()
        choices = []

        for display, value in sizes:
            if current_lower in display.lower() or current_lower in value:
                choices.append(app_commands.Choice(name=display, value=value))

        return choices[:25]

    async def _style_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for image styles."""
        styles = [
            ("Vivid", "vivid"),
            ("Natural", "natural"),
            ("Anime", "anime"),
            ("Realistic", "realistic"),
        ]

        current_lower = current.lower()
        choices = []

        for display, value in styles:
            if current_lower in display.lower():
                choices.append(app_commands.Choice(name=display, value=value))

        return choices[:25]

    def _enhance_prompt(self, prompt: str, style: Optional[str] = None) -> str:
        """Enhance the user's prompt with quality and style modifiers."""
        enhanced = prompt.strip()

        # Add style-specific enhancements
        if style == "anime":
            if "anime" not in enhanced.lower():
                enhanced = f"anime style, {enhanced}"
            enhanced += ", high quality, detailed anime art, masterpiece"
        elif style == "realistic":
            enhanced += (
                ", photorealistic, high quality, detailed, professional photography"
            )
        elif style == "vivid":
            enhanced += ", vibrant colors, high contrast, dramatic lighting"
        elif style == "natural":
            enhanced += ", natural lighting, soft colors, realistic"
        else:
            # Default enhancements
            enhanced += ", high quality, detailed"

        return enhanced

    def _process_image_input(
        self, image: Optional[discord.Attachment], prompt: str
    ) -> tuple[Optional[str], str]:
        """Process image input and return (image_url, cleaned_prompt)."""
        image_url = None
        cleaned_prompt = prompt

        # Check for Discord attachment first
        if image and image.content_type and image.content_type.startswith("image/"):
            image_url = image.url
        else:
            # Look for image URLs in the prompt using a simple pattern
            url_pattern = r"(https?://[^\s]+)"
            urls = re.findall(url_pattern, prompt)

            # Check if any URL looks like an image
            image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
            for url in urls:
                if any(url.lower().endswith(ext) for ext in image_extensions):
                    image_url = url
                    # Remove the URL from the prompt and clean up extra spaces
                    cleaned_prompt = re.sub(
                        r"\s+", " ", prompt.replace(url, "")
                    ).strip()
                    break

        return image_url, cleaned_prompt

    @app_commands.command(
        name="generate", description="Generate an AI image from a text prompt"
    )
    @app_commands.describe(
        prompt="Description of the image you want to generate (can include image URLs)",
        model="AI model to use for image generation",
        size="Image size (default: 1024x1024)",
        style="Art style for the image",
        quality="Image quality setting",
        image="Optional: Upload an image for image-to-image generation",
    )
    @app_commands.autocomplete(
        model=_model_autocomplete, size=_size_autocomplete, style=_style_autocomplete
    )
    async def generate_image(
        self,
        interaction: discord.Interaction,
        prompt: str,
        model: str = None,
        size: str = "512x512",
        style: str = None,
        quality: str = "standard",
        image: Optional[discord.Attachment] = None,
    ):
        """Generate an AI image from a text prompt."""
        try:
            # Validate inputs
            if not prompt or len(prompt.strip()) < 3:
                embed = discord.Embed(
                    title="❌ Invalid Prompt",
                    description="Please provide a more detailed prompt (at least 3 characters).",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Get available models
            image_models = self._get_available_image_models()

            if not image_models:
                embed = discord.Embed(
                    title="❌ No Image Models Available",
                    description="No image generation models are currently available.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Use default model if none specified
            if not model:
                model = list(image_models.keys())[0]  # Use first available model
            elif model not in image_models:
                embed = discord.Embed(
                    title="❌ Invalid Model",
                    description=f"Model '{model}' is not available for image generation.\n"
                    f"Available models: {', '.join(image_models.keys())}",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Defer the response since image generation takes time
            await interaction.response.defer()

            # Get the actual model ID
            model_id = image_models[model]

            # Process input image if provided and clean prompt
            input_image_url, cleaned_prompt = self._process_image_input(image, prompt)

            # Enhance the prompt
            enhanced_prompt = self._enhance_prompt(cleaned_prompt, style)

            # Send initial "generating" message
            image_info = "\n**Input Image:** Provided" if input_image_url else ""
            embed = discord.Embed(
                title="🎨 Generating Image...",
                description=f"Creating an image with **{model}**\n\n"
                f"**Prompt:** {cleaned_prompt}\n"
                f"**Size:** {size}\n"
                f"**Style:** {style or 'Default'}\n"
                f"**Quality:** {quality}{image_info}",
                color=0x3498DB,
            )
            embed.set_footer(text="This may take 10-30 seconds...")

            # Include input image with the initial message if provided
            files = []
            if image and image.content_type and image.content_type.startswith("image/"):
                # For Discord attachments, we can include the original image
                try:
                    # Read the image data
                    image_data = await image.read()
                    # Create a file object with the original filename
                    input_file = discord.File(
                        io.BytesIO(image_data), filename=f"input_{image.filename}"
                    )
                    files.append(input_file)
                    embed.set_image(url=f"attachment://input_{image.filename}")
                except Exception as e:
                    self.logger.warning(f"Failed to include input image: {e}")
            elif input_image_url:
                # For URLs, set the image in the embed
                embed.set_image(url=input_image_url)

            if files:
                await interaction.edit_original_response(embed=embed, attachments=files)
            else:
                await interaction.edit_original_response(embed=embed)

            # Prepare the request
            try:
                # Create a special image generation request
                request = ImageRequest(
                    prompt=enhanced_prompt,
                    model=model_id,
                    user_id=str(interaction.user.id),
                    input_image_url=input_image_url,
                )

                response = await self.services.llm_manager.generate_image(request)

                # Parse the response (assuming it contains the image URL)
                if response.error:
                    embed = discord.Embed(
                        title="❌ Generation Failed",
                        description=f"Failed to generate image. Error: {response.error}",
                        color=0xFF6B6B,
                    )

                    await interaction.edit_original_response(embed=embed)
                # elif response.image_url:
                #     embed = discord.Embed(
                #         title="✅ Image Generated",
                #         description=f"Image generated with **{model}**",
                #         url=response.image_url,
                #         color=0x2ECC71,
                #     )

                #     await interaction.edit_original_response(embed=embed)
                elif response.image_base64:
                    file = discord.File(
                        io.BytesIO(base64.b64decode(response.image_base64)),
                        filename="image.png",
                    )
                    embed = discord.Embed(
                        title="✅ Image Generated",
                        description=f"Image generated with **{model}**",
                        color=0x2ECC71,
                    )

                    await interaction.edit_original_response(
                        embed=embed, attachments=[file]
                    )
                else:
                    # Handle error response
                    embed = discord.Embed(
                        title="❌ Generation Failed",
                        description=f"Failed to generate image. Response: {response.content[:200]}",
                        color=0xFF6B6B,
                    )
                    await interaction.edit_original_response(embed=embed)

            except Exception as e:
                self.logger.error(f"Error generating image: {e}")
                embed = discord.Embed(
                    title="❌ Generation Error",
                    description=f"An error occurred while generating the image: {str(e)[:200]}",
                    color=0xFF6B6B,
                )
                await interaction.edit_original_response(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in generate_image command: {e}")

            error_embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred. Please try again.",
                color=0xFF0000,
            )

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        embed=error_embed, ephemeral=True
                    )
            except Exception as followup_error:
                self.logger.error(f"Failed to send error message: {followup_error}")

    @app_commands.command(
        name="image_models", description="List available image generation models"
    )
    async def list_image_models(self, interaction: discord.Interaction):
        """List all available image generation models."""
        try:
            image_models = self._get_available_image_models()

            if not image_models:
                embed = discord.Embed(
                    title="❌ No Image Models",
                    description="No image generation models are currently available.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="🎨 Available Image Generation Models",
                description=f"Found {len(image_models)} image generation models:",
                color=0x00FF88,
            )

            # Add model information
            model_list = []
            for display_name, model_id in image_models.items():
                model_info = MODEL_INFOS[display_name]

                # Create model description
                info_parts = []
                if model_info.cost_per_million_tokens:
                    cost = model_info.cost_per_million_tokens.get("out", 0)
                    if cost == 0:
                        info_parts.append("🆓 Free")
                    else:
                        info_parts.append(f"💰 ${cost:.3f}/image")

                if model_info.description:
                    # Truncate description if too long
                    desc = (
                        model_info.description[:100] + "..."
                        if len(model_info.description) > 100
                        else model_info.description
                    )
                    info_parts.append(desc)

                info_text = (
                    " • ".join(info_parts) if info_parts else "Image generation model"
                )
                model_list.append(f"🎨 **{display_name}**\n   └ {info_text}")

            # Split into chunks if too many models
            if len(model_list) <= 8:
                embed.add_field(
                    name="Models", value="\n".join(model_list), inline=False
                )
            else:
                # Split into multiple fields
                mid = len(model_list) // 2
                embed.add_field(
                    name="Models (Part 1)",
                    value="\n".join(model_list[:mid]),
                    inline=True,
                )
                embed.add_field(
                    name="Models (Part 2)",
                    value="\n".join(model_list[mid:]),
                    inline=True,
                )

            embed.set_footer(
                text="Use /generate <prompt> model:<model_name> to generate images"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error in list_image_models: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to retrieve image models.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    services = getattr(bot, "services", None)
    if services is None:
        raise RuntimeError(
            "Services container not found. Make sure bot is properly initialized."
        )

    await bot.add_cog(ImageGenerationCog(bot, services))
