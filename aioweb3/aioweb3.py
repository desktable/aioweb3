import asyncio
import logging
import typing
from typing import Any, Dict, List, Optional, Union

import eth_abi
from eth_hash.auto import keccak
from hexbytes import HexBytes

from .endpoints import RPCMethod
from .methodcall import MethodCallParams
from .transport import BaseTransport, Subscription, get_transport
from .types import (
    Address,
    AddressFilter,
    BlockData,
    BlockParameter,
    CallStateOverrideParams,
    FilterId,
    LogData,
    SignedTransaction,
    TopicsFilter,
    TxData,
    TxHash,
    TxParams,
    TxReceipt,
    Wei,
)


def _format_block_parameter(block_parameter: Optional[BlockParameter]) -> Optional[str]:
    if isinstance(block_parameter, int):
        return hex(block_parameter)
    else:
        return block_parameter


def _format_params(params: typing.Mapping[str, Any]) -> Dict[str, Any]:
    return {k: hex(v) if isinstance(v, int) else v for k, v in params.items()}


class AioWeb3:
    """Main interface for interacting with the Web3 server"""

    def __init__(self, transport: Union[BaseTransport, str]):
        self.logger = logging.getLogger(__name__)
        self._transport: BaseTransport
        if isinstance(transport, str):
            self._transport = get_transport(transport)
        else:
            self._transport = transport
        self._chain_id: Optional[int] = None

    def __repr__(self) -> str:
        return f"<AioWeb3: {self._transport.uri}>"

    async def send_request(self, method: str, params: Any = None) -> Any:
        """Send a request using Web3's JSON-API"""
        ret = await self._transport.send_request(method, params)
        return ret

    async def subscribe(self, params: Any) -> Subscription:
        """Subscribe to streaming updates from Web3"""
        return await self._transport.subscribe(params)

    async def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe a subscription"""
        await self._transport.unsubscribe(subscription)

    async def close(self):
        """Close Web3 connection

        Note that it is important to close the connection when you are done interacting with
        AioWeb3. This has to be an async method, because both closing WebSocket connections and
        closing AioHTTP sessions are async operations.
        """
        await self._transport.close()

    async def is_connect(self):
        try:
            await self.client_version
        except Exception:
            return False
        return True

    @property
    async def client_version(self) -> str:
        return await self.send_request(RPCMethod.web3_clientVersion)

    @property
    async def chain_id(self) -> int:
        if self._chain_id is None:
            id_hex = await self.send_request(RPCMethod.eth_chainId)
            self._chain_id = int(id_hex, 16)
        return self._chain_id

    @property
    async def accounts(self):
        return await self.send_request(RPCMethod.eth_accounts)

    @property
    async def block_number(self) -> int:
        hex_block = await self.send_request(RPCMethod.eth_blockNumber)
        return int(hex_block, 16)

    @property
    async def gas_price(self) -> int:
        hex_price = await self.send_request(RPCMethod.eth_gasPrice)
        return int(hex_price, 16)

    async def get_transaction_count(
        self, address: Address, block: BlockParameter = "latest"
    ) -> int:
        hex_count = await self.send_request(
            RPCMethod.eth_getTransactionCount, [address, _format_block_parameter(block)]
        )
        return int(hex_count, 16)

    async def call_method(
        self,
        to: Address,
        method_name: str,
        input_types,
        output_types,
        *args,
        block: BlockParameter = "latest",
        **kwargs,
    ):
        function_signature = method_name + "(" + ",".join(input_types) + ")"
        function_selector = "0x" + keccak(function_signature.encode()).hex()[:8]
        input_data = eth_abi.encode_abi(input_types, args).hex()
        data = function_selector + input_data
        params = TxParams(to=to, data=data)
        output_data = await self._call(params, block=block, **kwargs)
        output = eth_abi.decode_abi(output_types, bytes(HexBytes(output_data)))
        if len(output) == 1:
            return output[0]
        else:
            return output

    async def get_code(self, address: Address, block: BlockParameter = "latest") -> Optional[str]:
        code = await self.send_request(
            RPCMethod.eth_getCode, [address, _format_block_parameter(block)]
        )
        if code == "0x":
            return None
        else:
            return code

    async def send_signed_transaction(self, signed: SignedTransaction) -> TxHash:
        res = await self.send_request(
            RPCMethod.eth_sendRawTransaction, [signed.rawTransaction.hex()]
        )
        return TxHash(res)

    async def get_transaction_by_hash(self, tx_hash: TxHash) -> Optional[TxData]:
        """Get the information about a transaction

        Returns `None` when no transaction is found.

        https://eth.wiki/json-rpc/API#eth_gettransactionbyhash
        """
        res = await self.send_request(RPCMethod.eth_getTransactionByHash, [tx_hash])
        if res:
            return TxData(**res)
        else:
            return None

    async def get_transaction_receipt(self, tx_hash: TxHash) -> Optional[TxReceipt]:
        """Get the receipt of a transaction by transaction hash

        Returns `None` when no receipt is found.

        https://eth.wiki/json-rpc/API#eth_gettransactionreceipt
        """
        res = await self.send_request(RPCMethod.eth_getTransactionReceipt, [tx_hash])
        if res:
            return TxReceipt(**res)
        else:
            return None

    async def wait_for_transaction_receipt(
        self, tx_hash: TxHash, poll_interval: float = 3
    ) -> TxReceipt:
        while True:
            receipt = await self.get_transaction_receipt(tx_hash)
            if receipt is not None:
                return receipt
            await asyncio.sleep(poll_interval)

    async def call(
        self, method_call_params: MethodCallParams, block: BlockParameter = "latest", **kwargs
    ):
        data = await self._call(method_call_params.tx_params, block=block, **kwargs)
        ret = method_call_params.method_call.decode_output(data)
        if len(ret) == 1:
            return ret[0]
        else:
            return ret

    async def _call(
        self,
        params: TxParams,
        block: BlockParameter = "latest",
        state_override: CallStateOverrideParams = {},
    ) -> str:
        """
        https://eth.wiki/json-rpc/API#eth_call
        https://geth.ethereum.org/docs/rpc/ns-eth

        Return raw string output (not decoded)
        """
        return await self.send_request(
            RPCMethod.eth_call,
            [
                _format_params(params),
                _format_block_parameter(block),
                _format_params(state_override),
            ],
        )

    async def estimate_gas(self, params: TxParams, block: BlockParameter = "latest") -> Wei:
        qty = await self.send_request(
            RPCMethod.eth_estimateGas,
            [
                _format_params(params),
                _format_block_parameter(block),
            ],
        )
        return Wei(int(qty, 16))

    async def get_balance(self, address: Address, block: BlockParameter = "latest") -> Wei:
        b = await self.send_request(
            RPCMethod.eth_getBalance, [address, _format_block_parameter(block)]
        )
        return Wei(int(b, 16))

    async def get_block_by_number(
        self, block: BlockParameter = "latest"
    ) -> Optional[BlockData[TxHash]]:
        full_transactions = False
        res = await self.send_request(
            RPCMethod.eth_getBlockByNumber, [_format_block_parameter(block), full_transactions]
        )
        if res is not None:
            return BlockData[TxHash](**res)
        else:
            return None

    async def get_full_block_by_number(
        self, block: BlockParameter = "latest"
    ) -> Optional[BlockData[TxData]]:
        full_transactions = True
        res = await self.send_request(
            RPCMethod.eth_getBlockByNumber, [_format_block_parameter(block), full_transactions]
        )
        if res is not None:
            return BlockData[TxData](**res)
        else:
            return None

    async def new_filter(
        self,
        from_block: Optional[BlockParameter] = None,
        to_block: Optional[BlockParameter] = None,
        address: Optional[AddressFilter] = None,
        topics: Optional[TopicsFilter] = None,
    ) -> FilterId:
        """
        https://eth.wiki/json-rpc/API#eth_newFilter
        """
        params = {
            "fromBlock": _format_block_parameter(from_block),
            "toBlock": _format_block_parameter(to_block),
            "address": address,
            "topics": topics,
        }
        params = {k: v for k, v in params.items() if v is not None}
        filter_id = await self.send_request(RPCMethod.eth_newFilter, [params])
        return FilterId(int(filter_id, 16))

    async def new_block_filter(self) -> FilterId:
        filter_id = await self.send_request(RPCMethod.eth_newBlockFilter)
        return FilterId(int(filter_id, 16))

    async def new_pending_transaction_filter(self) -> FilterId:
        filter_id = await self.send_request(RPCMethod.eth_newPendingTransactionFilter)
        return FilterId(int(filter_id, 16))

    async def uninstall_filter(self, filter_id: FilterId) -> bool:
        return await self.send_request(RPCMethod.eth_uninstallFilter, [hex(filter_id)])

    async def get_filter_logs(self, filter_id: FilterId) -> List[LogData]:
        # TODO: handle new block & pending transaction filters
        res = await self.send_request(RPCMethod.eth_getFilterLogs, [hex(filter_id)])
        return [LogData(**log_data) for log_data in res]

    async def get_filter_changes(self, filter_id: FilterId) -> List[LogData]:
        # TODO: handle new block & pending transaction filters
        res = await self.send_request(RPCMethod.eth_getFilterChanges, [hex(filter_id)])
        return [LogData(**log_data) for log_data in res]

    async def get_logs(
        self,
        from_block: Optional[BlockParameter] = None,
        to_block: Optional[BlockParameter] = None,
        address: Optional[AddressFilter] = None,
        topics: Optional[TopicsFilter] = None,
        blockhash: Optional[str] = None,
    ) -> List[LogData]:
        """Get event logs

        https://eth.wiki/json-rpc/API#eth_getlogs
        """
        params = {
            "fromBlock": _format_block_parameter(from_block),
            "toBlock": _format_block_parameter(to_block),
            "address": address,
            "topics": topics,
            "blockhash": blockhash,
        }
        params = {k: v for k, v in params.items() if v is not None}
        res = await self.send_request(RPCMethod.eth_getLogs, [params])
        return [LogData(**log_data) for log_data in res]

    async def subscribe_block(self) -> Subscription:
        return await self.subscribe(["newHeads"])

    async def subscribe_syncing(self) -> Subscription:
        return await self.subscribe(["syncing"])

    async def subscribe_new_pending_transaction(self) -> Subscription:
        return await self.subscribe(["newPendingTransactions"])

    async def subscribe_logs(
        self,
        address: Optional[AddressFilter] = None,
        topics: Optional[TopicsFilter] = None,
    ) -> Subscription:
        params: List[Any] = ["logs"]
        log_spec: Dict[str, Any] = {}
        if address:
            log_spec["address"] = address
        if topics:
            log_spec["topics"] = topics
        if log_spec:
            params.append(log_spec)
        return await self.subscribe(params)
