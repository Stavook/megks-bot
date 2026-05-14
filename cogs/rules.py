import discord
from discord.ext import commands
import json
import os

RULES_FILE = "rules.json"


def load_rules() -> dict:
    if not os.path.exists(RULES_FILE):
        return {}
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_rules(rules: dict):
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


class Rules(commands.Cog):
    """Κανόνες του server."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rules")
    async def rules(self, ctx):
        """Δείχνει τους κανόνες του server."""
        rules = load_rules().get(str(ctx.guild.id), [])
        if not rules:
            return await ctx.send("Δεν υπάρχουν κανόνες ακόμα.")
        embed = discord.Embed(title=f"Κανόνες — {ctx.guild.name}", color=discord.Color.blurple())
        embed.description = "\n".join(f"**{i+1}.** {rule}" for i, rule in enumerate(rules))
        await ctx.send(embed=embed)

    @commands.command(name="addrule")
    @commands.has_permissions(administrator=True)
    async def addrule(self, ctx, *, text: str):
        """Προσθέτει έναν νέο κανόνα. Μόνο για admins."""
        data = load_rules()
        guild_rules = data.setdefault(str(ctx.guild.id), [])
        guild_rules.append(text)
        save_rules(data)
        await ctx.send(f"Προστέθηκε κανόνας **#{len(guild_rules)}**: {text}")

    @commands.command(name="delrule")
    @commands.has_permissions(administrator=True)
    async def delrule(self, ctx, number: int):
        """Διαγράφει έναν κανόνα μέσω αριθμού. Μόνο για admins."""
        data = load_rules()
        guild_rules = data.get(str(ctx.guild.id), [])
        if not 1 <= number <= len(guild_rules):
            return await ctx.send(f"Ο αριθμός πρέπει να είναι μεταξύ 1 και {len(guild_rules)}.")
        removed = guild_rules.pop(number - 1)
        save_rules(data)
        await ctx.send(f"Διαγράφηκε κανόνας **#{number}**: {removed}")


async def setup(bot):
    await bot.add_cog(Rules(bot))