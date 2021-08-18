import asyncio
import logging
import time
from typing import Optional, Union

from eth_account import Account
from eth_account.datastructures import SignedTransaction

from .methodcall import MethodCallParams
from .types import Address, TxHash, TxParams, TxReceipt
from .web3mixin import Web3Mixin


class Transaction(Web3Mixin):
    logger = logging.getLogger(__name__)

    def __init__(self, params: Union[TxParams, MethodCallParams]):
        self.params: TxParams
        if isinstance(params, MethodCallParams):
            self.params = params.tx_params
        else:
            self.params = params
        self.signed_tx: Optional[SignedTransaction] = None
        self.tx_hash: Optional[TxHash] = None
        self.receipt: Optional[TxReceipt] = None

    async def _set_default_chain_id(self) -> None:
        if "chainId" not in self.params:
            self.params["chainId"] = await self.web3.chain_id

    async def _set_default_gas(self) -> None:
        if "gas" not in self.params:
            # note that we generally need to set "from" before estimating gas
            gas = await self.web3.estimate_gas(self.params)
            self.params["gas"] = gas * 2 + 125000

    async def _set_default_gas_price(self, gas_multiplier: float):
        if "gasPrice" not in self.params:
            gas_price = await self.web3.gas_price
            gas_price = int(gas_price * gas_multiplier)
            self.params["gasPrice"] = gas_price

    async def _set_default_nonce(self, wallet_address: Address, nonce_offset: int):
        if "nonce" not in self.params:
            nonce = await self.web3.get_transaction_count(wallet_address)
            nonce += nonce_offset
            self.params["nonce"] = nonce

    async def sign(
        self,
        wallet_address: Address,
        wallet_private_key: str,
        nonce_offset: int = 0,
        gas_multiplier: float = 1.0,
    ) -> "Transaction":
        """Sign the transaction with the private key

        Fill in the following fields if not yet set: chainId, gas, gasPrice, nonce
        """
        start_ts = time.time()
        if "from" not in self.params:
            self.params["from"] = wallet_address.to_checksum_address()
        await asyncio.gather(
            self._set_default_chain_id(),
            self._set_default_gas(),
            self._set_default_gas_price(gas_multiplier),
            self._set_default_nonce(wallet_address, nonce_offset),
        )
        self.signed_tx = Account.sign_transaction(self.params, wallet_private_key)
        elapsed_time = time.time() - start_ts
        self.logger.info(f"Signed transaction: {self.params} ({elapsed_time*1e3:.3f}ms)")
        return self

    async def send(self) -> TxHash:
        start_ts = time.time()
        assert self.signed_tx is not None
        self.tx_hash = await self.web3.send_signed_transaction(self.signed_tx)
        elapsed_time = time.time() - start_ts
        self.logger.info(f"Sent transaction: {self.tx_hash} ({elapsed_time*1e3:.3f}ms)")
        return self.tx_hash

    async def wait(self, timeout: float = 120.0) -> Optional[TxReceipt]:
        assert self.tx_hash is not None
        start_ts = time.time()
        try:
            self.receipt = await asyncio.wait_for(
                self.web3.wait_for_transaction_receipt(self.tx_hash), timeout=timeout
            )
        except asyncio.TimeoutError:
            self.logger.error("Timeout for transaction! %s", self.tx_hash)
            raise
        else:
            elapsed_time = time.time() - start_ts
            self.logger.info(
                f"Received transaction receipt: {self.receipt} ({elapsed_time*1e3:.3f}ms)"
            )
        return self.receipt

    async def send_and_wait(self, timeout: float = 120.0):
        await self.send()
        await self.wait(timeout)
