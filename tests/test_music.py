import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.music import Music, GuildPlayer, Song


@pytest.fixture
def cog(mock_bot):
    return Music(mock_bot)


def make_song(title="Test Song", url="https://example.com", duration=180):
    song = MagicMock(spec=Song)
    song.title = title
    song.url = url
    song.duration = duration
    song.thumbnail = None
    song.requester = MagicMock()
    song.requester.mention = "<@111>"
    song.format_duration = MagicMock(return_value="3:00")
    song.source = MagicMock()
    return song


# --- Song.format_duration ---

def test_format_duration_minutes():
    song = Song.__new__(Song)
    song.duration = 185
    assert song.format_duration() == "3:05"


def test_format_duration_hours():
    song = Song.__new__(Song)
    song.duration = 3661
    assert song.format_duration() == "1:01:01"


# --- GuildPlayer ---

def test_guild_player_defaults():
    player = GuildPlayer()
    assert isinstance(player.queue, deque)
    assert player.current is None
    assert player.loop is False


# --- play ---

@pytest.mark.asyncio
async def test_play_not_in_voice(cog, mock_ctx):
    mock_ctx.author.voice = None
    await cog.play.callback(cog, mock_ctx, query="test song")
    assert "voice channel" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_play_already_playing_different_channel(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_playing.return_value = True
    mock_voice_client.channel = MagicMock()
    mock_ctx.author.voice.channel = MagicMock()

    await cog.play.callback(cog, mock_ctx, query="test")
    assert "Παίζω ήδη" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_play_adds_to_queue(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_playing.return_value = True
    mock_voice_client.is_paused.return_value = False
    mock_voice_client.channel = mock_ctx.author.voice.channel

    searching_msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=searching_msg)

    song = make_song()
    with patch("cogs.music.Song.from_query", AsyncMock(return_value=song)):
        await cog.play.callback(cog, mock_ctx, query="test song")

    player = cog.get_player(mock_ctx.guild.id)
    assert len(player.queue) == 1
    assert "Προστέθηκε" in searching_msg.edit.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_play_starts_playback(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_playing.return_value = False
    mock_voice_client.is_paused.return_value = False
    mock_voice_client.channel = mock_ctx.author.voice.channel

    searching_msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=searching_msg)

    song = make_song()
    with patch("cogs.music.Song.from_query", AsyncMock(return_value=song)):
        await cog.play.callback(cog, mock_ctx, query="test song")

    mock_voice_client.play.assert_called_once()
    assert cog.get_player(mock_ctx.guild.id).current == song


@pytest.mark.asyncio
async def test_play_fetch_error(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.channel = mock_ctx.author.voice.channel

    searching_msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=searching_msg)

    with patch("cogs.music.Song.from_query", AsyncMock(side_effect=Exception("Network error"))):
        await cog.play.callback(cog, mock_ctx, query="bad query")

    assert "ανάκτηση" in searching_msg.edit.call_args.kwargs["content"]


# --- pause ---

@pytest.mark.asyncio
async def test_pause_while_playing(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_playing.return_value = True
    await cog.pause.callback(cog, mock_ctx)
    mock_voice_client.pause.assert_called_once()
    assert mock_ctx.send.call_args.args[0] == "Παύση."


@pytest.mark.asyncio
async def test_pause_nothing_playing(cog, mock_ctx):
    await cog.pause.callback(cog, mock_ctx)
    assert mock_ctx.send.call_args.args[0] == "Δεν παίζει τίποτα."


# --- resume ---

@pytest.mark.asyncio
async def test_resume_while_paused(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_paused.return_value = True
    await cog.resume.callback(cog, mock_ctx)
    mock_voice_client.resume.assert_called_once()
    assert "Συνέχιση" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_resume_nothing_paused(cog, mock_ctx):
    await cog.resume.callback(cog, mock_ctx)
    assert "παύση" in mock_ctx.send.call_args.args[0]


# --- skip ---

@pytest.mark.asyncio
async def test_skip_while_playing(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_playing.return_value = True
    await cog.skip.callback(cog, mock_ctx)
    mock_voice_client.stop.assert_called_once()
    assert "Παρακάμφθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_skip_nothing_playing(cog, mock_ctx):
    await cog.skip.callback(cog, mock_ctx)
    assert "Δεν παίζει" in mock_ctx.send.call_args.args[0]


# --- queue ---

@pytest.mark.asyncio
async def test_queue_empty(cog, mock_ctx):
    await cog.queue.callback(cog, mock_ctx)
    assert "άδεια" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_queue_with_songs(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    player.current = make_song("Current Song")
    player.queue.append(make_song("Next Song"))
    await cog.queue.callback(cog, mock_ctx)
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert embed.title == "Ουρά"


# --- nowplaying ---

@pytest.mark.asyncio
async def test_nowplaying_nothing(cog, mock_ctx):
    await cog.nowplaying.callback(cog, mock_ctx)
    assert "Δεν παίζει" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_nowplaying_with_song(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    player.current = make_song()
    await cog.nowplaying.callback(cog, mock_ctx)
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert embed.title == "Παίζει Τώρα"


# --- loop ---

@pytest.mark.asyncio
async def test_loop_toggle(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    assert player.loop is False
    await cog.loop.callback(cog, mock_ctx)
    assert player.loop is True
    await cog.loop.callback(cog, mock_ctx)
    assert player.loop is False


# --- stop ---

@pytest.mark.asyncio
async def test_stop_clears_and_disconnects(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    player = cog.get_player(mock_ctx.guild.id)
    player.current = make_song()
    player.queue.append(make_song("Next"))
    player.loop = True

    await cog.stop.callback(cog, mock_ctx)

    assert player.current is None
    assert len(player.queue) == 0
    assert player.loop is False
    mock_voice_client.stop.assert_called_once()
    mock_voice_client.disconnect.assert_called_once()
    assert "Σταμάτησε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_stop_no_voice_client(cog, mock_ctx):
    await cog.stop.callback(cog, mock_ctx)
    assert "Σταμάτησε" in mock_ctx.send.call_args.args[0]


# --- remove ---

@pytest.mark.asyncio
async def test_remove_success(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    player.queue.append(make_song("Song A"))
    player.queue.append(make_song("Song B"))
    player.queue.append(make_song("Song C"))

    await cog.remove.callback(cog, mock_ctx, 2)

    assert len(player.queue) == 2
    titles = [s.title for s in player.queue]
    assert "Song B" not in titles
    assert "Αφαιρέθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_remove_empty_queue(cog, mock_ctx):
    await cog.remove.callback(cog, mock_ctx, 1)
    assert "άδεια" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_remove_out_of_range(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    player.queue.append(make_song())
    await cog.remove.callback(cog, mock_ctx, 5)
    assert "θέση" in mock_ctx.send.call_args.args[0]


# --- shuffle ---

@pytest.mark.asyncio
async def test_shuffle_success(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    for i in range(5):
        player.queue.append(make_song(f"Song {i}"))

    await cog.shuffle.callback(cog, mock_ctx)

    assert len(player.queue) == 5
    assert "ανακατεύτηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_shuffle_too_few(cog, mock_ctx):
    player = cog.get_player(mock_ctx.guild.id)
    player.queue.append(make_song())
    await cog.shuffle.callback(cog, mock_ctx)
    assert "τουλάχιστον 2" in mock_ctx.send.call_args.args[0]