from __future__ import annotations

import typing
from typing import List, Literal, NewType, Optional, Union

import eth_utils
import pydantic
from eth_account.datastructures import SignedTransaction

# from hexbytes import HexBytes


__all__ = [
    "Address",
    "Wei",
    "BlockParameter",
    "CallStateOverrideParams",
    "SignedTransaction",
    "TxHash",
    "TxReceipt",
]


BlockParameter = Union[Literal["earlist", "latest", "pending"], int]
Wei = NewType("Wei", int)
TxHash = NewType("TxHash", str)
FilterId = NewType("FilterId", int)


class Address(str):
    def __new__(cls, value) -> Address:
        try:
            converted_value = eth_utils.to_checksum_address(value)
        except ValueError:
            raise ValueError(f"'{value}' is not a valid ETH address")
        return super().__new__(cls, converted_value)


TxParams = typing.TypedDict(
    "TxParams",
    {
        "from": Address,  # required
        "to": Address,  # optional when creating new contract
        "gas": int,  # optional, default 90000
        "gasPrice": int,  # optional
        "value": int,  # optional
        "data": str,  # required
        "nonce": int,  # optional
        "chainId": int,  # optional
    },
    total=False,
)


CallStateOverrideParams = typing.TypedDict(
    "CallStateOverrideParams",
    # Note: this is geth specific
    # https://geth.ethereum.org/docs/rpc/ns-eth
    {
        "balance": Wei,
        "nonce": int,
        "code": str,
        "state": typing.Any,
        "stateDiff": typing.Any,
    },
    total=False,
)


class BlockData(pydantic.BaseModel):
    number: int
    hash: str
    parentHash: str
    nonce: Optional[str]
    sha3Uncles: str
    logsBloom: Optional[str]
    transactionsRoot: str
    stateRoot: str
    receiptsRoot: str
    miner: Address
    difficulty: int
    totalDifficulty: int
    extraData: str
    size: int
    gasLimit: int
    gasUsed: int
    timestamp: int
    transactions: List[str]  # TODO: full transactions
    uncles: List[str]

    @pydantic.validator(
        "number",
        "difficulty",
        "totalDifficulty",
        "size",
        "gasLimit",
        "gasUsed",
        "timestamp",
        pre=True,
    )
    def quantity_to_int(cls, v):
        return int(v, 16) if isinstance(v, str) else v


class LogData(pydantic.BaseModel):
    removed: bool
    logIndex: int
    transactionIndex: int
    transactionHash: str
    blockHash: str
    blockNumber: int
    address: Address
    data: str
    topics: List[str]

    @pydantic.validator("logIndex", "transactionIndex", "blockNumber", pre=True)
    def quantity_to_int(cls, v):
        return int(v, 16) if isinstance(v, str) else v

    @pydantic.validator("address", pre=True)
    def str_to_address(cls, v):
        return Address(v)


class TxData(pydantic.BaseModel):
    blockHash: str
    blockNumber: int
    from_address: Address
    gas: int
    gasPrice: int
    hash: str
    input: str
    nonce: int
    to_address: Address
    transactionIndex: int
    value: int
    v: int
    r: str
    s: str

    @pydantic.validator(
        "blockNumber",
        "gas",
        "gasPrice",
        "nonce",
        "transactionIndex",
        "value",
        "v",
        pre=True,
    )
    def quantity_to_int(cls, v):
        return int(v, 16) if isinstance(v, str) else v

    @pydantic.validator("from_address", "to_address", pre=True)
    def str_to_address(cls, v):
        if v is not None:
            return Address(v)

    class Config:
        fields = {"from_address": "from", "to_address": "to"}


class TxReceipt(pydantic.BaseModel):
    """
    https://eth.wiki/json-rpc/API#eth_getTransactionReceipt

    Example:
    {
        "blockHash": "0xc7316bf1631a01df297ac8540f0ec159593bb856a52b289290313cdce679b1a9",
        "blockNumber": "0xa8b319",
        "contractAddress": None,
        "cumulativeGasUsed": "0xa09c7",
        "from": "0xeba0de32fddb36751a83ac4a10ab0fa9a6f339ce",
        "gasUsed": "0x5208",
        "logs": [],
        "logsBloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "status": "0x1",
        "to": "0x0678aa21a3485eed7e9bdfb802d620ea8efff860",
        "transactionHash": "0xdecc513528b35a17dd76b7f776f7977a8a5c93f67ee89dd9c77936591c636908",
        "transactionIndex": "0x4",
        "type": "0x0",
    }
    """

    transactionHash: TxHash
    transactionIndex: int
    blockHash: str
    blockNumber: int
    from_address: Address  # "from" is a reserved keyword of Python
    to_address: Address
    cumulativeGasUsed: int
    gasUsed: int
    contractAddress: Optional[Address]
    logs: List[LogData]
    logsBloom: str
    status: Literal[0, 1]  # 1 (success) or 0 (failure)

    @pydantic.validator(
        "transactionIndex",
        "blockNumber",
        "cumulativeGasUsed",
        "gasUsed",
        "status",
        pre=True,
    )
    def quantity_to_int(cls, v):
        return int(v, 16) if isinstance(v, str) else v

    @pydantic.validator("from_address", "to_address", "contractAddress", pre=True)
    def str_to_address(cls, v):
        if v is not None:
            return Address(v)

    class Config:
        fields = {"from_address": "from", "to_address": "to"}
