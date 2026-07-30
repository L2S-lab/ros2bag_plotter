from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .decoders import decode_by_type_and_topic

DecoderFn = Callable[[str, str, Any], Optional[Dict[str, Any]]]


@dataclass
class DecoderEntry:
    name: str
    decoder: DecoderFn


class CustomDecoderRegistry:
    def __init__(self, decoders: List[DecoderEntry] | None = None):
        self._decoders: List[DecoderEntry] = list(decoders or [])

    def register(self, name: str, decoder: DecoderFn):
        self._decoders.append(DecoderEntry(name=name, decoder=decoder))

    def decode(self, topic: str, type_name: str, msg: Any) -> Optional[Dict[str, Any]]:
        for entry in self._decoders:
            try:
                decoded = entry.decoder(topic, type_name, msg)
            except Exception:
                continue
            if decoded:
                return decoded
        return None


def create_default_decoder_registry() -> CustomDecoderRegistry:
    registry = CustomDecoderRegistry()
    registry.register("builtin-topic-type-decoder", decode_by_type_and_topic)
    return registry
