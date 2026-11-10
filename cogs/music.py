import discord
from discord.ext import commands
import yt_dlp
import asyncio
import aiohttp
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

INACTIVITY_TIMEOUT = 120

LRCLIB_API = "https://lrclib.net/api/search"
LYRICS_PAGE_SIZE = 3500
LYRICS_VIEW_TIMEOUT = 120

async def fetch_lyrics(song: str, artist: str = None):
    """Returns the first LRCLIB result that has plain lyrics, or None."""
    params = {"track_name": song, "artist_name": artist} if artist else {"q": song}
    timeout = aiohttp.ClientTimeout(total=10)
    headers = {"User-Agent": "discord-music-bot"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(LRCLIB_API, params=params) as resp:
            if resp.status != 200:
                raise aiohttp.ClientError(f"LRCLIB returned status {resp.status}")
            results = await resp.json()
    for result in results:
        if not result.get("instrumental") and (result.get("plainLyrics") or "").strip():
            return result
    return None


def paginate_lyrics(text: str, limit: int = LYRICS_PAGE_SIZE) -> list[str]:
    """Splits lyrics into pages of at most `limit` characters, on line boundaries."""
    pages = []
    current = ""
    for line in text.strip().splitlines():
        while len(line) > limit:
            if current:
                pages.append(current.rstrip("\n"))
                current = ""
            pages.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            pages.append(current.rstrip("\n"))
            current = ""
        current += line + "\n"
    if current.strip():
        pages.append(current.rstrip("\n"))
    return pages


class LyricsPaginator(discord.ui.View):
    def __init__(self, pages, title, author):
        super().__init__(timeout=LYRICS_VIEW_TIMEOUT)
        self.pages = pages
        self.title = title
        self.author = author
        self.index = 0
        self.message = None
        self._sync_buttons()

    def make_embed(self):
        embed = discord.Embed(
            title=self.title[:256],
            description=self.pages[self.index],
            color=discord.Color.blurple(),
        )
        if len(self.pages) > 1:
            embed.set_footer(text=f"Σελίδα {self.index + 1}/{len(self.pages)}")
        return embed

    def _sync_buttons(self):
        self.prev_button.disabled = self.index == 0
        self.next_button.disabled = self.index >= len(self.pages) - 1

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "Μόνο όποιος έδωσε την εντολή μπορεί να αλλάξει σελίδα.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction, button):
        self.index = max(0, self.index - 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction, button):
        self.index = min(len(self.pages) - 1, self.index + 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Song:
    def __init__(self, source, data, requester):
        self.source = source
        self.title = data.get("title", "Άγνωστο")
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

        ffmpeg_options = dict(FFMPEG_OPTIONS)
        headers = data.get("http_headers")
        if headers:
            header_lines = "".join(f"{key}: {value}\r\n" for key, value in headers.items())
            ffmpeg_options["before_options"] = f'-headers "{header_lines}" ' + ffmpeg_options["before_options"]

        source = discord.FFmpegPCMAudio(data["url"], **ffmpeg_options)
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
        self.timeout_task = None


class Music(commands.Cog):
    """Εντολές αναπαραγωγής μουσικής."""

    def __init__(self, bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    async def _disconnect_after_timeout(self, ctx):
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        player = self.get_player(ctx.guild.id)
        if ctx.voice_client and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            player.queue.clear()
            player.current = None
            player.loop = False
            player.timeout_task = None
            await ctx.voice_client.disconnect()
            await ctx.send("Αποσυνδέθηκα λόγω αδράνειας.")

    async def play_next(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player.loop and player.current:
            song = await Song.from_query(player.current.url, player.current.requester, self.bot.loop)
        elif player.queue:
            song = player.queue.popleft()
        else:
            player.current = None
            player.timeout_task = self.bot.loop.create_task(self._disconnect_after_timeout(ctx))
            return

        player.current = song
        ctx.voice_client.play(
            song.source,
            after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
        )
        embed = discord.Embed(title="Παίζει Τώρα", description=f"[{song.title}]({song.url})", color=discord.Color.green())
        embed.add_field(name="Διάρκεια", value=song.format_duration())
        embed.add_field(name="Ζητήθηκε από", value=song.requester.mention)
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.send(embed=embed)

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        """Παίζει ένα τραγούδι από URL ή αναζήτηση."""
        if not ctx.author.voice:
            return await ctx.send("Δεν είσαι σε voice channel.")
        if ctx.voice_client and ctx.voice_client.is_playing() and ctx.voice_client.channel != ctx.author.voice.channel:
            return await ctx.send(f"Παίζω ήδη μουσική στο **{ctx.voice_client.channel.name}**.")
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        player = self.get_player(ctx.guild.id)
        searching = await ctx.send(f"Αναζήτηση για `{query}`...")
        try:
            song = await Song.from_query(query, ctx.author, self.bot.loop)
        except Exception as e:
            return await searching.edit(content=f"Δεν ήταν δυνατή η ανάκτηση: {e}")

        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            player.queue.append(song)
            await searching.edit(content=f"Προστέθηκε στην ουρά: **{song.title}** (θέση {len(player.queue)})")
        else:
            if player.timeout_task:
                player.timeout_task.cancel()
                player.timeout_task = None
            player.current = song
            ctx.voice_client.play(
                song.source,
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            )
            embed = discord.Embed(title="Παίζει Τώρα", description=f"[{song.title}]({song.url})", color=discord.Color.green())
            embed.add_field(name="Διάρκεια", value=song.format_duration())
            embed.add_field(name="Ζητήθηκε από", value=song.requester.mention)
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            await searching.edit(content=None, embed=embed)

    @commands.command(name="pause")
    async def pause(self, ctx):
        """Παγώνει την αναπαραγωγή."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Παύση.")
        else:
            await ctx.send("Δεν παίζει τίποτα.")

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        """Συνεχίζει την αναπαραγωγή."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Συνέχιση.")
        else:
            await ctx.send("Δεν υπάρχει κάτι σε παύση.")

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        """Παρακάμπτει το τρέχον τραγούδι."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Παρακάμφθηκε.")
        else:
            await ctx.send("Δεν παίζει τίποτα.")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        """Δείχνει την τρέχουσα ουρά."""
        player = self.get_player(ctx.guild.id)
        if not player.current and not player.queue:
            return await ctx.send("Η ουρά είναι άδεια.")
        embed = discord.Embed(title="Ουρά", color=discord.Color.blurple())
        if player.current:
            embed.add_field(
                name="Παίζει Τώρα",
                value=f"[{player.current.title}]({player.current.url}) — {player.current.format_duration()}",
                inline=False
            )
        if player.queue:
            lines = [
                f"`{i+1}.` [{s.title}]({s.url}) — {s.format_duration()}"
                for i, s in enumerate(player.queue)
            ]
            embed.add_field(name="Επόμενα", value="\n".join(lines[:10]), inline=False)
            if len(player.queue) > 10:
                embed.set_footer(text=f"...και {len(player.queue) - 10} ακόμα")
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Δείχνει το τραγούδι που παίζει τώρα."""
        player = self.get_player(ctx.guild.id)
        if not player.current:
            return await ctx.send("Δεν παίζει τίποτα.")
        song = player.current
        embed = discord.Embed(title="Παίζει Τώρα", description=f"[{song.title}]({song.url})", color=discord.Color.green())
        embed.add_field(name="Διάρκεια", value=song.format_duration())
        embed.add_field(name="Ζητήθηκε από", value=song.requester.mention)
        embed.add_field(name="Επανάληψη", value="Ναι" if player.loop else "Όχι")
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.send(embed=embed)

    @commands.command(name="lyrics", aliases=["ly"])
    async def lyrics(self, ctx, song: str, *, artist: str = None):
        """Δείχνει τους στίχους ενός τραγουδιού. Χρήση: !lyrics "τίτλος" [καλλιτέχνης]"""
        try:
            async with ctx.typing():
                result = await fetch_lyrics(song, artist)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await ctx.send("Δεν ήταν δυνατή η ανάκτηση, δοκίμασε ξανά αργότερα.")

        if not result:
            label = f"{song} - {artist}" if artist else song
            return await ctx.send(f"Δεν βρέθηκαν στίχοι για: `{label}`")

        pages = paginate_lyrics(result["plainLyrics"])
        track_name = result.get("trackName") or song
        artist_name = result.get("artistName") or ""
        # LRCLIB track names sometimes already include the artist ("Song - Artist")
        title = track_name if artist_name.lower() in track_name.lower() else f"{track_name} - {artist_name}"
        view = LyricsPaginator(pages, title, ctx.author)
        if len(pages) == 1:
            return await ctx.send(embed=view.make_embed())
        view.message = await ctx.send(embed=view.make_embed(), view=view)

    @commands.command(name="loop", aliases=["l"])
    async def loop(self, ctx):
        """Ενεργοποιεί/απενεργοποιεί την επανάληψη του τραγουδιού."""
        player = self.get_player(ctx.guild.id)
        player.loop = not player.loop
        await ctx.send(f"Επανάληψη {'ενεργοποιήθηκε' if player.loop else 'απενεργοποιήθηκε'}.")

    @commands.command(name="remove")
    async def remove(self, ctx, position: int):
        """Αφαιρεί ένα τραγούδι από την ουρά μέσω θέσης."""
        player = self.get_player(ctx.guild.id)
        if not player.queue:
            return await ctx.send("Η ουρά είναι άδεια.")
        if not 1 <= position <= len(player.queue):
            return await ctx.send(f"Η θέση πρέπει να είναι μεταξύ 1 και {len(player.queue)}.")
        queue_list = list(player.queue)
        removed = queue_list.pop(position - 1)
        player.queue = deque(queue_list)
        await ctx.send(f"Αφαιρέθηκε το **{removed.title}** από την ουρά.")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        """Ανακατεύει την ουρά."""
        player = self.get_player(ctx.guild.id)
        if len(player.queue) < 2:
            return await ctx.send("Χρειάζονται τουλάχιστον 2 τραγούδια στην ουρά για ανακάτεμα.")
        import random
        queue_list = list(player.queue)
        random.shuffle(queue_list)
        player.queue = deque(queue_list)
        await ctx.send("Η ουρά ανακατεύτηκε.")

    @commands.command(name="stop")
    async def stop(self, ctx):
        """Σταματάει την αναπαραγωγή, καθαρίζει την ουρά και αποσυνδέεται."""
        player = self.get_player(ctx.guild.id)
        if player.timeout_task:
            player.timeout_task.cancel()
            player.timeout_task = None
        player.queue.clear()
        player.current = None
        player.loop = False
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
        await ctx.send("Σταμάτησε και αποσυνδέθηκε.")


async def setup(bot):
    await bot.add_cog(Music(bot))