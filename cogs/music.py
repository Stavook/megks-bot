import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


class Song:
    def __init__(self, source, data, requester):
        self.source = source
        self.title = data.get("title", "Unknown")
        self.url = data.get("webpage_url", "")
        self.duration = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail")
        self.requester = requester

    @classmethod
    async def from_query(cls, query, requester, loop):
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(query, download=False)
        )
        if "entries" in data:
            data = data["entries"][0]
        source = discord.FFmpegPCMAudio(data["url"], **FFMPEG_OPTIONS)
        return cls(source, data, requester)

    def format_duration(self):
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class GuildPlayer:
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.loop = False


class Music(commands.Cog):
    """Music playback commands."""

    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    async def play_next(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player.loop and player.current:
            song = await Song.from_query(player.current.url, player.current.requester, self.bot.loop)
        elif player.queue:
            song = player.queue.popleft()
        else:
            player.current = None
            return

        player.current = song
        ctx.voice_client.play(
            song.source,
            after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
        )
        embed = discord.Embed(title="Now Playing", description=f"[{song.title}]({song.url})", color=discord.Color.green())
        embed.add_field(name="Duration", value=song.format_duration())
        embed.add_field(name="Requested by", value=song.requester.mention)
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.send(embed=embed)

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        """Plays a song by URL or search query."""
        if not ctx.author.voice:
            return await ctx.send("You're not in a voice channel.")
        if ctx.voice_client and ctx.voice_client.is_playing() and ctx.voice_client.channel != ctx.author.voice.channel:
            return await ctx.send(f"I'm already playing music in **{ctx.voice_client.channel.name}**.")
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        player = self.get_player(ctx.guild.id)
        searching = await ctx.send(f"Searching for `{query}`...")
        try:
            song = await Song.from_query(query, ctx.author, self.bot.loop)
        except Exception as e:
            return await searching.edit(content=f"Could not fetch audio: {e}")

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            player.queue.append(song)
            await searching.edit(content=f"Added to queue: **{song.title}** (position {len(player.queue)})")
        else:
            player.current = song
            ctx.voice_client.play(
                song.source,
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            )
            embed = discord.Embed(title="Now Playing", description=f"[{song.title}]({song.url})", color=discord.Color.green())
            embed.add_field(name="Duration", value=song.format_duration())
            embed.add_field(name="Requested by", value=song.requester.mention)
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            await searching.edit(content=None, embed=embed)

    @commands.command(name="pause")
    async def pause(self, ctx):
        """Pauses playback."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        """Resumes playback."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed.")
        else:
            await ctx.send("Nothing is paused.")

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        """Skips the current song."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        """Shows the current queue."""
        player = self.get_player(ctx.guild.id)
        if not player.current and not player.queue:
            return await ctx.send("Queue is empty.")
        embed = discord.Embed(title="Queue", color=discord.Color.blurple())
        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"[{player.current.title}]({player.current.url}) — {player.current.format_duration()}",
                inline=False
            )
        if player.queue:
            lines = [
                f"`{i+1}.` [{s.title}]({s.url}) — {s.format_duration()}"
                for i, s in enumerate(player.queue)
            ]
            embed.add_field(name="Up Next", value="\n".join(lines[:10]), inline=False)
            if len(player.queue) > 10:
                embed.set_footer(text=f"...and {len(player.queue) - 10} more")
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Shows the currently playing song."""
        player = self.get_player(ctx.guild.id)
        if not player.current:
            return await ctx.send("Nothing is playing.")
        song = player.current
        embed = discord.Embed(title="Now Playing", description=f"[{song.title}]({song.url})", color=discord.Color.green())
        embed.add_field(name="Duration", value=song.format_duration())
        embed.add_field(name="Requested by", value=song.requester.mention)
        embed.add_field(name="Loop", value="On" if player.loop else "Off")
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.send(embed=embed)

    @commands.command(name="loop", aliases=["l"])
    async def loop(self, ctx):
        """Toggles looping the current song."""
        player = self.get_player(ctx.guild.id)
        player.loop = not player.loop
        await ctx.send(f"Loop {'enabled' if player.loop else 'disabled'}.")

    @commands.command(name="remove")
    async def remove(self, ctx, position: int):
        """Removes a song from the queue by position."""
        player = self.get_player(ctx.guild.id)
        if not player.queue:
            return await ctx.send("The queue is empty.")
        if not 1 <= position <= len(player.queue):
            return await ctx.send(f"Position must be between 1 and {len(player.queue)}.")
        queue_list = list(player.queue)
        removed = queue_list.pop(position - 1)
        player.queue = deque(queue_list)
        await ctx.send(f"Removed **{removed.title}** from the queue.")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        """Shuffles the queue."""
        player = self.get_player(ctx.guild.id)
        if len(player.queue) < 2:
            return await ctx.send("Need at least 2 songs in the queue to shuffle.")
        import random
        queue_list = list(player.queue)
        random.shuffle(queue_list)
        player.queue = deque(queue_list)
        await ctx.send("Queue shuffled.")

    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stops playback, clears the queue, and disconnects."""
        player = self.get_player(ctx.guild.id)
        player.queue.clear()
        player.current = None
        player.loop = False
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
        await ctx.send("Stopped and disconnected.")


async def setup(bot):
    await bot.add_cog(Music(bot))
