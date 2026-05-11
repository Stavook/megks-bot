import pytest
from unittest.mock import AsyncMock, patch
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
    mock_ctx.send.assert_called_once_with("Reloaded `cogs.music`")


@pytest.mark.asyncio
async def test_reload_specific_not_loaded(cog, mock_ctx):
    from discord.ext import commands
    cog.bot.reload_extension = AsyncMock(side_effect=commands.ExtensionNotLoaded("cogs.music"))
    await cog.reload.callback(cog, mock_ctx, cog="music")
    mock_ctx.send.assert_called_once_with("`cogs.music` is not loaded.")


@pytest.mark.asyncio
async def test_reload_specific_error(cog, mock_ctx):
    cog.bot.reload_extension = AsyncMock(side_effect=Exception("Syntax error"))
    await cog.reload.callback(cog, mock_ctx, cog="music")
    assert "Failed to reload" in mock_ctx.send.call_args.args[0]


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
    mock_ctx.send.assert_called_once_with("Loaded `cogs.fun`")


@pytest.mark.asyncio
async def test_load_failure(cog, mock_ctx):
    cog.bot.load_extension = AsyncMock(side_effect=Exception("Not found"))
    await cog.load.callback(cog, mock_ctx, cog="badcog")
    assert "Failed to load" in mock_ctx.send.call_args.args[0]


# --- unload ---

@pytest.mark.asyncio
async def test_unload_success(cog, mock_ctx):
    cog.bot.unload_extension = AsyncMock()
    await cog.unload.callback(cog, mock_ctx, cog="fun")
    cog.bot.unload_extension.assert_called_once_with("cogs.fun")
    mock_ctx.send.assert_called_once_with("Unloaded `cogs.fun`")


@pytest.mark.asyncio
async def test_unload_failure(cog, mock_ctx):
    cog.bot.unload_extension = AsyncMock(side_effect=Exception("Not loaded"))
    await cog.unload.callback(cog, mock_ctx, cog="badcog")
    assert "Failed to unload" in mock_ctx.send.call_args.args[0]
