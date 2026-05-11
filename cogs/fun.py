import discord
from discord.ext import commands
import random


class Fun(commands.Cog):
    """Εντολές διασκέδασης."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="choose")
    async def choose(self, ctx, *, options: str):
        """Επιλέγει τυχαία από επιλογές χωρισμένες με κόμμα."""
        choices = [o.strip() for o in options.split(",") if o.strip()]
        if len(choices) < 2:
            return await ctx.send("Δώσε τουλάχιστον 2 επιλογές χωρισμένες με κόμμα.")
        await ctx.send(f"Επιλέγω: **{random.choice(choices)}**")


async def setup(bot):
    await bot.add_cog(Fun(bot))