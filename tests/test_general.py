import pytest
from unittest.mock import AsyncMock, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.general import General


@pytest.fixture
def cog(mock_bot):
    return General(mock_bot)


@pytest.mark.asyncio
async def test_ping(cog, mock_ctx):
    msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=msg)
    await cog.ping.callback(cog, mock_ctx)
    mock_ctx.send.assert_called_once_with("Pinging...")
    msg.edit.assert_called_once()
    assert "Pong!" in msg.edit.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_help_no_args(cog, mock_ctx):
    mock_cog = MagicMock()
    cmd = MagicMock()
    cmd.name = "ping"
    cmd.help = "Shows bot latency."
    cmd.hidden = False
    mock_cog.get_commands.return_value = [cmd]
    cog.bot.cogs = {"General": mock_cog}

    await cog.help_command.callback(cog, mock_ctx)
    mock_ctx.send.assert_called_once()
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert embed.title == "Megks Bot"


@pytest.mark.asyncio
async def test_help_specific_command(cog, mock_ctx):
    cmd = MagicMock()
    cmd.name = "ping"
    cmd.help = "Shows bot latency."
    cmd.aliases = ["p"]
    cog.bot.get_command = MagicMock(return_value=cmd)

    await cog.help_command.callback(cog, mock_ctx, command_name="ping")
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert "ping" in embed.title


@pytest.mark.asyncio
async def test_help_unknown_command(cog, mock_ctx):
    cog.bot.get_command = MagicMock(return_value=None)
    await cog.help_command.callback(cog, mock_ctx, command_name="nonexistent")
    mock_ctx.send.assert_called_once_with("Command `nonexistent` not found.")


@pytest.mark.asyncio
async def test_avatar_self(cog, mock_ctx):
    await cog.avatar.callback(cog, mock_ctx)
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert mock_ctx.author.display_name in embed.title


@pytest.mark.asyncio
async def test_avatar_other(cog, mock_ctx, mock_member):
    await cog.avatar.callback(cog, mock_ctx, member=mock_member)
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert mock_member.display_name in embed.title


@pytest.mark.asyncio
async def test_userinfo_self(cog, mock_ctx):
    mock_ctx.author.roles = []
    await cog.userinfo.callback(cog, mock_ctx)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_userinfo_other(cog, mock_ctx, mock_member):
    mock_member.roles = []
    await cog.userinfo.callback(cog, mock_ctx, member=mock_member)
    mock_ctx.send.assert_called_once()
