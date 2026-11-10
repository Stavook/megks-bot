import logging

import discord
import pytest
from unittest.mock import AsyncMock, MagicMock
from discord.ext import commands
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.errors import Errors, GENERIC_ERROR, describe_error


@pytest.fixture
def cog(mock_bot):
    return Errors(mock_bot)


@pytest.fixture
def ctx(mock_ctx):
    mock_ctx.prefix = "!"
    mock_ctx.command = MagicMock()
    mock_ctx.command.qualified_name = "lyrics"
    mock_ctx.command.signature = "<song> [artist]"
    mock_ctx.command.has_error_handler.return_value = False
    mock_ctx.cog = MagicMock()
    mock_ctx.cog.has_error_handler.return_value = False
    mock_ctx.guild.id = 99999
    return mock_ctx


def invoke_error(original):
    return commands.CommandInvokeError(original)


@pytest.mark.asyncio
async def test_command_not_found_is_silent(cog, ctx):
    await cog.on_command_error(ctx, commands.CommandNotFound('Command "x" is not found'))
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_check_failure_is_silent(cog, ctx):
    """e.g. a non-owner running a Dev command: no 'check functions failed' text."""
    await cog.on_command_error(ctx, commands.CheckFailure("The check functions for command reload failed."))
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_not_owner_is_silent(cog, ctx):
    await cog.on_command_error(ctx, commands.NotOwner("You do not own this bot."))
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_missing_argument_shows_usage(cog, ctx):
    param = MagicMock()
    param.name = "song"
    await cog.on_command_error(ctx, commands.MissingRequiredArgument(param))
    msg = ctx.send.call_args.args[0]
    assert "`song`" in msg
    assert "`!lyrics <song> [artist]`" in msg
    assert "is a required argument" not in msg


@pytest.mark.asyncio
async def test_missing_argument_no_signature(cog, ctx):
    ctx.command.signature = ""
    param = MagicMock()
    param.name = "x"
    await cog.on_command_error(ctx, commands.MissingRequiredArgument(param))
    assert "`!lyrics`" in ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_bad_argument_hides_converter_text(cog, ctx):
    await cog.on_command_error(ctx, commands.BadArgument('Member "zzz" not found.'))
    msg = ctx.send.call_args.args[0]
    assert "Μη έγκυρο όρισμα" in msg
    assert "zzz" not in msg


@pytest.mark.asyncio
async def test_parsing_error_is_invalid_argument(cog, ctx):
    await cog.on_command_error(ctx, commands.ExpectedClosingQuoteError('"'))
    assert "Μη έγκυρο όρισμα" in ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_missing_permissions(cog, ctx):
    await cog.on_command_error(ctx, commands.MissingPermissions(["kick_members"]))
    msg = ctx.send.call_args.args[0]
    assert "Δεν έχεις δικαίωμα" in msg
    assert "kick_members" not in msg


@pytest.mark.asyncio
async def test_bot_missing_permissions_lists_pretty_names(cog, ctx):
    await cog.on_command_error(ctx, commands.BotMissingPermissions(["kick_members"]))
    msg = ctx.send.call_args.args[0]
    assert "`kick members`" in msg
    assert "Bot requires" not in msg


@pytest.mark.asyncio
async def test_no_private_message(cog, ctx):
    await cog.on_command_error(ctx, commands.NoPrivateMessage())
    assert "server" in ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_cooldown(cog, ctx):
    error = commands.CommandOnCooldown(MagicMock(), 4.6, commands.BucketType.user)
    await cog.on_command_error(ctx, error)
    assert "5δ" in ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_forbidden_gets_friendly_message(cog, ctx):
    response = MagicMock(status=403, reason="Forbidden")
    error = invoke_error(discord.Forbidden(response, "Missing Permissions"))
    await cog.on_command_error(ctx, error)
    msg = ctx.send.call_args.args[0]
    assert "Δεν έχω δικαίωμα" in msg
    assert "Missing Permissions" not in msg
    assert "403" not in msg


@pytest.mark.asyncio
async def test_unexpected_error_is_generic_and_logged(cog, ctx, caplog):
    error = invoke_error(RuntimeError("db password is hunter2"))
    with caplog.at_level(logging.ERROR, logger="megks_bot.errors"):
        await cog.on_command_error(ctx, error)
    ctx.send.assert_awaited_once_with(GENERIC_ERROR)
    assert "hunter2" not in ctx.send.call_args.args[0]
    # full detail still reaches the logs
    assert caplog.records and caplog.records[0].exc_info is not None


@pytest.mark.asyncio
async def test_unknown_error_type_is_generic(cog, ctx):
    await cog.on_command_error(ctx, commands.CommandError("weird internal state"))
    ctx.send.assert_awaited_once_with(GENERIC_ERROR)


@pytest.mark.asyncio
async def test_commands_with_local_handler_are_skipped(cog, ctx):
    ctx.command.has_error_handler.return_value = True
    await cog.on_command_error(ctx, invoke_error(RuntimeError("x")))
    ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_send_failure_does_not_raise(cog, ctx):
    ctx.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=500, reason="x"), "boom"))
    await cog.on_command_error(ctx, invoke_error(RuntimeError("x")))  # must not raise


def test_describe_error_never_contains_exception_text(ctx):
    errors = [
        invoke_error(ValueError("LEAK")),
        commands.BadArgument("LEAK"),
        commands.CheckFailure("LEAK"),
        commands.CommandError("LEAK"),
        commands.TooManyArguments("LEAK"),
    ]
    for error in errors:
        assert "LEAK" not in (describe_error(ctx, error) or "")
