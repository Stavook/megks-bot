import discord
from discord.ext import commands
import aiohttp
import random

NEKOBOT_API = "https://nekobot.xyz/api/image"

VALID_TAGS = ["pgif", "hentai", "boobs", "anal", "pussy"]


class NSFW(commands.Cog):
    """NSFW commands — only usable in age-restricted channels."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="porn", aliases=["nsfw"])
    @commands.is_nsfw()
    async def porn(self, ctx, tag: str = "pgif"):
        """Posts a random NSFW image/GIF. Optional tag: pgif, hentai, boobs, anal, pussy."""
        if tag not in VALID_TAGS:
            return await ctx.send(f"Invalid tag. Choose from: {', '.join(f'`{t}`' for t in VALID_TAGS)}")

        async with aiohttp.ClientSession() as session:
            async with session.get(NEKOBOT_API, params={"type": tag}) as resp:
                if resp.status != 200:
                    return await ctx.send("Could not fetch content, try again later.")
                data = await resp.json()

        if not data.get("success"):
            return await ctx.send("Could not fetch content, try again later.")

        embed = discord.Embed(color=discord.Color.red())
        embed.set_footer(text=f"Tag: {tag}")
        embed.set_image(url=data["message"])
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(NSFW(bot))
