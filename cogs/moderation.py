import discord
from discord.ext import commands
import datetime


def can_act_on(ctx, member: discord.Member) -> tuple[bool, str | None]:
    """Returns (allowed, error_message). Used by kick/ban/mute."""
    if member == ctx.author:
        return False, "Δεν μπορείς να το κάνεις στον εαυτό σου."
    if member == ctx.guild.me:
        return False, "Δεν μπορώ να το κάνω στον εαυτό μου."
    if member == ctx.guild.owner:
        return False, "Δεν μπορείς να το κάνεις στον ιδιοκτήτη του server."
    if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
        return False, "Δεν μπορείς να ενεργήσεις σε κάποιον με ίσο ή ανώτερο ρόλο από τον δικό σου."
    if member.top_role >= ctx.guild.me.top_role:
        return False, "Ο ρόλος μου είναι χαμηλότερος ή ίσος με του χρήστη — δεν μπορώ να ενεργήσω."
    return True, None


class Moderation(commands.Cog):
    """Εντολές διαχείρισης server."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Χωρίς λόγο"):
        """Διώχνει έναν χρήστη από τον server."""
        allowed, error = can_act_on(ctx, member)
        if not allowed:
            return await ctx.send(error)
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.send(f"Διώχτηκε ο **{member}** | Λόγος: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Χωρίς λόγο"):
        """Κάνει ban έναν χρήστη από τον server."""
        allowed, error = can_act_on(ctx, member)
        if not allowed:
            return await ctx.send(error)
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)
        await ctx.send(f"Έγινε ban ο **{member}** | Λόγος: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, *, user: str):
        """Αφαιρεί το ban από έναν χρήστη μέσω name ή ID."""
        target = None
        async for entry in ctx.guild.bans():
            if str(entry.user) == user or str(entry.user.id) == user or entry.user.name == user:
                target = entry.user
                break
        if target is None:
            return await ctx.send(f"Δεν βρέθηκε χρήστης με ban που να ταιριάζει με `{user}`.")
        await ctx.guild.unban(target)
        await ctx.send(f"Αφαιρέθηκε το ban από **{target}**")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Διαγράφει έναν αριθμό μηνυμάτων (1-100)."""
        if not 1 <= amount <= 100:
            return await ctx.send("Ο αριθμός μηνυμάτων πρέπει να είναι μεταξύ 1 και 100.")
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Διαγράφηκαν {len(deleted) - 1} μηνύματα.")
        await msg.delete(delay=3)

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason: str = "Χωρίς λόγο"):
        """Φιμώνει έναν χρήστη για συγκεκριμένα λεπτά (μέγιστο 40320 = 28 ημέρες)."""
        if minutes < 1 or minutes > 40320:
            return await ctx.send("Η διάρκεια πρέπει να είναι μεταξύ 1 και 40320 λεπτών (28 ημέρες).")
        allowed, error = can_act_on(ctx, member)
        if not allowed:
            return await ctx.send(error)
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{ctx.author}: {reason}")
        await ctx.send(f"Φιμώθηκε ο **{member}** για {minutes} λεπτό(ά) | Λόγος: {reason}")

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Αφαιρεί τη φίμωση από έναν χρήστη."""
        if not member.is_timed_out():
            return await ctx.send(f"Ο **{member}** δεν είναι φιμωμένος.")
        await member.timeout(None)
        await ctx.send(f"Αφαιρέθηκε η φίμωση από **{member}**")


async def setup(bot):
    await bot.add_cog(Moderation(bot))