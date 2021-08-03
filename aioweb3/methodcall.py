from dataclasses import dataclass
from typing import List, Optional

import eth_abi
from eth_hash.auto import keccak
from hexbytes import HexBytes

from .types import Address, TxParams


@dataclass
class MethodCall:
    method_name: str
    input_types: List[str]
    output_types: List[str]
    to: Optional[Address] = None
    tx_params: Optional[TxParams] = None

    def __call__(self, *args, to: Optional[Address] = None) -> "MethodCallParams":
        params = {
            "data": self.encode_input(*args),
            "to": to or self.to,
        }
        params = {k: v for k, v, in params.items() if v is not None}
        return MethodCallParams(TxParams(**params), self)

    def bind(self, to: Address) -> "MethodCall":
        return MethodCall(self.method_name, self.input_types, self.output_types, to)

    def encode_input(self, *args) -> str:
        function_signature = self.method_name + "(" + ",".join(self.input_types) + ")"
        function_selector = "0x" + keccak(function_signature.encode()).hex()[:8]
        input_data = eth_abi.encode_abi(self.input_types, args).hex()
        data = function_selector + input_data
        return data

    def decode_output(self, data: str):
        return eth_abi.decode_abi(self.output_types, bytes(HexBytes(data)))


@dataclass
class MethodCallParams:
    tx_params: TxParams
    method_call: MethodCall

    def update(self, kwargs) -> "MethodCallParams":
        self.tx_params.update(**kwargs)
        return self


class ERC20:
    name = MethodCall("name", [], ["string"])
    symbol = MethodCall("symbol", [], ["string"])
    decimals = MethodCall("decimals", [], ["uint8"])
    totalSupply = MethodCall("totalSupply", [], ["uint256"])
    balanceOf = MethodCall("balanceOf", ["address"], ["uint256"])
    transfer = MethodCall("transfer", ["address", "uint256"], ["bool"])
    allowance = MethodCall("allowance", ["address", "address"], ["uint256"])
    approve = MethodCall("approve", ["address", "uint256"], ["bool"])
    transferFrom = MethodCall("transferFrom", ["address", "address", "uint256"], ["bool"])


class DEXPair(ERC20):
    """
    https://docs.uniswap.org/protocol/V2/reference/smart-contracts/pair
    """

    factory = MethodCall("factory", [], ["address"])
    token0 = MethodCall("token0", [], ["address"])
    token1 = MethodCall("token1", [], ["address"])
    getReserves = MethodCall("getReserves", [], ["uint112", "uint112", "uint32"])


class DEXFactory:
    """
    https://docs.uniswap.org/protocol/V2/reference/smart-contracts/factory
    """

    getPair = MethodCall("getPair", ["address", "address"], ["address"])
    allPairsLength = MethodCall("allPairsLength", [], ["uint256"])
    allPairs = MethodCall("allPairs", ["uint256"], ["address"])


class DEXRouter:
    """
    https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02
    """

    factory = MethodCall("factory", [], ["address"])
    getAmountsOut = MethodCall("getAmountsOut", ["uint256", "address[]"], ["uint256[]"])
    swapExactTokensForTokens = MethodCall(
        "swapExactTokensForTokens",
        ["uint256", "uint256", "address[]", "address", "uint256"],
        ["uint256[]"],
    )
