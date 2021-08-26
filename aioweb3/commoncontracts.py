from .event import EventArgSpec, EventSpec
from .methodcall import MethodCall


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

    Transfer = EventSpec(
        "Transfer",
        [
            EventArgSpec("from", "address", True),
            EventArgSpec("to", "address", True),
            EventArgSpec("value", "uint256", False),
        ],
    )
    Approval = EventSpec(
        "Approval",
        [
            EventArgSpec("owner", "address", True),
            EventArgSpec("spender", "address", True),
            EventArgSpec("value", "uint256", False),
        ],
    )


class DEXPair(ERC20):
    """
    https://docs.uniswap.org/protocol/V2/reference/smart-contracts/pair
    """

    factory = MethodCall("factory", [], ["address"])
    token0 = MethodCall("token0", [], ["address"])
    token1 = MethodCall("token1", [], ["address"])
    getReserves = MethodCall("getReserves", [], ["uint112", "uint112", "uint32"])

    Sync = EventSpec(
        "Sync", [EventArgSpec("reserve0", "uint112"), EventArgSpec("reserve1", "uint112")]
    )
    Swap = EventSpec(
        "Swap",
        [
            EventArgSpec("sender", "address", True),
            EventArgSpec("amount0In", "uint256"),
            EventArgSpec("amount1In", "uint256"),
            EventArgSpec("amount0Out", "uint256"),
            EventArgSpec("amount1Out", "uint256"),
            EventArgSpec("to", "address", True),
        ],
    )
    Mint = EventSpec(
        "Mint",
        [
            EventArgSpec("sender", "address", True),
            EventArgSpec("amount0", "uint"),
            EventArgSpec("amount1", "uint"),
        ],
    )
    Burn = EventSpec(
        "Burn",
        [
            EventArgSpec("sender", "address", True),
            EventArgSpec("amount0", "uint"),
            EventArgSpec("amount1", "uint"),
            EventArgSpec("to", "address", True),
        ],
    )


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
