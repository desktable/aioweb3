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

    def __call__(self, *args, to: Optional[Address] = None) -> "MethodCallParams":
        params = TxParams(data=self.encode_input(*args))
        to = to or self.to
        if to is not None:
            params["to"] = to.to_checksum_address()
        return MethodCallParams(params, self)

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

    def update(self, kwargs: TxParams) -> "MethodCallParams":
        self.tx_params.update(**kwargs)  # type: ignore
        return self
