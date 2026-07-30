from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

import pandas as pd

from .bag_reader import Ros2BagReader
from .decoder_registry import CustomDecoderRegistry, create_default_decoder_registry
from .decoding_strategy import is_known_ros_type
from .exporter import save_unknown_raw
from .export_contract import TIME_COLUMN, normalize_frame_for_contract, normalize_record_for_contract
from .msg_flatten import flatten_ros_message
from .schema_cache import SchemaCache
from .type_mapping import TypeMappingStore, decode_with_multifield_mapping

SchemaPromptFn = Callable[[str, str], str | None]
MappingPromptFn = Callable[[str, Any], Dict[str, Any] | None]
ProgressFn = Callable[[int, int], None]


class BagProcessingService:
    def __init__(
        self,
        type_map_store: TypeMappingStore | None = None,
        schema_cache: SchemaCache | None = None,
        decoder_registry: CustomDecoderRegistry | None = None,
    ):
        self.type_map_store = type_map_store or TypeMappingStore()
        self.schema_cache = schema_cache or SchemaCache()
        self.decoder_registry = decoder_registry or create_default_decoder_registry()

    def register_custom_decoder(self, name: str, decoder):
        self.decoder_registry.register(name, decoder)

    def _preload_cached_schemas(self, reader: Ros2BagReader, topic_type_map: Dict[str, str]):
        for type_name in set(topic_type_map.values()):
            if is_known_ros_type(type_name):
                continue
            schema = self.schema_cache.get_schema(type_name)
            if schema:
                reader.register_msg_schema(type_name, schema)

    def _recover_custom_message(
        self,
        reader: Ros2BagReader,
        type_name: str,
        raw: bytes,
        decode_error: Exception | None,
        request_schema: SchemaPromptFn | None,
        declined_types: set[str],
    ):
        cached_schema = self.schema_cache.get_schema(type_name)
        if cached_schema:
            ok, _ = reader.register_msg_schema(type_name, cached_schema)
            if ok:
                msg, _ = reader.decode_raw(raw, type_name)
                if msg is not None:
                    return msg

        if type_name in declined_types or request_schema is None:
            return None

        err_text = str(decode_error) if decode_error is not None else "unknown decode error"
        while True:
            schema = request_schema(type_name, err_text)
            if not schema:
                declined_types.add(type_name)
                return None

            ok, reg_error = reader.register_msg_schema(type_name, schema)
            if not ok:
                err_text = reg_error or err_text
                continue

            self.schema_cache.upsert_schema(type_name, schema)
            msg, decode_err = reader.decode_raw(raw, type_name)
            if msg is not None:
                return msg
            err_text = str(decode_err) if decode_err is not None else err_text

    def load_frames(
        self,
        bag: Path,
        topics: List[str],
        *,
        progress_cb: ProgressFn | None = None,
        request_schema_cb: SchemaPromptFn | None = None,
        request_mapping_cb: MappingPromptFn | None = None,
    ) -> Dict[str, pd.DataFrame]:
        reader = Ros2BagReader(bag)
        selected = topics if topics else None
        topic_type_map = reader.get_topic_type_map()
        self._preload_cached_schemas(reader, topic_type_map)

        total = reader.count_messages(selected)
        if progress_cb:
            progress_cb(0, total)

        rows: Dict[str, List[dict]] = {}
        t0_ns = None
        declined_types: set[str] = set()

        i = 0
        for topic, type_name, ts_ns, raw, msg, err in reader.iter_messages(selected):
            i += 1
            if progress_cb:
                progress_cb(i, total)

            if t0_ns is None:
                t0_ns = ts_ns
            t_sec = (ts_ns - t0_ns) * 1e-9

            if err is not None or msg is None:
                if not is_known_ros_type(type_name):
                    recovered = self._recover_custom_message(
                        reader,
                        type_name,
                        raw,
                        err,
                        request_schema_cb,
                        declined_types,
                    )
                    if recovered is not None:
                        msg = recovered
                        err = None
                if err is not None or msg is None:
                    save_unknown_raw(bag, topic, ts_ns, raw)
                    continue

            rec = {TIME_COLUMN: t_sec}
            if is_known_ros_type(type_name):
                rec.update(flatten_ros_message(msg))
            else:
                plugin_decoded = self.decoder_registry.decode(topic, type_name, msg)
                if plugin_decoded:
                    rec.update(plugin_decoded)
                else:
                    mapping = self.type_map_store.get(type_name)
                    if mapping is None and request_mapping_cb is not None:
                        mapping = request_mapping_cb(type_name, msg)
                        if mapping and mapping.get("fields"):
                            self.type_map_store.upsert(type_name, mapping)
                    if not mapping or not mapping.get("fields"):
                        continue
                    rec.update(decode_with_multifield_mapping(msg, mapping))

            rec = normalize_record_for_contract(rec)
            if len(rec) > 1:
                rows.setdefault(topic, []).append(rec)

        if progress_cb:
            progress_cb(total, total)
        frames: Dict[str, pd.DataFrame] = {}
        for topic, records in rows.items():
            if not records:
                continue
            frames[topic] = normalize_frame_for_contract(pd.DataFrame(records))
        return frames
