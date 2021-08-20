"""A utility for executing the trades on DEX"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from .exceptions import Web3APIError
from .transaction import Transaction
from .types import Address
from .web3mixin import Web3Mixin


class TransactionError(Exception):
    def __init__(self, tx: Transaction):
        self.tx = tx


class FailedToSendTransactionError(TransactionError):
    reason = "failed to send transaction"


class FailedToGetReceiptError(TransactionError):
    reason = "failed to get transaction receipt"


class WaitForTransactionTimeoutError(TransactionError):
    reason = "transaction time out while waiting for receipt"


class Signer(Web3Mixin):
    """Signer is an abstraction of the Ethereum account

    It can be used to sign messages and send transactions. It keeps track of "nonce"s and pending
    transactions (transactions already sent out but not mined). It allows multiple transactions to
    be sent simultaneously.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, wallet_address: Address, wallet_private_key: str):
        self.wallet_address = wallet_address
        self.wallet_private_key = wallet_private_key

        # The number of transactions known to have been mined
        self._mined_transaction_count = 0

        # maps from nonce to the Transaction object
        self._pending_transactions: dict[int, Transaction] = {}

        self._send_transaction_lock = asyncio.Lock()

    async def send_in_order_and_wait(self, txs: list[Transaction]) -> None:
        """Send multiple transactions in order, then wait for all"""
        wait_tasks = []
        for tx in txs:
            await self.send_transaction(tx)
            wait_tasks.append(asyncio.create_task(self.wait_for_transaction(tx)))
        await asyncio.gather(*wait_tasks)

    async def send_and_wait(
        self,
        tx: Transaction,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """Send a transaction and wait for it to be mined

        See `send_transaction` and `wait_for_transaction` for more details.
        """
        await self.send_transaction(tx, gas_limit, gas_price)
        await self.wait_for_transaction(tx, timeout)

    async def send_transaction(
        self, tx: Transaction, gas_limit: Optional[int] = None, gas_price: Optional[int] = None
    ) -> None:
        """Send a transaction (no waiting)

        Parameters:
        - tx: The transaction to send
        - gas_limit: The gas limit to use for the transaction (optional)
        - gas_price: The gas price to use for the transaction (optional)

        Users are encouraged to specify `gas_limit` and `gas_price`. There are two benefits: 1) to
        speed up the transaction, and 2) to avoid estimating the gasPrice via Web3 (which tends to
        cause errors when the Web3 server is lagged behind the main network).

        This class may raise various subclasses of `TransactionError` if the transaction fails
        (meaning we fail to get a transaction receipt).
        """
        if gas_limit is not None:
            tx.params.update({"gas": gas_limit})
        if gas_price is not None:
            tx.params.update({"gasPrice": gas_price})
        # We allow only one transaction to be sent at a time. Once transactions are sent out, they
        # can be waited simultaneously.
        async with self._send_transaction_lock:
            try:
                nonce = await self._allocate_next_nonce()
                tx.params.update({"nonce": nonce})
                await tx.sign(self.wallet_address, self.wallet_private_key)
                self.logger.info("sending out transaction nonce=%d", nonce)
                await tx.send()
            except Web3APIError as e:
                raise FailedToSendTransactionError(tx) from e
            self._pending_transactions[nonce] = tx

    async def wait_for_transaction(self, tx: Transaction, timeout: Optional[float] = None) -> None:
        """Wait for transaction to be mined

        Parameters:
        - tx: The transaction to send
        - timeout: The timeout timestamp in seconds for waiting (optional). If not set, will wait
          indefinitely.

        Note that `timeout` should be given in epoch timestamp in seconds. It is only a timeout for
        waiting for the transaction receipt, and has no effect on sending the transaction itself.

        This class may raise various subclasses of `TransactionError` if the transaction fails
        (meaning we fail to get a transaction receipt).
        """
        assert tx.tx_hash is not None
        assert "nonce" in tx.params
        nonce = tx.params["nonce"]
        try:
            while tx.receipt is None:
                await asyncio.sleep(3)
                try:
                    await self._query_mined_transaction_count()
                except Web3APIError:
                    self.logger.exception("Failed to update transaction count")
                nonce_has_passed = nonce < self._mined_transaction_count
                try:
                    await tx.check_receipt()
                except Web3APIError:
                    self.logger.exception("Failed to query check transaction receipt")
                if tx.receipt is None and nonce_has_passed:
                    raise FailedToGetReceiptError(tx)
                if timeout is not None and time.time() > timeout:
                    raise WaitForTransactionTimeoutError(tx)
            if tx.receipt is not None:
                # We know at least (nonce + 1) transactions have been mined for this account.
                self._update_mined_transaction_count(nonce + 1)
        finally:
            self._pending_transactions.pop(nonce)

    async def _allocate_next_nonce(self) -> int:
        """Allocate nonce for the next transaction

        When there are no pending transactions, we query Web3 for the nonce.

        When there are pending transactions, we skip querying Web3 and use the next nonce.
        """
        if self._pending_transactions:
            return max(self._mined_transaction_count, max(self._pending_transactions.keys()) + 1)
        else:
            await self._query_mined_transaction_count()
            return self._mined_transaction_count

    def _update_mined_transaction_count(self, transaction_count: int) -> None:
        """Update mined transaction count -- only if the new value is greater than the old value"""
        if transaction_count > self._mined_transaction_count:
            self._mined_transaction_count = transaction_count

    async def _query_mined_transaction_count(self) -> None:
        """Query web3 for the latest transaction count"""
        self._update_mined_transaction_count(
            await self.web3.get_transaction_count(self.wallet_address)
        )
