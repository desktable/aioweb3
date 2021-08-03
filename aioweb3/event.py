from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

import eth_abi
from eth_hash.auto import keccak
from hexbytes import HexBytes

from .types import LogData


@dataclass
class EventArgSpec:
    name: str
    type: str
    indexed: bool


class EventSpec:
    def __init__(self, event_name: str, fields: List[EventArgSpec]):
        self.event_name = event_name
        self.fields = fields

        self.signature = event_name + "(" + ",".join(f.type for f in fields) + ")"
        self.signature_hash = "0x" + keccak(self.signature.encode()).hex()

        self._indexed_fields = [(f.name, f.type) for f in fields if f.indexed]
        self._non_indexed_field_names = [f.name for f in fields if not f.indexed]
        self._non_indexed_field_types = [f.type for f in fields if not f.indexed]

    def __repr__(self):
        return f"<EventSpec: {self.signature}>"

    @property
    def num_indexed_fields(self):
        return len(self._indexed_fields)

    def parse_log(self, log: LogData) -> Dict[str, Any]:
        ret: Dict[str, Any] = {}
        try:
            # verify signature hash
            assert log.topics[0] == self.signature_hash
            # parse indexed fields
            assert len(self._indexed_fields) + 1 == len(log.topics)
            for idx, (name, type_) in enumerate(self._indexed_fields):
                parsed = eth_abi.decode_abi([type_], bytes(HexBytes(log.topics[idx + 1])))[0]
                ret[name] = parsed
            # parse non-indexed fields
            parsed = eth_abi.decode_abi(self._non_indexed_field_types, bytes(HexBytes(log.data)))
            ret.update(zip(self._non_indexed_field_names, parsed))
        except Exception as exc:
            raise ValueError(f"Failed to parse log {log} using parser {self}") from exc
        return ret


@dataclass
class ParsedEvent:
    event_spec: "EventSpec"
    fields: Dict[str, Any]
    log: LogData


class EventParser:
    def __init__(self, event_specs: List[EventSpec]):
        self.event_specs = {event_spec.signature_hash: event_spec for event_spec in event_specs}

    def parse_logs(self, logs: List[LogData]) -> Iterable[ParsedEvent]:
        for log in logs:
            if not log.topics:
                continue
            event_spec = self.event_specs.get(log.topics[0])
            if event_spec and 1 + event_spec.num_indexed_fields == len(log.topics):
                fields = event_spec.parse_log(log)
                yield ParsedEvent(event_spec, fields, log)
