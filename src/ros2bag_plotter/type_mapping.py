from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .export_contract import make_channel_name

NUMERIC_SCALARS = (int, float, bool)
INTERNAL_KEYS = {"__msgtype__"}
DB_OBJECT_NAME = "type_mappings"
DB_VERSION = 3
CURRENT_MAPPING_VERSION = 2


class TypeMappingStore:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or (Path.home() / ".ros2bag_plotter_mappings.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as con:
            self._migrate(con)
            con.commit()

    @staticmethod
    def _table_exists(con: sqlite3.Connection, table_name: str) -> bool:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _column_exists(con: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        rows = con.execute(f"PRAGMA table_info({table_name})").fetchall()
        return any(r[1] == column_name for r in rows)

    def _get_db_version(self, con: sqlite3.Connection) -> int:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                name TEXT PRIMARY KEY,
                version INTEGER NOT NULL
            )
            """
        )
        row = con.execute(
            "SELECT version FROM schema_versions WHERE name=?",
            (DB_OBJECT_NAME,),
        ).fetchone()
        return int(row[0]) if row else 0

    def _set_db_version(self, con: sqlite3.Connection, version: int):
        con.execute(
            """
            INSERT INTO schema_versions(name, version)
            VALUES(?, ?)
            ON CONFLICT(name) DO UPDATE SET version=excluded.version
            """,
            (DB_OBJECT_NAME, int(version)),
        )

    def _migrate(self, con: sqlite3.Connection):
        version = self._get_db_version(con)

        if version == 0:
            if self._table_exists(con, DB_OBJECT_NAME):
                version = 1
            else:
                con.execute(
                    """
                    CREATE TABLE type_mappings (
                        type_name TEXT PRIMARY KEY,
                        mapping_json TEXT NOT NULL
                    )
                    """
                )
                version = 1
            self._set_db_version(con, version)

        if version < 2:
            if not self._column_exists(con, DB_OBJECT_NAME, "mapping_version"):
                con.execute(
                    """
                    ALTER TABLE type_mappings
                    ADD COLUMN mapping_version INTEGER NOT NULL DEFAULT 1
                    """
                )
            version = 2
            self._set_db_version(con, version)

        if version < 3:
            if not self._column_exists(con, DB_OBJECT_NAME, "updated_at"):
                con.execute(
                    """
                    ALTER TABLE type_mappings
                    ADD COLUMN updated_at TEXT
                    """
                )
                con.execute(
                    """
                    UPDATE type_mappings
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE updated_at IS NULL OR updated_at = ''
                    """
                )
            version = 3
            self._set_db_version(con, version)

    def _normalize_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(mapping, dict):
            return {"mapping_version": CURRENT_MAPPING_VERSION, "fields": []}

        # Current format: {"mapping_version": 2, "fields": [...]}
        if "fields" in mapping and isinstance(mapping.get("fields"), list):
            fields = []
            for item in mapping.get("fields", []):
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                if not path:
                    continue
                alias = item.get("alias", path.replace(".", "_"))
                mode = item.get("mode", "scalar")
                if mode not in {"scalar", "array_channels"}:
                    mode = "scalar"
                fields.append({"path": path, "alias": alias, "mode": mode})
            return {
                "mapping_version": int(mapping.get("mapping_version", CURRENT_MAPPING_VERSION)),
                "fields": fields,
            }

        # Legacy single-field format: {"path": "...", "mode": "...", "name": "..."}
        path = mapping.get("path")
        if path:
            alias = mapping.get("alias") or mapping.get("name") or path.replace(".", "_")
            mode = mapping.get("mode", "scalar")
            if mode not in {"scalar", "array_channels"}:
                mode = "scalar"
            return {
                "mapping_version": CURRENT_MAPPING_VERSION,
                "fields": [{"path": path, "alias": alias, "mode": mode}],
            }

        return {"mapping_version": CURRENT_MAPPING_VERSION, "fields": []}

    def get(self, type_name: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                "SELECT mapping_json, mapping_version FROM type_mappings WHERE type_name=?",
                (type_name,),
            ).fetchone()
            if not row:
                return None
            payload = json.loads(row[0])
            normalized = self._normalize_mapping(payload)
            if "mapping_version" not in normalized:
                normalized["mapping_version"] = int(row[1]) if row[1] is not None else CURRENT_MAPPING_VERSION
            return normalized

    def upsert(self, type_name: str, mapping: Dict[str, Any]):
        normalized = self._normalize_mapping(mapping)
        mapping_version = int(normalized.get("mapping_version", CURRENT_MAPPING_VERSION))
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO type_mappings(type_name, mapping_json, mapping_version, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(type_name) DO UPDATE SET
                    mapping_json=excluded.mapping_json,
                    mapping_version=excluded.mapping_version,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (type_name, json.dumps(normalized), mapping_version),
            )
            con.commit()


def get_by_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur[part]
        else:
            cur = getattr(cur, part)
    return cur


def _is_numeric_scalar(v: Any) -> bool:
    return isinstance(v, NUMERIC_SCALARS)


def _as_sequence(v: Any):
    if isinstance(v, (list, tuple)):
        return list(v)
    if hasattr(v, "tolist"):
        try:
            arr = v.tolist()
            if isinstance(arr, list):
                return arr
        except Exception:
            return None
    if hasattr(v, "__iter__") and not isinstance(v, (str, bytes, dict)):
        try:
            return list(v)
        except Exception:
            return None
    return None


def _is_numeric_array(v: Any) -> bool:
    seq = _as_sequence(v)
    return seq is not None and (len(seq) == 0 or all(_is_numeric_scalar(x) for x in seq))


def _iter_object_fields(v: Any):
    if hasattr(v, "get_fields_and_field_types"):
        for f in v.get_fields_and_field_types().keys():
            yield f, getattr(v, f)
    elif hasattr(v, "__dict__"):
        for f, child in vars(v).items():
            if f in INTERNAL_KEYS:
                continue
            yield f, child


def list_leaf_paths(msg: Any, prefix: str = "") -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    if isinstance(msg, dict):
        for k, v in msg.items():
            if str(k) in INTERNAL_KEYS:
                continue
            p = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict) or hasattr(v, "get_fields_and_field_types") or hasattr(v, "__dict__"):
                out.extend(list_leaf_paths(v, p))
            elif _is_numeric_scalar(v):
                out.append((p, "scalar"))
            elif _is_numeric_array(v):
                out.append((p, "array"))
    elif hasattr(msg, "get_fields_and_field_types") or hasattr(msg, "__dict__"):
        for f, v in _iter_object_fields(msg):
            p = f"{prefix}.{f}" if prefix else f
            if isinstance(v, dict) or hasattr(v, "get_fields_and_field_types") or hasattr(v, "__dict__"):
                out.extend(list_leaf_paths(v, p))
            elif _is_numeric_scalar(v):
                out.append((p, "scalar"))
            elif _is_numeric_array(v):
                out.append((p, "array"))
    else:
        if _is_numeric_scalar(msg):
            out.append((prefix or "value", "scalar"))
        elif _is_numeric_array(msg):
            out.append((prefix or "value", "array"))
    return out


def decode_with_multifield_mapping(msg: Any, mapping: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in mapping.get("fields", []):
        path = item.get("path")
        if not path:
            continue
        alias = item.get("alias", path.replace(".", "_"))
        mode = item.get("mode", "scalar")
        try:
            v = get_by_path(msg, path)
        except Exception:
            continue

        seq = _as_sequence(v)
        if mode == "array_channels" and seq is not None:
            for i, x in enumerate(seq):
                try:
                    out[make_channel_name(alias, i)] = float(x)
                except Exception:
                    out[make_channel_name(alias, i)] = None
        else:
            try:
                out[alias] = float(v)
            except Exception:
                out[alias] = str(v)
    return out
