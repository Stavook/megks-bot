import pytest
from unittest.mock import patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.rules import Rules


@pytest.fixture
def cog(mock_bot):
    return Rules(mock_bot)


@pytest.mark.asyncio
async def test_rules_empty(cog, mock_ctx):
    with patch("cogs.rules.load_rules", return_value={}):
        await cog.rules.callback(cog, mock_ctx)
    assert "Δεν υπάρχουν" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_rules_with_entries(cog, mock_ctx):
    mock_ctx.guild.name = "TestServer"
    data = {str(mock_ctx.guild.id): ["Rule one", "Rule two"]}
    with patch("cogs.rules.load_rules", return_value=data):
        await cog.rules.callback(cog, mock_ctx)
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert "TestServer" in embed.title
    assert "Rule one" in embed.description
    assert "Rule two" in embed.description


@pytest.mark.asyncio
async def test_addrule(cog, mock_ctx):
    data = {}
    with patch("cogs.rules.load_rules", return_value=data), \
         patch("cogs.rules.save_rules") as mock_save:
        await cog.addrule.callback(cog, mock_ctx, text="No spam")
    assert data[str(mock_ctx.guild.id)] == ["No spam"]
    mock_save.assert_called_once_with(data)
    assert "Προστέθηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_delrule_success(cog, mock_ctx):
    data = {str(mock_ctx.guild.id): ["Rule A", "Rule B", "Rule C"]}
    with patch("cogs.rules.load_rules", return_value=data), \
         patch("cogs.rules.save_rules"):
        await cog.delrule.callback(cog, mock_ctx, 2)
    assert data[str(mock_ctx.guild.id)] == ["Rule A", "Rule C"]
    assert "Διαγράφηκε" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_delrule_out_of_range(cog, mock_ctx):
    data = {str(mock_ctx.guild.id): ["Only rule"]}
    with patch("cogs.rules.load_rules", return_value=data):
        await cog.delrule.callback(cog, mock_ctx, 5)
    assert "αριθμός" in mock_ctx.send.call_args.args[0]