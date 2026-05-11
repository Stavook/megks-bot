import pytest
from unittest.mock import AsyncMock, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.moderation import Moderation


@pytest.fixture
def cog(mock_bot):
    return Moderation(mock_bot)


# --- kick ---

@pytest.mark.asyncio
async def test_kick_success(cog, mock_ctx, mock_member):
    await cog.kick.callback(cog, mock_ctx, mock_member, reason="test")
    mock_member.kick.assert_called_once()
    assert "Kicked" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_kick_self(cog, mock_ctx):
    await cog.kick.callback(cog, mock_ctx, mock_ctx.author)
    mock_ctx.send.assert_called_once_with("You can't kick yourself.")


@pytest.mark.asyncio
async def test_kick_higher_role(cog, mock_ctx, mock_member, mock_role_high):
    mock_member.top_role = mock_role_high
    await cog.kick.callback(cog, mock_ctx, mock_member)
    mock_ctx.send.assert_called_once_with("You can't kick someone with an equal or higher role.")
    mock_member.kick.assert_not_called()


# --- ban ---

@pytest.mark.asyncio
async def test_ban_success(cog, mock_ctx, mock_member):
    await cog.ban.callback(cog, mock_ctx, mock_member, reason="test")
    mock_member.ban.assert_called_once()
    assert "Banned" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_ban_self(cog, mock_ctx):
    await cog.ban.callback(cog, mock_ctx, mock_ctx.author)
    mock_ctx.send.assert_called_once_with("You can't ban yourself.")


@pytest.mark.asyncio
async def test_ban_higher_role(cog, mock_ctx, mock_member, mock_role_high):
    mock_member.top_role = mock_role_high
    await cog.ban.callback(cog, mock_ctx, mock_member)
    mock_ctx.send.assert_called_once_with("You can't ban someone with an equal or higher role.")
    mock_member.ban.assert_not_called()


# --- unban ---

@pytest.mark.asyncio
async def test_unban_found(cog, mock_ctx):
    banned_user = MagicMock()
    banned_user.id = 999
    banned_user.__str__ = lambda self: "BannedUser#0000"
    entry = MagicMock()
    entry.user = banned_user

    async def fake_bans():
        yield entry

    mock_ctx.guild.bans = MagicMock(return_value=fake_bans())
    await cog.unban.callback(cog, mock_ctx, user="BannedUser#0000")
    mock_ctx.guild.unban.assert_called_once_with(banned_user)
    assert "Unbanned" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_unban_not_found(cog, mock_ctx):
    async def fake_bans():
        return
        yield

    mock_ctx.guild.bans = MagicMock(return_value=fake_bans())
    await cog.unban.callback(cog, mock_ctx, user="Nobody#0000")
    mock_ctx.send.assert_called_once_with("Banned user not found.")


# --- purge ---

@pytest.mark.asyncio
async def test_purge_valid(cog, mock_ctx):
    deleted_msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=deleted_msg)
    await cog.purge.callback(cog, mock_ctx, 5)
    mock_ctx.channel.purge.assert_called_once_with(limit=6)
    deleted_msg.delete.assert_called_once()


@pytest.mark.asyncio
async def test_purge_out_of_range(cog, mock_ctx):
    await cog.purge.callback(cog, mock_ctx, 0)
    mock_ctx.send.assert_called_once_with("Amount must be between 1 and 100.")

    mock_ctx.send.reset_mock()
    await cog.purge.callback(cog, mock_ctx, 101)
    mock_ctx.send.assert_called_once_with("Amount must be between 1 and 100.")


# --- mute ---

@pytest.mark.asyncio
async def test_mute_success(cog, mock_ctx, mock_member):
    await cog.mute.callback(cog, mock_ctx, mock_member, 10, reason="spam")
    mock_member.timeout.assert_called_once()
    assert "Muted" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_mute_invalid_duration(cog, mock_ctx, mock_member):
    await cog.mute.callback(cog, mock_ctx, mock_member, 0)
    mock_ctx.send.assert_called_once_with("Duration must be between 1 and 40320 minutes.")
    mock_member.timeout.assert_not_called()

    mock_ctx.send.reset_mock()
    await cog.mute.callback(cog, mock_ctx, mock_member, 99999)
    mock_ctx.send.assert_called_once_with("Duration must be between 1 and 40320 minutes.")


# --- unmute ---

@pytest.mark.asyncio
async def test_unmute(cog, mock_ctx, mock_member):
    await cog.unmute.callback(cog, mock_ctx, mock_member)
    mock_member.timeout.assert_called_once_with(None)
    assert "Unmuted" in mock_ctx.send.call_args.args[0]
