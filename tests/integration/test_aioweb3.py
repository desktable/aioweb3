import pytest

from aioweb3 import AioWeb3, Address, Wei


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


@pytest.mark.asyncio
async def test_get_balance():
    web3 = AioWeb3("http://localhost:9545")
    balance = await web3.get_balance(Address("0x55d398326f99059ff775485246999027b3197955"))
    assert balance >= 0
    await web3.close()
