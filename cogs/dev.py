import discord
from discord.ext import commands
import os


class Dev(commands.Cog, command_attrs={"hidden": True}):
    """Εντολές developer — μόνο για τον owner."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="reload", aliases=["rl"])
    async def reload(self, ctx, cog: str = None):
        """Επαναφορτώνει ένα cog ή όλα αν δεν δοθεί όνομα."""
        if cog:
            target = f"cogs.{cog}"
            try:
                await self.bot.reload_extension(target)
                await ctx.send(f"Επαναφορτώθηκε `{target}`")
            except commands.ExtensionNotLoaded:
                await ctx.send(f"Το `{target}` δεν είναι φορτωμένο.")
            except Exception as e:
                await ctx.send(f"Αποτυχία επαναφόρτωσης `{target}`: {e}")
        else:
            results = []
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    ext = f"cogs.{filename[:-3]}"
                    try:
                        await self.bot.reload_extension(ext)
                        results.append(f"✓ {ext}")
                    except Exception as e:
                        results.append(f"✗ {ext}: {e}")
            await ctx.send("```\n" + "\n".join(results) + "\n```")

    @commands.command(name="load")
    async def load(self, ctx, cog: str):
        """Φορτώνει ένα cog."""
        target = f"cogs.{cog}"
        try:
            await self.bot.load_extension(target)
            await ctx.send(f"Φορτώθηκε `{target}`")
        except Exception as e:
            await ctx.send(f"Αποτυχία φόρτωσης `{target}`: {e}")

    @commands.command(name="unload")
    async def unload(self, ctx, cog: str):
        """Αποφορτώνει ένα cog."""
        target = f"cogs.{cog}"
        try:
            await self.bot.unload_extension(target)
            await ctx.send(f"Αποφορτώθηκε `{target}`")
        except Exception as e:
            await ctx.send(f"Αποτυχία αποφόρτωσης `{target}`: {e}")


async def setup(bot):
    await bot.add_cog(Dev(bot))