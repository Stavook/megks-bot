import discord
from discord.ext import commands


class Moderation(commands.Cog):
    """Server moderation commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kicks a member from the server."""
        if member == ctx.author:
            return await ctx.send("You can't kick yourself.")
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("You can't kick someone with an equal or higher role.")
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.send(f"Kicked **{member}** | Reason: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Bans a member from the server."""
        if member == ctx.author:
            return await ctx.send("You can't ban yourself.")
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("You can't ban someone with an equal or higher role.")
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)
        await ctx.send(f"Banned **{member}** | Reason: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, *, user: str):
        """Unbans a user by name#discriminator or ID."""
        bans = [entry async for entry in ctx.guild.bans()]
        target = None
        for entry in bans:
            if str(entry.user) == user or str(entry.user.id) == user:
                target = entry.user
                break
        if target is None:
            return await ctx.send("Banned user not found.")
        await ctx.guild.unban(target)
        await ctx.send(f"Unbanned **{target}**")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Deletes a number of messages (1-100)."""
        if not 1 <= amount <= 100:
            return await ctx.send("Amount must be between 1 and 100.")
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Deleted {len(deleted) - 1} messages.")
        await msg.delete(delay=3)

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason: str = "No reason provided"):
        """Timeouts a member for the given number of minutes (max 40320)."""
        import datetime
        if minutes < 1 or minutes > 40320:
            return await ctx.send("Duration must be between 1 and 40320 minutes.")
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{ctx.author}: {reason}")
        await ctx.send(f"Muted **{member}** for {minutes} minute(s) | Reason: {reason}")

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Removes timeout from a member."""
        await member.timeout(None)
        await ctx.send(f"Unmuted **{member}**")


async def setup(bot):
    await bot.add_cog(Moderation(bot))