import pytest
import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock, PropertyMock


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.latency = 0.05
    bot.guilds = [MagicMock(member_count=10)]
    bot.is_owner = AsyncMock(return_value=True)
    bot.loop = asyncio.new_event_loop()
    bot.cogs = {}
    bot.user = MagicMock()
    bot.user.display_avatar.url = "https://example.com/bot.png"
    return bot


@pytest.fixture
def mock_role_low():
    role = MagicMock(spec=discord.Role)
    role.position = 1
    role.__ge__ = lambda self, other: self.position >= other.position
    role.__lt__ = lambda self, other: self.position < other.position
    return role


@pytest.fixture
def mock_role_high():
    role = MagicMock(spec=discord.Role)
    role.position = 10
    role.__ge__ = lambda self, other: self.position >= other.position
    role.__lt__ = lambda self, other: self.position < other.position
    return role


@pytest.fixture
def mock_author(mock_role_high):
    member = MagicMock(spec=discord.Member)
    member.id = 111
    member.display_name = "TestUser"
    member.mention = "<@111>"
    member.nick = None
    member.color = discord.Color.default()
    member.top_role = mock_role_high
    member.roles = []
    member.display_avatar = MagicMock()
    member.display_avatar.url = "https://example.com/avatar.png"
    member.joined_at = discord.utils.utcnow()
    member.created_at = discord.utils.utcnow()
    member.voice = MagicMock()
    member.voice.channel = MagicMock(spec=discord.VoiceChannel)
    member.voice.channel.connect = AsyncMock()
    member.voice.channel.name = "General"
    return member


@pytest.fixture
def mock_member(mock_role_low):
    member = MagicMock(spec=discord.Member)
    member.id = 222
    member.display_name = "TargetUser"
    member.mention = "<@222>"
    member.nick = None
    member.color = discord.Color.default()
    member.top_role = mock_role_low
    member.roles = []
    member.display_avatar = MagicMock()
    member.display_avatar.url = "https://example.com/avatar2.png"
    member.joined_at = discord.utils.utcnow()
    member.created_at = discord.utils.utcnow()
    member.kick = AsyncMock()
    member.ban = AsyncMock()
    member.timeout = AsyncMock()
    member.voice = None
    return member


@pytest.fixture
def mock_voice_client():
    vc = MagicMock(spec=discord.VoiceClient)
    vc.is_playing = MagicMock(return_value=False)
    vc.is_paused = MagicMock(return_value=False)
    vc.stop = MagicMock()
    vc.pause = MagicMock()
    vc.resume = MagicMock()
    vc.play = MagicMock()
    vc.disconnect = AsyncMock()
    vc.channel = MagicMock(spec=discord.VoiceChannel)
    vc.channel.name = "Music"
    return vc


@pytest.fixture
def mock_ctx(mock_author, mock_bot):
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.typing = MagicMock()
    ctx.typing.return_value.__aenter__ = AsyncMock(return_value=None)
    ctx.typing.return_value.__aexit__ = AsyncMock(return_value=False)
    ctx.prefix = "!"
    ctx.author = mock_author
    ctx.bot = mock_bot
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 99999
    ctx.guild.default_role = MagicMock()
    ctx.guild.bans = MagicMock()
    ctx.guild.unban = AsyncMock()
    ctx.channel = MagicMock()
    ctx.channel.purge = AsyncMock(return_value=[MagicMock()] * 6)
    ctx.voice_client = None
    return ctx