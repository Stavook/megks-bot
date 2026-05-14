import discord
from discord.ext import commands

COG_ICONS = {
    "General": "🔧",
    "Moderation": "🔨",
    "Music": "🎵",
    "Fun": "🎲",
    "NSFW": "🔞",
    "Rules": "📜",
    "Soundboard": "🔊",
}


class General(commands.Cog):
    """Γενικές εντολές."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx, *, query: str = None):
        """Δείχνει τις διαθέσιμες κατηγορίες εντολών."""
        prefix = ctx.prefix

        if query:
            cog_match = next(
                (c for name, c in self.bot.cogs.items() if name.lower() == query.lower()),
                None
            )
            if cog_match:
                cmds = [c for c in cog_match.get_commands() if not c.hidden]
                cog_name = type(cog_match).__name__
                icon = COG_ICONS.get(cog_name, "📁")
                embed = discord.Embed(
                    title=f"{icon} {cog_name}",
                    description=cog_match.description or "Χωρίς περιγραφή.",
                    color=discord.Color.blurple()
                )
                if cmds:
                    value = "\n".join(
                        f"`{prefix}{c.name}` — {c.help.split('.')[0] if c.help else 'Χωρίς περιγραφή'}"
                        for c in cmds
                    )
                    embed.add_field(name="Εντολές", value=value, inline=False)
                embed.set_footer(text=f"Συμβουλή: {prefix}help <εντολή> για λεπτομέρειες")
                return await ctx.send(embed=embed)

            cmd = self.bot.get_command(query)
            if cmd is None:
                return await ctx.send(f"Δεν βρέθηκε κατηγορία ή εντολή `{query}`.")
            embed = discord.Embed(
                title=f"`{prefix}{cmd.name}`",
                description=cmd.help or "Χωρίς περιγραφή.",
                color=discord.Color.blurple()
            )
            if cmd.aliases:
                embed.add_field(name="Συντομεύσεις", value=" ".join(f"`{a}`" for a in cmd.aliases))
            embed.set_footer(text=f"Συμβουλή: {prefix}help <εντολή> για περισσότερες πληροφορίες")
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="Megks Bot",
            description=f"Διάλεξε μια κατηγορία για να δεις τις εντολές της.",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        for cog_name, cog in self.bot.cogs.items():
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue
            icon = COG_ICONS.get(cog_name, "📁")
            embed.add_field(
                name=f"{icon} {cog_name}",
                value=f"`{prefix}help {cog_name.lower()}`",
                inline=True
            )

        embed.set_footer(
            text=f"Ζητήθηκε από {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    async def avatar(self, ctx, member: discord.Member = None):
        """Δείχνει το avatar ενός χρήστη. Προεπιλογή: εσένα."""
        member = member or ctx.author
        embed = discord.Embed(title=f"Avatar του {member.display_name}", color=discord.Color.blurple())
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        """Δείχνει πληροφορίες για έναν χρήστη."""
        member = member or ctx.author
        embed = discord.Embed(title=str(member), color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Ψευδώνυμο", value=member.nick or "Κανένα")
        embed.add_field(name="Μπήκε στον Server", value=discord.utils.format_dt(member.joined_at, style="R"))
        embed.add_field(name="Δημιουργία Λογαριασμού", value=discord.utils.format_dt(member.created_at, style="R"))
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
        embed.add_field(name=f"Ρόλοι ({len(roles)})", value=" ".join(roles) or "Κανένας", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))