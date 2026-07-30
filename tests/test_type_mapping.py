from __future__ import annotations

import json
import sqlite3

import numpy as np

from ros2bag_plotter.type_mapping import TypeMappingStore, decode_with_multifield_mapping


class _Msg:
    def __init__(self):
        self.temperature = 42.0
        self.values = np.array([10.0, 11.0, 12.0], dtype=np.float32)


def test_decode_multifield_mapping_uses_zero_based_channels():
    mapping = {
        "fields": [
            {"path": "values", "alias": "values", "mode": "array_channels"},
            {"path": "temperature", "alias": "temp", "mode": "scalar"},
        ]
    }
    out = decode_with_multifield_mapping(_Msg(), mapping)
    assert out["values_channel_0"] == 10.0
    assert out["values_channel_2"] == 12.0
    assert out["temp"] == 42.0


def test_mapping_store_migrates_and_normalizes_legacy_payload(tmp_path):
    db_path = tmp_path / "legacy_mappings.db"
    with sqlite3.connect(db_path) as con:
        con.execute("CREATE TABLE type_mappings (type_name TEXT PRIMARY KEY, mapping_json TEXT NOT NULL)")
        con.execute(
            "INSERT INTO type_mappings(type_name, mapping_json) VALUES(?, ?)",
            (
                "my_pkg/msg/MyCustom",
                json.dumps({"path": "values", "mode": "array_channels", "name": "vals"}),
            ),
        )
        con.commit()

    store = TypeMappingStore(db_path=db_path)
    got = store.get("my_pkg/msg/MyCustom")
    assert got is not None
    assert got["fields"][0]["path"] == "values"
    assert got["fields"][0]["alias"] == "vals"
    assert got["fields"][0]["mode"] == "array_channels"

    with sqlite3.connect(db_path) as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(type_mappings)").fetchall()]
        assert "mapping_version" in cols
        assert "updated_at" in cols
