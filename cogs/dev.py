import discord
from discord.ext import commands
import logging
import os

log = logging.getLogger("megks_bot.dev")


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
            except commands.ExtensionNotFound:
                await ctx.send(f"Δεν βρέθηκε το `{target}`.")
            except Exception:
                log.exception("Failed to reload %s", target)
                await ctx.send(f"Αποτυχία επαναφόρτωσης `{target}`. Δες τα logs για λεπτομέρειες.")
        else:
            results = []
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    ext = f"cogs.{filename[:-3]}"
                    try:
                        await self.bot.reload_extension(ext)
                        results.append(f"✓ {ext}")
                    except Exception:
                        log.exception("Failed to reload %s", ext)
                        results.append(f"✗ {ext}")
            summary = "\n".join(results)
            if any(line.startswith("✗") for line in results):
                summary += "\n\nΔες τα logs για λεπτομέρειες."
            await ctx.send("```\n" + summary + "\n```")

    @commands.command(name="load")
    async def load(self, ctx, cog: str):
        """Φορτώνει ένα cog."""
        target = f"cogs.{cog}"
        try:
            await self.bot.load_extension(target)
            await ctx.send(f"Φορτώθηκε `{target}`")
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f"Το `{target}` είναι ήδη φορτωμένο.")
        except commands.ExtensionNotFound:
            await ctx.send(f"Δεν βρέθηκε το `{target}`.")
        except Exception:
            log.exception("Failed to load %s", target)
            await ctx.send(f"Αποτυχία φόρτωσης `{target}`. Δες τα logs για λεπτομέρειες.")

    @commands.command(name="unload")
    async def unload(self, ctx, cog: str):
        """Αποφορτώνει ένα cog."""
        target = f"cogs.{cog}"
        try:
            await self.bot.unload_extension(target)
            await ctx.send(f"Αποφορτώθηκε `{target}`")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"Το `{target}` δεν είναι φορτωμένο.")
        except Exception:
            log.exception("Failed to unload %s", target)
            await ctx.send(f"Αποτυχία αποφόρτωσης `{target}`. Δες τα logs για λεπτομέρειες.")


async def setup(bot):
    await bot.add_cog(Dev(bot))