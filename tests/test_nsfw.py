import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.nsfw import NSFW, VALID_TAGS


@pytest.fixture
def cog(mock_bot):
    return NSFW(mock_bot)


def make_aiohttp_response(status=200, json_data=None):
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data or {})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    session = AsyncMock()
    session.get = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.mark.asyncio
async def test_porn_invalid_tag(cog, mock_ctx):
    await cog.porn.callback(cog, mock_ctx, tag="invalid")
    assert "Άκυρο" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_porn_api_error(cog, mock_ctx):
    session = make_aiohttp_response(status=500)
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.porn.callback(cog, mock_ctx, tag="boobs")
    assert "ανάκτηση" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_porn_no_results(cog, mock_ctx):
    session = make_aiohttp_response(json_data={"success": False})
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.porn.callback(cog, mock_ctx, tag="boobs")
    assert "ανάκτηση" in mock_ctx.send.call_args.args[0]


@pytest.mark.asyncio
async def test_porn_success(cog, mock_ctx):
    session = make_aiohttp_response(json_data={"success": True, "message": "https://example.com/image.gif"})
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.porn.callback(cog, mock_ctx, tag="boobs")
    embed = mock_ctx.send.call_args.kwargs["embed"]
    assert embed.image.url == "https://example.com/image.gif"


@pytest.mark.asyncio
async def test_porn_default_tag(cog, mock_ctx):
    session = make_aiohttp_response(json_data={"success": True, "message": "https://example.com/image.gif"})
    with patch("aiohttp.ClientSession", return_value=session):
        await cog.porn.callback(cog, mock_ctx)
    assert session.get.call_args.kwargs["params"]["type"] == "pgif"


def test_valid_tags_not_empty():
    assert len(VALID_TAGS) > 0