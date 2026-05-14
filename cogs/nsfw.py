import discord
from discord.ext import commands
import aiohttp

NEKOBOT_API = "https://nekobot.xyz/api/image"

VALID_TAGS = ["pgif", "boobs", "ass", "thigh", "pussy", "anal", "gonewild", "4k"]


class NSFW(commands.Cog):
    """NSFW εντολές — μόνο σε age-restricted channels."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="porn", aliases=["nsfw"])
    @commands.is_nsfw()
    async def porn(self, ctx, tag: str = "pgif"):
        """Στέλνει τυχαίο NSFW image/GIF. Tags: pgif, boobs, ass, thigh, pussy, anal, gonewild, 4k."""
        if tag not in VALID_TAGS:
            return await ctx.send(f"Άκυρο tag. Επίλεξε από: {', '.join(f'`{t}`' for t in VALID_TAGS)}")

        async with aiohttp.ClientSession() as session:
            async with session.get(NEKOBOT_API, params={"type": tag}) as resp:
                if resp.status != 200:
                    return await ctx.send("Δεν ήταν δυνατή η ανάκτηση, δοκίμασε ξανά αργότερα.")
                data = await resp.json()

        if not data.get("success"):
            return await ctx.send("Δεν ήταν δυνατή η ανάκτηση, δοκίμασε ξανά αργότερα.")

        embed = discord.Embed(color=discord.Color.red())
        embed.set_footer(text=f"Tag: {tag}")
        embed.set_image(url=data["message"])
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(NSFW(bot))