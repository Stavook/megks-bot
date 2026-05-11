import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.fun import Fun


@pytest.fixture
def cog(mock_bot):
    return Fun(mock_bot)


@pytest.mark.asyncio
async def test_choose_valid(cog, mock_ctx):
    await cog.choose.callback(cog, mock_ctx, options="cats, dogs, birds")
    mock_ctx.send.assert_called_once()
    assert any(opt in mock_ctx.send.call_args.args[0] for opt in ["cats", "dogs", "birds"])


@pytest.mark.asyncio
async def test_choose_single_option(cog, mock_ctx):
    await cog.choose.callback(cog, mock_ctx, options="only one")
    assert "τουλάχιστον 2" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_choose_empty(cog, mock_ctx):
    await cog.choose.callback(cog, mock_ctx, options=",,,")
    assert "τουλάχιστον 2" in mock_ctx.send.call_args.args[0]