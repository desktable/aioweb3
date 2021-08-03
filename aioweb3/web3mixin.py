from typing import List, Optional

from .aioweb3 import AioWeb3

default_web3: Optional[AioWeb3] = None


class Web3Mixin:
    _web3_stack: List[AioWeb3] = []

    @property
    def web3(self) -> AioWeb3:
        if self._web3_stack:
            return self._web3_stack[-1]
        else:
            assert default_web3 is not None
            return default_web3


class UseWeb3:
    def __init__(self, web3: AioWeb3):
        self.web3 = web3

    def __enter__(self):
        Web3Mixin._web3_stack.append(self.web3)

    def __exit__(self, exc_type, exc_val, exc_tb):
        Web3Mixin._web3_stack.pop()


def set_default_web3(web3: AioWeb3):
    global default_web3
    default_web3 = web3
