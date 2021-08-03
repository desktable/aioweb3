import abc
import asyncio
import itertools
import json
import logging
from typing import Any, Dict, Literal, Optional, Tuple, Type, Union

import aiohttp
import pydantic
from aiohttp.payload import BytesPayload
from websockets.legacy.client import WebSocketClientProtocol, connect

from .endpoints import RPCMethod
from .exceptions import Web3APIError


class Subscription:
    def __init__(self, subscription_id: str, queue: asyncio.Queue):
        self.subscription_id = subscription_id
        self.queue = queue

    @property
    def id(self) -> str:
        return self.subscription_id

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.queue.get()


class RequestMessage(pydantic.BaseModel):
    jsonrpc: Literal["2.0"]
    method: str
    params: Any
    id: int


class ResponseMessage(pydantic.BaseModel):
    jsonrpc: Literal["2.0"]
    error: Any
    result: Any
    id: int


class NotificationParams(pydantic.BaseModel):
    subscription: str  # subscription id, e.g., "0xcd0c3e8af590364c09d0fa6a1210faf5"
    result: Any


class NotificationMessage(pydantic.BaseModel):
    """
    https://geth.ethereum.org/docs/rpc/pubsub
    """

    jsonrpc: Literal["2.0"]
    method: Literal["eth_subscription"]
    params: NotificationParams


class BaseTransport(abc.ABC):
    logger = logging.getLogger(__name__)

    def __init__(self):
        self._rpc_counter = itertools.count(1)

    @abc.abstractmethod
    async def close(self) -> None:
        pass

    async def send_request(self, method: str, params: Any = None) -> Any:
        request_id = next(self._rpc_counter)
        rpc_dict = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": request_id,
        }
        request = RequestMessage(**rpc_dict)
        response = await self._send_request(request)
        if response.error:
            raise Web3APIError(f"Received error response {response} for request {request}")
        return response.result

    @abc.abstractmethod
    async def _send_request(self, request: RequestMessage) -> ResponseMessage:
        pass

    async def subscribe(self, method: str, params: Any = None) -> Subscription:
        raise NotImplementedError

    async def unsubscribe(self, subscription: Subscription) -> None:
        raise NotImplementedError

    def _parse_message(self, msg: bytes) -> Union[ResponseMessage, NotificationMessage]:
        self.logger.debug("inbound: %s", msg.decode())
        try:
            j = json.loads(msg)
            if "method" in j:
                return NotificationMessage(**j)
            else:
                return ResponseMessage(**j)
        except Exception as exc:
            raise Web3APIError(f"Failed to parse message {msg}") from exc


class PersistentListener:
    def __init__(self, listen_func) -> None:
        self.listen_func = listen_func
        self.is_listening: Optional[asyncio.Event] = None
        self.task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        if self.task is None or self.task.done():
            self.is_listening = asyncio.Event()
            self.task = asyncio.create_task(self.listen_func())
            await self.is_listening.wait()

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb
    ) -> None:
        if exc_val is not None:
            try:
                if self.task is not None:
                    self.task.cancel()
            except Exception:
                pass
            self.task = None

    def is_ready(self):
        if self.is_listening is not None:
            self.is_listening.set()

    def close(self):
        if self.task is not None:
            self.task.cancel()
            self.task = None


class TwoWayTransport(BaseTransport, metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()
        self.listener = PersistentListener(self.listen)
        self._requests: Dict[int, asyncio.Future[ResponseMessage]] = {}
        self._subscriptions: Dict[str, asyncio.Queue[Any]] = {}

    async def _send_request(self, request: RequestMessage) -> ResponseMessage:
        data = json.dumps(request.dict()).encode("utf-8")
        fut = asyncio.get_event_loop().create_future()
        self._requests[request.id] = fut
        self.logger.debug("outbound: %s", data.decode())
        async with self.listener:
            await self.send(data)
            result = await fut
        del self._requests[request.id]
        return result

    async def subscribe(self, params: Any) -> Subscription:
        """
        https://geth.ethereum.org/docs/rpc/pubsub
        """
        subscription_id = await self.send_request(RPCMethod.eth_subscribe, params)
        queue = asyncio.Queue()
        self._subscriptions[subscription_id] = queue
        return Subscription(subscription_id, queue)

    async def unsubscribe(self, subscription: Subscription) -> None:
        assert isinstance(subscription, Subscription)
        response = await self.send_request(RPCMethod.eth_unsubscribe, [subscription.id])
        assert response
        queue = self._subscriptions[subscription.id]
        del self._subscriptions[subscription.id]
        queue.task_done()

    @abc.abstractmethod
    async def send(self, data: bytes):
        pass

    @abc.abstractmethod
    async def receive(self) -> bytes:
        pass

    @abc.abstractmethod
    async def close(self):
        self.listener.close()

    def _handle_response_message(self, response: ResponseMessage):
        if response.id in self._requests:
            self._requests[response.id].set_result(response)
        else:
            self.logger.warning("Unsolicitated response message: %s", response)

    def _handle_notification_message(self, notification: NotificationMessage):
        sub_id = notification.params.subscription
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id].put_nowait(notification.params.result)
        else:
            self.logger.warning("Unsolicitated notification message: %s", notification)

    async def listen(self):
        self.logger.info("Starting listening for messages")
        handlers = {
            ResponseMessage: self._handle_response_message,
            NotificationMessage: self._handle_notification_message,
        }
        while True:
            msg = await self.receive()
            parsed = self._parse_message(msg)
            handlers[type(parsed)](parsed)


class PersistentSocket:
    def __init__(self, ipc_path) -> None:
        self.ipc_path = ipc_path
        self.reader_writer: Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = None

    async def __aenter__(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        if self.reader_writer is None:
            self.reader_writer = await asyncio.open_unix_connection(self.ipc_path)
        return self.reader_writer

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb
    ) -> None:
        if exc_val is not None:
            try:
                if self.reader_writer is not None:
                    _, writer = self.reader_writer
                    writer.close()
            except Exception:
                pass
            self.reader_writer = None

    async def close(self):
        if self.reader_writer is not None:
            _, writer = self.reader_writer
            writer.close()
            self.reader_writer = None


class IPCTransport(TwoWayTransport):
    def __init__(self, local_ipc_path: str):
        super().__init__()
        self.socket = PersistentSocket(local_ipc_path)

    async def send(self, data: bytes):
        async with self.socket as (_, writer):
            writer.write(data)
            await writer.drain()

    async def receive(self) -> bytes:
        async with self.socket as (reader, _):
            self.listener.is_ready()
            msg = await reader.readuntil()
        return msg

    async def close(self) -> None:
        await super().close()  # first stop listening
        await self.socket.close()  # then stop connection


class PersistentWebSocket:
    def __init__(self, endpoint_uri: str, websocket_kwargs: Any) -> None:
        self.ws: Optional[WebSocketClientProtocol] = None
        self.endpoint_uri = endpoint_uri
        self.websocket_kwargs = websocket_kwargs

    async def __aenter__(self) -> WebSocketClientProtocol:
        if self.ws is None:
            self.ws = await connect(uri=self.endpoint_uri, **self.websocket_kwargs)
        return self.ws

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb
    ) -> None:
        if exc_val is not None:
            try:
                if self.ws is not None:
                    await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
            self.ws = None


class WebsocketTransport(TwoWayTransport):
    def __init__(self, websocket_uri: str, websocket_kwargs: Optional[Any] = None):
        super().__init__()
        self.websocket_uri = websocket_uri
        if websocket_kwargs is None:
            websocket_kwargs = {}
        self.conn = PersistentWebSocket(websocket_uri, websocket_kwargs)

    async def send(self, data: bytes):
        async with self.conn as conn:
            await conn.send(data)

    async def receive(self) -> bytes:
        async with self.conn as conn:
            self.listener.is_ready()
            msg = await conn.recv()
            if isinstance(msg, str):
                return msg.encode()
            else:
                return msg

    async def close(self) -> None:
        await super().close()  # first stop listening
        await self.conn.close()  # then stop connection


class PersistentHTTPSession:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> aiohttp.ClientSession:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def __aexit__(
        self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb
    ) -> None:
        if exc_val is not None:
            try:
                if self.session is not None:
                    await self.session.close()
            except Exception:
                pass
            self.session = None

    async def close(self):
        if self.session is not None:
            await self.session.close()
            self.session = None


class HTTPTransport(BaseTransport):
    def __init__(self, http_uri: str):
        super().__init__()
        self._http_uri = http_uri
        self.session = PersistentHTTPSession()

    async def _send_request(self, request: RequestMessage) -> ResponseMessage:
        data = json.dumps(request.dict()).encode("utf-8")
        self.logger.debug("outbound: %s", data.decode())
        payload = BytesPayload(data, content_type="application/json")
        async with self.session as session:
            async with session.get(self._http_uri, data=payload) as resp:
                res = await resp.read()
        parsed = self._parse_message(res)
        assert isinstance(parsed, ResponseMessage)
        return parsed

    async def close(self):
        await self.session.close()


def get_transport(uri) -> BaseTransport:
    w3: BaseTransport
    if uri.startswith("ws://") or uri.startswith("wss://"):
        w3 = WebsocketTransport(uri)
    elif uri.startswith("http://") or uri.startswith("https://"):
        w3 = HTTPTransport(uri)
    else:
        w3 = IPCTransport(uri)
    return w3
