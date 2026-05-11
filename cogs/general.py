import discord
from discord.ext import commands
import time

COG_ICONS = {
    "General": "🔧",
    "Moderation": "🔨",
    "Music": "🎵",
    "Fun": "🎲",
    "NSFW": "🔞",
}


class General(commands.Cog):
    """General utility commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx, *, command_name: str = None):
        """Shows available commands."""
        prefix = ctx.prefix

        if command_name:
            cmd = self.bot.get_command(command_name)
            if cmd is None:
                return await ctx.send(f"Command `{command_name}` not found.")
            embed = discord.Embed(
                title=f"`{prefix}{cmd.name}`",
                description=cmd.help or "No description.",
                color=discord.Color.blurple()
            )
            if cmd.aliases:
                embed.add_field(name="Aliases", value=" ".join(f"`{a}`" for a in cmd.aliases))
            embed.set_footer(text=f"Tip: {prefix}help <command> for more info")
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Megks Bot",
            description=f"Use `{prefix}help <command>` for details on a specific command.",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        for cog_name, cog in self.bot.cogs.items():
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue
            icon = COG_ICONS.get(cog_name, "📁")
            value = "\n".join(
                f"`{prefix}{c.name}` — {c.help.split('.')[0] if c.help else 'No description'}"
                for c in cmds
            )
            embed.add_field(name=f"{icon} {cog_name}", value=value, inline=False)

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Shows bot latency."""
        start = time.monotonic()
        msg = await ctx.send("Pinging...")
        elapsed = (time.monotonic() - start) * 1000
        await msg.edit(content=f"Pong! Latency: `{self.bot.latency * 1000:.1f}ms` | Round-trip: `{elapsed:.1f}ms`")

    @commands.command(name="avatar")
    async def avatar(self, ctx, member: discord.Member = None):
        """Shows a user's avatar. Defaults to you."""
        member = member or ctx.author
        embed = discord.Embed(title=f"{member.display_name}'s avatar", color=discord.Color.blurple())
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        """Shows information about a user."""
        member = member or ctx.author
        embed = discord.Embed(title=str(member), color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Nickname", value=member.nick or "None")
        embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, style="R"))
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style="R"))
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) or "None", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
