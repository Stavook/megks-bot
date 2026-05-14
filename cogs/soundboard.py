import discord
from discord.ext import commands
from discord.http import Route
import asyncio
import random


class Soundboard(commands.Cog):
    """Παίζει τυχαίο soundboard ήχο όταν μπαίνει χρήστης σε voice channel."""

    def __init__(self, bot):
        self.bot = bot
        self.enabled: dict[int, bool] = {}

    def is_enabled(self, guild_id: int) -> bool:
        return self.enabled.get(guild_id, True)

    @commands.command(name="autosound")
    @commands.has_permissions(manage_guild=True)
    async def autosound(self, ctx):
        """Ενεργοποιεί/απενεργοποιεί τυχαίο ήχο όταν μπαίνει χρήστης."""
        current = self.is_enabled(ctx.guild.id)
        self.enabled[ctx.guild.id] = not current
        state = "ενεργοποιήθηκε" if not current else "απενεργοποιήθηκε"
        await ctx.send(f"Το auto-soundboard {state}.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        if before.channel == after.channel:
            return
        if after.channel is None:
            return
        guild = member.guild
        if not self.is_enabled(guild.id):
            return
        if guild.voice_client and guild.voice_client.is_playing():
            return

        try:
            sounds = await guild.fetch_soundboard_sounds()
        except discord.HTTPException:
            return
        if not sounds:
            return
        sound = random.choice(sounds)

        try:
            vc = await after.channel.connect()
        except discord.ClientException:
            return

        try:
            await self.bot.http.request(
                Route("POST", "/channels/{channel_id}/send-soundboard-sound", channel_id=after.channel.id),
                json={"sound_id": str(sound.id), "source_guild_id": str(guild.id)}
            )
        except discord.HTTPException:
            pass

        await asyncio.sleep(4)
        if vc.is_connected() and not vc.is_playing():
            await vc.disconnect()


async def setup(bot):
    await bot.add_cog(Soundboard(bot))