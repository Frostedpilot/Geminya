import discord
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="en")
    async def help(self, ctx):
        embed = discord.Embed(title="Bot Commands", color=0x03A64B)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        command_tree = self.bot.commands
        for command in command_tree:
            if command.hidden:
                continue
            command_description = command.description or "Not implemented yet, nyaa!"
            embed.add_field(name=command.name, value=command_description, inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
