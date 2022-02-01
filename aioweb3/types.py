from __future__ import annotations

import typing
from typing import Generic, List, Literal, NewType, Optional, TypeVar, Union, cast

import eth_utils
import pydantic
from eth_account.datastructures import SignedTransaction
from pydantic.generics import GenericModel

__all__ = [
    "Address",
    "Wei",
    "BlockParameter",
    "CallStateOverrideParams",
    "SignedTransaction",
    "TxHash",
    "TxReceipt",
]


class Address(str):
    def __new__(cls, value) -> Address:
        converted_value = value.lower()
        return super().__new__(cls, converted_value)

    def to_checksum_address(self) -> "ChecksumAddress":
        try:
            converted = eth_utils.to_checksum_address(self)
        except ValueError:
            raise ValueError(f"'{self}' is not a valid ETH address")
        return cast("ChecksumAddress", converted)

    def to_event_topic(self) -> EventTopic:
        """Convert the address into a 32 Bytes "event topic" in hex string format

        The output is to be used for Web3 log filtering.

        Note: An address has 20 Bytes (40 chars in hex form). A topic is 32 Bytes (64 chars in hex
        form). Thus we need to pad 24 zeros.
        """
        return EventTopic(self[:2] + "0" * 24 + self[2:])


ChecksumAddress = NewType("ChecksumAddress", Address)
BlockParameter = Union[Literal["earlist", "latest", "pending"], int]
Wei = NewType("Wei", int)
TxHash = NewType("TxHash", str)
FilterId = NewType("FilterId", int)
EventTopic = NewType("EventTopic", str)


AddressFilter = Union[Address, List[Address]]
TopicsFilter = List[Union[EventTopic, List[EventTopic], None]]

TxParams = typing.TypedDict(
    "TxParams",
    {
        "from": Address,  # required
        "to": Address,  # optional when creating new contract
        "gas": int,  # optional, default 90000
        # legacy gas price field
        "gasPrice": int,  # optional
        # EIP-1559 gas price field
        # Signer will be charged min(maxFeePerGas, baseFeePerGas + maxPriorityFeePerGas)
        "maxPriorityFeePerGas": int,  # optional
        "maxFeePerGas": int,  # optional
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
        "balance": int,
        "nonce": int,
        "code": str,
        "state": typing.Any,
        "stateDiff": typing.Any,
    },
    total=False,
)


class TxData(pydantic.BaseModel):
    blockHash: Optional[str]  # `None` when transaction is pending
    blockNumber: Optional[int]  # `None` when transaction is pending
    from_address: Address
    gas: int
    gasPrice: int
    hash: str  # 32 Bytes - hash of the transaction.
    input: str  # the data send along with the transaction
    nonce: int  # the number of transactions made by the sender prior to this one
    to_address: Optional[Address]  # contract creation transactions have no "to" address
    transactionIndex: int  # `None` when transaction is pending
    value: int
    v: int  # ECDSA recovery id
    r: str  # 32 Bytes - ECDSA signature r
    s: str  # 32 Bytes - ECDSA signature s

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


T = TypeVar("T", TxHash, TxData)


class NewHead(pydantic.BaseModel):
    """Data from streaming NewHead"""

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
    extraData: str
    gasLimit: int
    gasUsed: int
    timestamp: int

    @pydantic.validator(
        "number",
        "difficulty",
        "gasLimit",
        "gasUsed",
        "timestamp",
        pre=True,
    )
    def quantity_to_int(cls, v):
        return int(v, 16) if isinstance(v, str) else v


class BlockData(GenericModel, Generic[T]):
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
    transactions: List[T]
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


# BlockData = GenericBlockData[str]
# FullBlockData = GenericBlockData[TxData]


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
