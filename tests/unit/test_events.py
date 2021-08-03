import json
from collections import Counter
from pathlib import Path

from aioweb3 import commoncontracts as c
from aioweb3.event import EventParser
from aioweb3.types import LogData


def test_can_parse_common_events():
    log_file = Path(__file__).resolve().parent / "logs.json"
    with open(log_file, "rt") as f:
        loaded = json.loads(f.read())
    logs = [LogData(**log) for log in loaded]
    assert len(logs) == 667

    parser = EventParser([c.ERC20.Transfer, c.DEXPair.Swap, c.DEXPair.Sync])
    all_parsed = list(parser.parse_logs(logs))
    assert len(all_parsed) == 287

    ct = Counter(parsed.event_spec for parsed in all_parsed)
    assert ct[c.ERC20.Transfer] == 194
    assert ct[c.DEXPair.Swap] == 46
    assert ct[c.DEXPair.Sync] == 47

    parsed = all_parsed[-1]
    assert parsed.event_spec == c.DEXPair.Swap
    assert parsed.fields == {
        "amount0In": 0,
        "amount0Out": 9674758874794323778,
        "amount1In": 159014267657368539,
        "amount1Out": 0,
        "sender": "0x10ed43c718714eb63d5aa57b78b54704e256024e",
        "to": "0x91411a761431484f6fbaef3d9eea6d62d8f391c4",
    }
