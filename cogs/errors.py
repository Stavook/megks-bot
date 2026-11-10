import logging
from typing import Optional

import discord
from discord.ext import commands

log = logging.getLogger("megks_bot.errors")

GENERIC_ERROR = "Κάτι πήγε στραβά. Δοκίμασε ξανά αργότερα."


def format_usage(ctx) -> str:
    command = ctx.command
    invocation = " ".join(part for part in (command.qualified_name, command.signature) if part)
    return f"`{ctx.prefix}{invocation}`"


def format_permissions(perms) -> str:
    return ", ".join(f"`{p.replace('_', ' ')}`" for p in perms)


def describe_error(ctx, error) -> Optional[str]:
    """Maps an exception to a short user-facing message, or None to stay silent.

    Never includes raw exception text.
    """
    if isinstance(error, commands.CommandNotFound):
        return None

    if isinstance(error, commands.CommandInvokeError):
        original = error.original
        if isinstance(original, discord.Forbidden):
            return "Δεν έχω δικαίωμα να εκτελέσω αυτή την ενέργεια."
        return GENERIC_ERROR

    if isinstance(error, commands.MissingPermissions):
        return "Δεν έχεις δικαίωμα να χρησιμοποιήσεις αυτή την εντολή."
    if isinstance(error, commands.BotMissingPermissions):
        return f"Δεν έχω τα απαραίτητα δικαιώματα για αυτή την εντολή: {format_permissions(error.missing_permissions)}."
    if isinstance(error, commands.NoPrivateMessage):
        return "Η εντολή αυτή λειτουργεί μόνο μέσα σε server."
    if isinstance(error, commands.CommandOnCooldown):
        return f"Περίμενε λίγο· δοκίμασε ξανά σε {max(1, round(error.retry_after))}δ."
    if isinstance(error, commands.CheckFailure):
        # e.g. owner-only commands: don't reveal that they exist.
        return None

    if isinstance(error, commands.MissingRequiredArgument):
        return f"Λείπει το όρισμα `{error.param.name}`. Χρήση: {format_usage(ctx)}"
    if isinstance(error, commands.UserInputError):
        return f"Μη έγκυρο όρισμα. Χρήση: {format_usage(ctx)}"

    return GENERIC_ERROR


class Errors(commands.Cog):
    """Κεντρική διαχείριση σφαλμάτων εντολών."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Commands/cogs with their own handler take care of themselves.
        if ctx.command and ctx.command.has_error_handler():
            return
        if ctx.cog and ctx.cog.has_error_handler():
            return

        message = describe_error(ctx, error)
        if isinstance(error, commands.CommandInvokeError) or message == GENERIC_ERROR:
            log.error(
                "Unhandled error in command %r (guild=%s, user=%s)",
                ctx.command.qualified_name if ctx.command else None,
                ctx.guild.id if ctx.guild else None,
                ctx.author.id,
                exc_info=error,
            )
        if message is None:
            return
        try:
            await ctx.send(message)
        except discord.HTTPException:
            log.warning("Could not send error message to channel %s", getattr(ctx.channel, "id", None))


async def setup(bot):
    await bot.add_cog(Errors(bot))
