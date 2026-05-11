import discord
from discord.ext import commands
import random


class Fun(commands.Cog):
    """Fun and games commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="choose")
    async def choose(self, ctx, *, options: str):
        """Randomly picks from comma-separated options."""
        choices = [o.strip() for o in options.split(",") if o.strip()]
        if len(choices) < 2:
            return await ctx.send("Provide at least 2 options separated by commas.")
        await ctx.send(f"I choose: **{random.choice(choices)}**")


async def setup(bot):
    await bot.add_cog(Fun(bot))