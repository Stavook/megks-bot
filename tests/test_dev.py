import pytest
from unittest.mock import AsyncMock, patch
from discord.ext import commands
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.dev import Dev


@pytest.fixture
def cog(mock_bot):
    return Dev(mock_bot)


# --- reload ---

@pytest.mark.asyncio
async def test_reload_specific_success(cog, mock_ctx):
    cog.bot.reload_extension = AsyncMock()
    await cog.reload.callback(cog, mock_ctx, cog="music")
    cog.bot.reload_extension.assert_called_once_with("cogs.music")
    assert "Επαναφορτώθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_reload_specific_not_loaded(cog, mock_ctx):
    from discord.ext import commands
    cog.bot.reload_extension = AsyncMock(side_effect=commands.ExtensionNotLoaded("cogs.music"))
    await cog.reload.callback(cog, mock_ctx, cog="music")
    assert "δεν είναι φορτωμένο" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_reload_specific_error(cog, mock_ctx):
    cog.bot.reload_extension = AsyncMock(side_effect=Exception("Syntax error"))
    await cog.reload.callback(cog, mock_ctx, cog="music")
    assert "Αποτυχία" in mock_ctx.send.call_args.args[0]
    assert "Syntax error" not in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_reload_specific_not_found(cog, mock_ctx):
    cog.bot.reload_extension = AsyncMock(side_effect=commands.ExtensionNotFound("cogs.nope"))
    await cog.reload.callback(cog, mock_ctx, cog="nope")
    assert "Δεν βρέθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_reload_all(cog, mock_ctx):
    cog.bot.reload_extension = AsyncMock()
    fake_files = ["general.py", "music.py", "_ignore.py", "notpython.txt"]
    with patch("os.listdir", return_value=fake_files):
        await cog.reload.callback(cog, mock_ctx)
    assert cog.bot.reload_extension.call_count == 2
    msg = mock_ctx.send.call_args.args[0]
    assert "cogs.general" in msg
    assert "cogs.music" in msg


# --- load ---

@pytest.mark.asyncio
async def test_load_success(cog, mock_ctx):
    cog.bot.load_extension = AsyncMock()
    await cog.load.callback(cog, mock_ctx, cog="fun")
    cog.bot.load_extension.assert_called_once_with("cogs.fun")
    assert "Φορτώθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_load_failure(cog, mock_ctx):
    cog.bot.load_extension = AsyncMock(side_effect=Exception("Not found"))
    await cog.load.callback(cog, mock_ctx, cog="badcog")
    assert "Αποτυχία φόρτωσης" in mock_ctx.send.call_args.args[0]
    assert "Not found" not in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_load_already_loaded(cog, mock_ctx):
    cog.bot.load_extension = AsyncMock(side_effect=commands.ExtensionAlreadyLoaded("cogs.music"))
    await cog.load.callback(cog, mock_ctx, cog="music")
    assert "ήδη φορτωμένο" in mock_ctx.send.call_args.args[0]


# --- unload ---

@pytest.mark.asyncio
async def test_unload_success(cog, mock_ctx):
    cog.bot.unload_extension = AsyncMock()
    await cog.unload.callback(cog, mock_ctx, cog="fun")
    cog.bot.unload_extension.assert_called_once_with("cogs.fun")
    assert "Αποφορτώθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_unload_failure(cog, mock_ctx):
    cog.bot.unload_extension = AsyncMock(side_effect=Exception("Not loaded"))
    await cog.unload.callback(cog, mock_ctx, cog="badcog")
    assert "Αποτυχία αποφόρτωσης" in mock_ctx.send.call_args.args[0]

@pytest.mark.asyncio
async def test_reload_all_failure_hides_exception_text(cog, mock_ctx):
    cog.bot.reload_extension = AsyncMock(side_effect=Exception("secret traceback detail"))
    with patch("os.listdir", return_value=["music.py"]):
        await cog.reload.callback(cog, mock_ctx)
    msg = mock_ctx.send.call_args.args[0]
    assert "✗ cogs.music" in msg
    assert "secret traceback detail" not in msg
