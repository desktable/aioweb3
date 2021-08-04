import pytest

from aioweb3 import types


def test_Address_convert_to_lower_case():
    checksum_address = "0x18C2ccD3e937bb5b1560A6f70DE9bDB1340D849d"
    assert types.Address(checksum_address) == checksum_address.lower()


def test_Address_type():
    address_str = "0x18C2ccD3e937bb5b1560A6f70DE9bDB1340D849d"
    address = types.Address(address_str)
    assert type(address) == types.Address
    assert isinstance(address, str)

def test_Address_to_checksum_address():
    address_str = "0x18C2ccD3e937bb5b1560A6f70DE9bDB1340D849d"
    checksum_address = types.Address(address_str).to_checksum_address()
    assert isinstance(checksum_address, str)
    assert checksum_address == address_str


def test_Address_to_checksum_address_raises_on_incorrect_address():
    address = "0x18C2ccD3e937bb5b1560A6f70DE9bDB1340D849d"
    with pytest.raises(ValueError):
        types.Address(address[:-1]).to_checksum_address()


def test_LogData_parses_address():
    data = {
        "address": "0x547a355e70cd1f8caf531b950905af751dbef5e6",
        "blockHash": "0xbe8888feb5f2924967b40cd024d2e88138b6c096371abe4f9a739b742eaf0674",
        "blockNumber": "0x93e02f",
        "data": "0x0000000000000000000000000000000000000000006c97c7265005587d9adae300000000000000000000000000000000000000000000013495768fe4bbc0f1ef",
        "logIndex": "0x4",
        "removed": False,
        "topics": ["0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"],
        "transactionHash": "0xcf804a5b1b45e29d4ddfa6edb16381ce07d9de1044e9d6d62a1737d6c9565abf",
        "transactionIndex": "0x0",
    }
    parsed = types.LogData(**data)
    assert type(parsed.address) == types.Address


def test_TxData_can_parse():
    data = {
        "blockHash": "0x1d59ff54b1eb26b013ce3cb5fc9dab3705b415a67127a003c3e61eb445bb8df2",
        "blockNumber": "0x5daf3b",  # 6139707
        "from": "0xa7d9ddbe1f17865597fbd27ec712455208b6b76d",
        "gas": "0xc350",  # 50000
        "gasPrice": "0x4a817c800",  # 20000000000
        "hash": "0x88df016429689c079f3b2f6ad39fa052532c56795b733da78a91ebe6a713944b",
        "input": "0x68656c6c6f21",
        "nonce": "0x15",  # 21
        "to": "0xf02c1c8e6114b1dbe8937a39260b5b0a374432bb",
        "transactionIndex": "0x41",  # 65
        "value": "0xf3dbb76162000",  # 4290000000000000
        "v": "0x25",  # 37
        "r": "0x1b5e176d927f8e9ab405058b2d2457392da3e20f328b16ddabcebc33eaac5fea",
        "s": "0x4ba69724e8f69de52f0125ad8b3c5c2cef33019bac3249e2c0a2192766d1721c",
    }
    parsed = types.TxData(**data)
    assert type(parsed.from_address) == types.Address
    assert type(parsed.to_address) == types.Address
    assert parsed.blockNumber == 6139707
    assert parsed.gas == 50000
    assert parsed.gasPrice == 20000000000
    assert parsed.nonce == 21
    assert parsed.value == 4290000000000000
    assert parsed.transactionIndex == 65


def test_TxReceipt_can_parse_address():
    data = {
        "blockHash": "0xc7316bf1631a01df297ac8540f0ec159593bb856a52b289290313cdce679b1a9",
        "blockNumber": "0xa8b319",
        "contractAddress": None,
        "cumulativeGasUsed": "0xa09c7",
        "from": "0xeba0de32fddb36751a83ac4a10ab0fa9a6f339ce",
        "gasUsed": "0x5208",
        "logs": [
            {
                "address": "0x547a355e70cd1f8caf531b950905af751dbef5e6",
                "blockHash": "0xbe8888feb5f2924967b40cd024d2e88138b6c096371abe4f9a739b742eaf0674",
                "blockNumber": "0x93e02f",
                "data": "0x0000000000000000000000000000000000000000006c97c7265005587d9adae300000000000000000000000000000000000000000000013495768fe4bbc0f1ef",
                "logIndex": "0x4",
                "removed": False,
                "topics": ["0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"],
                "transactionHash": "0xcf804a5b1b45e29d4ddfa6edb16381ce07d9de1044e9d6d62a1737d6c9565abf",
                "transactionIndex": "0x0",
            }
        ],
        "logsBloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "status": "0x1",
        "to": "0x0678aa21a3485eed7e9bdfb802d620ea8efff860",
        "transactionHash": "0xdecc513528b35a17dd76b7f776f7977a8a5c93f67ee89dd9c77936591c636908",
        "transactionIndex": "0x4",
        "type": "0x0",
    }
    parsed = types.TxReceipt(**data)
    assert type(parsed.from_address) == types.Address
    assert type(parsed.to_address) == types.Address
    for log in parsed.logs:
        assert type(log.address) == types.Address
