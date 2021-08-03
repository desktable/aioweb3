import pytest

from aioweb3 import AioWeb3


@pytest.mark.asyncio
async def test_AioWeb3_can_use_websocket():
    web3 = AioWeb3("ws://localhost:9546")
    client_version = await web3.client_version
    assert client_version.startswith("Geth/")
    await web3.close()


@pytest.mark.asyncio
async def test_AioWeb3_can_use_http():
    web3 = AioWeb3("http://localhost:9545")
    client_version = await web3.client_version
    assert client_version.startswith("Geth/")
    await web3.close()


@pytest.mark.asyncio
async def test_AioWeb3_can_use_ipc():
    web3 = AioWeb3("/data/henry/binance-smart-chain/node/geth.ipc")
    client_version = await web3.client_version
    assert client_version.startswith("Geth/")
    await web3.close()
