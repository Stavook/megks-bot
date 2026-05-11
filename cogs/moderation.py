import discord
from discord.ext import commands


class Moderation(commands.Cog):
    """Εντολές διαχείρισης server."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Χωρίς λόγο"):
        """Διώχνει έναν χρήστη από τον server."""
        if member == ctx.author:
            return await ctx.send("Δεν μπορείς να διώξεις τον εαυτό σου.")
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("Δεν μπορείς να διώξεις κάποιον με ίσο ή ανώτερο ρόλο.")
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.send(f"Διώχτηκε ο **{member}** | Λόγος: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Χωρίς λόγο"):
        """Κάνει ban έναν χρήστη από τον server."""
        if member == ctx.author:
            return await ctx.send("Δεν μπορείς να κάνεις ban τον εαυτό σου.")
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("Δεν μπορείς να κάνεις ban κάποιον με ίσο ή ανώτερο ρόλο.")
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)
        await ctx.send(f"Έγινε ban ο **{member}** | Λόγος: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, *, user: str):
        """Αφαιρεί το ban από έναν χρήστη μέσω name#discriminator ή ID."""
        bans = [entry async for entry in ctx.guild.bans()]
        target = None
        for entry in bans:
            if str(entry.user) == user or str(entry.user.id) == user:
                target = entry.user
                break
        if target is None:
            return await ctx.send("Δεν βρέθηκε χρήστης με ban.")
        await ctx.guild.unban(target)
        await ctx.send(f"Αφαιρέθηκε το ban από **{target}**")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Διαγράφει έναν αριθμό μηνυμάτων (1-100)."""
        if not 1 <= amount <= 100:
            return await ctx.send("Το πλήθος πρέπει να είναι μεταξύ 1 και 100.")
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Διαγράφηκαν {len(deleted) - 1} μηνύματα.")
        await msg.delete(delay=3)

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason: str = "Χωρίς λόγο"):
        """Φιμώνει έναν χρήστη για συγκεκριμένα λεπτά (μέγιστο 40320)."""
        import datetime
        if minutes < 1 or minutes > 40320:
            return await ctx.send("Η διάρκεια πρέπει να είναι μεταξύ 1 και 40320 λεπτών.")
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{ctx.author}: {reason}")
        await ctx.send(f"Φιμώθηκε ο **{member}** για {minutes} λεπτό(ά) | Λόγος: {reason}")

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Αφαιρεί τη φίμωση από έναν χρήστη."""
        await member.timeout(None)
        await ctx.send(f"Αφαιρέθηκε η φίμωση από **{member}**")


async def setup(bot):
    await bot.add_cog(Moderation(bot))