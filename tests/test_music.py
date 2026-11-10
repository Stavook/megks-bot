import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import aiohttp
from unittest.mock import PropertyMock

import cogs.music as music_module
from cogs.music import (
    Music, GuildPlayer, Song, LyricsPaginator, SearchPicker, paginate_lyrics,
    parse_lyrics_query, is_url, search_candidates, format_seconds,
    FETCH_ERROR, SEARCH_ERROR, CONNECT_ERROR,
)


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
        await cog.play.callback(cog, mock_ctx, query="https://www.youtube.com/watch?v=abc123")

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
        await cog.play.callback(cog, mock_ctx, query="https://www.youtube.com/watch?v=abc123")

    mock_voice_client.play.assert_called_once()
    assert cog.get_player(mock_ctx.guild.id).current == song


@pytest.mark.asyncio
async def test_play_fetch_error(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.channel = mock_ctx.author.voice.channel

    searching_msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=searching_msg)

    with patch("cogs.music.Song.from_query", AsyncMock(side_effect=Exception("Network error"))):
        await cog.play.callback(cog, mock_ctx, query="https://www.youtube.com/watch?v=abc123")

    assert "ανάκτηση" in searching_msg.edit.call_args.kwargs["content"]
    assert "Network error" not in searching_msg.edit.call_args.kwargs["content"]


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

# --- lyrics helpers ---

def make_lrclib_session(status=200, results=None, error=None):
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=results if results is not None else [])
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    session = AsyncMock()
    session.get = MagicMock(return_value=response, side_effect=error)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


def lrclib_result(lyrics="line one\nline two", track="Song", artist="Artist", instrumental=False):
    return {"trackName": track, "artistName": artist, "plainLyrics": lyrics, "instrumental": instrumental}


def test_paginate_lyrics_short():
    assert paginate_lyrics("a\nb\nc") == ["a\nb\nc"]


def test_paginate_lyrics_splits_on_lines_within_limit():
    text = "\n".join(["x" * 40] * 30)
    pages = paginate_lyrics(text, limit=200)
    assert len(pages) > 1
    assert all(len(p) <= 200 for p in pages)
    assert "\n".join(pages) == text


def test_paginate_lyrics_splits_overlong_line():
    pages = paginate_lyrics("y" * 450, limit=200)
    assert [len(p) for p in pages] == [200, 200, 50]


# --- lyrics ---

@pytest.mark.asyncio
async def test_lyrics_song_only(cog, mock_ctx):
    session = make_lrclib_session(results=[lrclib_result(track="Track", artist="Artist")])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="some song")
    assert session.get.call_args.kwargs["params"] == {"q": "some song"}
    kwargs = mock_ctx.send.call_args.kwargs
    assert kwargs["embed"].title == "Track - Artist"
    assert kwargs["embed"].description == "line one\nline two"
    assert "view" not in kwargs


@pytest.mark.asyncio
async def test_lyrics_title_does_not_repeat_artist(cog, mock_ctx):
    session = make_lrclib_session(results=[lrclib_result(track="Song - Artist", artist="Artist")])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="song")
    assert mock_ctx.send.call_args.kwargs["embed"].title == "Song - Artist"


@pytest.mark.asyncio
async def test_lyrics_song_and_artist(cog, mock_ctx):
    session = make_lrclib_session(results=[lrclib_result()])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="some song | some artist")
    assert session.get.call_args.kwargs["params"] == {
        "track_name": "some song", "artist_name": "some artist",
    }


@pytest.mark.asyncio
async def test_lyrics_ignores_current_song(cog, mock_ctx):
    cog.get_player(mock_ctx.guild.id).current = make_song(title="Playing Now")
    session = make_lrclib_session(results=[lrclib_result()])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="other")
    assert session.get.call_args.kwargs["params"] == {"q": "other"}


@pytest.mark.asyncio
async def test_lyrics_not_found(cog, mock_ctx):
    session = make_lrclib_session(results=[])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="gibberish")
    assert "Δεν βρέθηκαν" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_lyrics_skips_instrumental_results(cog, mock_ctx):
    session = make_lrclib_session(results=[lrclib_result(lyrics="", instrumental=True)])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="instrumental")
    assert "Δεν βρέθηκαν" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_lyrics_api_error_status(cog, mock_ctx):
    session = make_lrclib_session(status=500)
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="x")
    assert "ανάκτηση" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_lyrics_network_error(cog, mock_ctx):
    session = make_lrclib_session(error=aiohttp.ClientConnectionError())
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="x")
    assert "ανάκτηση" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_lyrics_long_paginates(cog, mock_ctx):
    long_lyrics = "\n".join(["la la la la la la la la"] * 600)
    session = make_lrclib_session(results=[lrclib_result(lyrics=long_lyrics)])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="long")
    kwargs = mock_ctx.send.call_args.kwargs
    view = kwargs["view"]
    assert isinstance(view, LyricsPaginator)
    assert len(view.pages) > 1
    assert "Σελίδα 1/" in kwargs["embed"].footer.text
    assert view.prev_button.disabled and not view.next_button.disabled


@pytest.mark.asyncio
async def test_lyrics_paginator_only_author_can_press(mock_author):
    view = LyricsPaginator(["a", "b"], "T", mock_author)
    intruder = MagicMock()
    intruder.user.id = 999
    intruder.response.send_message = AsyncMock()
    assert await view.interaction_check(intruder) is False
    owner = MagicMock()
    owner.user.id = mock_author.id
    assert await view.interaction_check(owner) is True


@pytest.mark.asyncio
async def test_lyrics_paginator_next_and_prev(mock_author):
    view = LyricsPaginator(["a", "b", "c"], "T", mock_author)
    interaction = MagicMock()
    interaction.response.edit_message = AsyncMock()
    await view.next_button.callback(interaction)
    assert view.index == 1
    await view.next_button.callback(interaction)
    assert view.index == 2 and view.next_button.disabled
    await view.prev_button.callback(interaction)
    assert view.index == 1



# --- lyrics: free-text parsing ---

@pytest.mark.parametrize("raw, expected", [
    ("where the hood at", ("where the hood at", None)),
    ("dmx where the hood at", ("dmx where the hood at", None)),
    ("where the hood at | dmx", ("where the hood at", "dmx")),
    ("  where the hood at   |   dmx  ", ("where the hood at", "dmx")),
    ('"bohemian rhapsody" queen', ("bohemian rhapsody queen", None)),
    ("song |", ("song", None)),
    ("| artist", ("", "artist")),
    ("a | b | c", ("a", "b | c")),
])
def test_parse_lyrics_query(raw, expected):
    assert parse_lyrics_query(raw) == expected


@pytest.mark.asyncio
async def test_lyrics_multiword_without_artist_is_one_query(cog, mock_ctx):
    """Regression: `!lyrics dmx where the hood at` used to split into song=dmx, artist=where the hood at."""
    session = make_lrclib_session(results=[lrclib_result()])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="dmx where the hood at")
    assert session.get.call_count == 1
    assert session.get.call_args.kwargs["params"] == {"q": "dmx where the hood at"}


@pytest.mark.asyncio
async def test_lyrics_pipe_artist_uses_exact_match(cog, mock_ctx):
    session = make_lrclib_session(results=[lrclib_result()])
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="where the hood at | dmx")
    assert session.get.call_args.kwargs["params"] == {"track_name": "where the hood at", "artist_name": "dmx"}


@pytest.mark.asyncio
async def test_lyrics_artist_search_falls_back_to_combined_query(cog, mock_ctx):
    def response(results):
        r = AsyncMock()
        r.status = 200
        r.json = AsyncMock(return_value=results)
        r.__aenter__ = AsyncMock(return_value=r)
        r.__aexit__ = AsyncMock(return_value=False)
        return r

    session = AsyncMock()
    session.get = MagicMock(side_effect=[response([]), response([lrclib_result(track="Where the Hood At?", artist="DMX")])])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.lyrics.callback(cog, mock_ctx, query="where the hood at | dmx")
    assert [c.kwargs["params"] for c in session.get.call_args_list] == [
        {"track_name": "where the hood at", "artist_name": "dmx"},
        {"q": "where the hood at dmx"},
    ]
    assert mock_ctx.send.call_args.kwargs["embed"].title == "Where the Hood At? - DMX"


@pytest.mark.asyncio
async def test_lyrics_empty_song_is_rejected(cog, mock_ctx):
    with patch("aiohttp.ClientSession") as client:
        await cog.lyrics.callback(cog, mock_ctx, query="| dmx")
    client.assert_not_called()
    assert "τίτλο" in mock_ctx.send.call_args.args[0]


# --- helpers ---

@pytest.mark.parametrize("text, expected", [
    ("https://www.youtube.com/watch?v=abc", True),
    ("http://youtu.be/abc", True),
    ("  https://youtu.be/abc  ", True),
    ("daft punk one more time", False),
    ("https://example.com with spaces", False),
    ("youtube.com/watch?v=abc", False),
])
def test_is_url(text, expected):
    assert is_url(text) is expected


def test_format_seconds():
    assert format_seconds(185) == "3:05"
    assert format_seconds(3661) == "1:01:01"
    assert format_seconds(185.7) == "3:05"
    assert format_seconds(None) == "0:00"


# --- search_candidates ---

def entry(vid, title=None, uploader="Chan", duration=200):
    return {"id": vid, "title": title or f"Title {vid}", "uploader": uploader, "duration": duration}


def fake_ytdl(results_by_query):
    ytdl = MagicMock()

    def extract_info(query, download=False):
        value = results_by_query[query]
        if isinstance(value, Exception):
            raise value
        return {"entries": value}

    ytdl.extract_info.side_effect = extract_info
    return ytdl


@pytest.mark.asyncio
async def test_search_short_query_runs_one_search():
    ytdl = fake_ytdl({"ytsearch5:daft punk": [entry("a"), entry("b")]})
    with patch.object(music_module, "ytdl_search", ytdl):
        result = await search_candidates("daft punk", asyncio.get_running_loop())
    assert [c["id"] for c in result] == ["a", "b"]
    assert ytdl.extract_info.call_count == 1


@pytest.mark.asyncio
async def test_search_long_query_adds_lyrics_variant_interleaved_and_deduped():
    q = "caught in a landslide no escape"
    ytdl = fake_ytdl({
        f"ytsearch5:{q}": [entry("a"), entry("b"), entry("c")],
        f"ytsearch5:{q} lyrics": [entry("b"), entry("d"), entry("a")],
    })
    with patch.object(music_module, "ytdl_search", ytdl):
        result = await search_candidates(q, asyncio.get_running_loop())
    assert [c["id"] for c in result] == ["a", "b", "d", "c"]
    assert ytdl.extract_info.call_count == 2


@pytest.mark.asyncio
async def test_search_caps_at_limit_and_builds_urls():
    ytdl = fake_ytdl({"ytsearch3:x": [entry(str(i)) for i in range(10)]})
    with patch.object(music_module, "ytdl_search", ytdl):
        result = await search_candidates("x", asyncio.get_running_loop(), limit=3)
    assert len(result) == 3
    assert result[0]["url"] == "https://www.youtube.com/watch?v=0"


@pytest.mark.asyncio
async def test_search_tolerates_one_failed_variant():
    q = "one two three four"
    ytdl = fake_ytdl({f"ytsearch5:{q}": [entry("a")], f"ytsearch5:{q} lyrics": RuntimeError("blocked")})
    with patch.object(music_module, "ytdl_search", ytdl):
        result = await search_candidates(q, asyncio.get_running_loop())
    assert [c["id"] for c in result] == ["a"]


@pytest.mark.asyncio
async def test_search_raises_when_every_search_fails():
    ytdl = fake_ytdl({"ytsearch5:x": RuntimeError("blocked")})
    with patch.object(music_module, "ytdl_search", ytdl):
        with pytest.raises(RuntimeError):
            await search_candidates("x", asyncio.get_running_loop())


@pytest.mark.asyncio
async def test_search_skips_entries_without_id_and_uses_channel_fallback():
    ytdl = fake_ytdl({"ytsearch5:x": [None, {"title": "no id"}, {"id": "ok", "channel": "Some Channel"}]})
    with patch.object(music_module, "ytdl_search", ytdl):
        result = await search_candidates("x", asyncio.get_running_loop())
    assert len(result) == 1
    assert result[0]["uploader"] == "Some Channel"
    assert result[0]["title"] == "Άγνωστο"


# --- play: search picker ---

def make_candidates(n=3):
    return [
        {"id": str(i), "title": f"Song {i}", "url": f"https://www.youtube.com/watch?v={i}",
         "duration": 200, "uploader": f"Chan {i}"}
        for i in range(n)
    ]


@pytest.fixture
def play_env(cog, mock_ctx, mock_voice_client):
    mock_ctx.voice_client = mock_voice_client
    mock_voice_client.is_playing.return_value = False
    mock_voice_client.is_paused.return_value = False
    mock_voice_client.channel = mock_ctx.author.voice.channel
    status = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=status)
    return status


@pytest.mark.asyncio
async def test_play_text_query_shows_picker(cog, mock_ctx, play_env):
    status = play_env
    with patch("cogs.music.search_candidates", AsyncMock(return_value=make_candidates(3))), \
         patch("cogs.music.Song.from_query", AsyncMock()) as from_query:
        await cog.play.callback(cog, mock_ctx, query="some lyrics i remember")
    view = status.edit.call_args.kwargs["view"]
    assert isinstance(view, SearchPicker)
    assert [o.label for o in view.select.options] == ["Song 0", "Song 1", "Song 2"]
    assert view.select.options[0].description == "Chan 0 • 3:20"
    assert view.message is status
    from_query.assert_not_called()       # nothing plays until the user picks


@pytest.mark.asyncio
async def test_play_text_query_does_not_connect_before_pick(cog, mock_ctx, play_env):
    mock_ctx.voice_client = None
    with patch("cogs.music.search_candidates", AsyncMock(return_value=make_candidates(3))):
        await cog.play.callback(cog, mock_ctx, query="some lyrics i remember")
    mock_ctx.author.voice.channel.connect.assert_not_called()


@pytest.mark.asyncio
async def test_play_single_result_plays_directly(cog, mock_ctx, play_env, mock_voice_client):
    candidates = make_candidates(1)
    song = make_song()
    with patch("cogs.music.search_candidates", AsyncMock(return_value=candidates)), \
         patch("cogs.music.Song.from_query", AsyncMock(return_value=song)) as from_query:
        await cog.play.callback(cog, mock_ctx, query="rare song")
    assert from_query.call_args.args[0] == candidates[0]["url"]
    mock_voice_client.play.assert_called_once()


@pytest.mark.asyncio
async def test_play_no_results(cog, mock_ctx, play_env):
    with patch("cogs.music.search_candidates", AsyncMock(return_value=[])):
        await cog.play.callback(cog, mock_ctx, query="zzzz")
    assert "Δεν βρέθηκαν αποτελέσματα" in play_env.edit.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_play_search_error_is_generic(cog, mock_ctx, play_env):
    with patch("cogs.music.search_candidates", AsyncMock(side_effect=RuntimeError("secret yt-dlp detail"))):
        await cog.play.callback(cog, mock_ctx, query="anything")
    assert play_env.edit.call_args.kwargs["content"] == SEARCH_ERROR


@pytest.mark.asyncio
async def test_play_url_skips_search(cog, mock_ctx, play_env, mock_voice_client):
    with patch("cogs.music.search_candidates", AsyncMock()) as search, \
         patch("cogs.music.Song.from_query", AsyncMock(return_value=make_song())):
        await cog.play.callback(cog, mock_ctx, query="https://youtu.be/abc")
    search.assert_not_called()
    mock_voice_client.play.assert_called_once()


async def open_picker(cog, mock_ctx, status, n=3):
    with patch("cogs.music.search_candidates", AsyncMock(return_value=make_candidates(n))):
        await cog.play.callback(cog, mock_ctx, query="some lyrics i remember")
    return status.edit.call_args.kwargs["view"]


def pick(picker, index):
    interaction = MagicMock()
    interaction.response.edit_message = AsyncMock()
    return interaction, patch.object(type(picker.select), "values", new_callable=PropertyMock, return_value=[str(index)])


@pytest.mark.asyncio
async def test_picker_selection_plays_chosen_song(cog, mock_ctx, play_env, mock_voice_client):
    picker = await open_picker(cog, mock_ctx, play_env)
    interaction, values = pick(picker, 1)
    song = make_song("Chosen")
    with values, patch("cogs.music.Song.from_query", AsyncMock(return_value=song)) as from_query:
        await picker._on_pick(interaction)
    assert interaction.response.edit_message.call_args.kwargs["view"] is None
    assert "Song 1" in interaction.response.edit_message.call_args.kwargs["content"]
    assert from_query.call_args.args[0] == "https://www.youtube.com/watch?v=1"
    mock_voice_client.play.assert_called_once()


@pytest.mark.asyncio
async def test_picker_selection_queues_when_already_playing(cog, mock_ctx, play_env, mock_voice_client):
    picker = await open_picker(cog, mock_ctx, play_env)
    mock_voice_client.is_playing.return_value = True
    interaction, values = pick(picker, 0)
    with values, patch("cogs.music.Song.from_query", AsyncMock(return_value=make_song())):
        await picker._on_pick(interaction)
    assert len(cog.get_player(mock_ctx.guild.id).queue) == 1
    mock_voice_client.play.assert_not_called()


@pytest.mark.asyncio
async def test_picker_selection_after_leaving_voice(cog, mock_ctx, play_env, mock_voice_client):
    picker = await open_picker(cog, mock_ctx, play_env)
    mock_ctx.author.voice = None
    interaction, values = pick(picker, 0)
    with values, patch("cogs.music.Song.from_query", AsyncMock()) as from_query:
        await picker._on_pick(interaction)
    from_query.assert_not_called()
    mock_voice_client.play.assert_not_called()
    assert "voice channel" in play_env.edit.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_picker_only_author_can_use(cog, mock_ctx, play_env):
    picker = await open_picker(cog, mock_ctx, play_env)
    intruder = MagicMock()
    intruder.user.id = 999
    intruder.response.send_message = AsyncMock()
    assert await picker.interaction_check(intruder) is False
    assert intruder.response.send_message.call_args.kwargs["ephemeral"] is True
    owner = MagicMock()
    owner.user.id = mock_ctx.author.id
    assert await picker.interaction_check(owner) is True


@pytest.mark.asyncio
async def test_picker_timeout_expires_message(cog, mock_ctx, play_env):
    picker = await open_picker(cog, mock_ctx, play_env)
    await picker.on_timeout()
    kwargs = play_env.edit.call_args.kwargs
    assert "έληξε" in kwargs["content"] and kwargs["view"] is None


@pytest.mark.asyncio
async def test_picker_option_limits(mock_author):
    candidates = [{"id": "1", "title": "T" * 300, "url": "u", "duration": None, "uploader": None}]
    picker = SearchPicker(mock_author, candidates, AsyncMock())
    assert len(picker.select.options[0].label) == 100
    assert picker.select.options[0].description is None


@pytest.mark.asyncio
async def test_play_connect_failure_is_clean(cog, mock_ctx, play_env):
    mock_ctx.voice_client = None
    mock_ctx.author.voice.channel.connect = AsyncMock(side_effect=Exception("opus lib missing"))
    await cog.play.callback(cog, mock_ctx, query="https://youtu.be/abc")
    assert play_env.edit.call_args.kwargs["content"] == CONNECT_ERROR
