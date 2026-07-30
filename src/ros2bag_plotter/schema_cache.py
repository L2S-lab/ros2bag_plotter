from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DB_OBJECT_NAME = "msg_schemas"
DB_VERSION = 2
SCHEMA_PAYLOAD_VERSION = 1


class SchemaCache:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or (Path.home() / ".ros2bag_plotter_schemas.db")
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
                    CREATE TABLE msg_schemas (
                        type_name TEXT PRIMARY KEY,
                        msg_definition TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                version = 1
            self._set_db_version(con, version)

        if version < 2:
            if not self._column_exists(con, DB_OBJECT_NAME, "payload_version"):
                con.execute(
                    """
                    ALTER TABLE msg_schemas
                    ADD COLUMN payload_version INTEGER NOT NULL DEFAULT 1
                    """
                )
            version = 2
            self._set_db_version(con, version)

    def get_schema(self, type_name: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute("SELECT msg_definition FROM msg_schemas WHERE type_name=?", (type_name,))
            row = cur.fetchone()
            return row[0] if row else None

    def upsert_schema(
        self,
        type_name: str,
        msg_definition: str,
        payload_version: int = SCHEMA_PAYLOAD_VERSION,
    ):
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO msg_schemas(type_name, msg_definition, payload_version)
                VALUES(?, ?, ?)
                ON CONFLICT(type_name) DO UPDATE SET
                    msg_definition=excluded.msg_definition,
                    payload_version=excluded.payload_version
                """,
                (type_name, msg_definition, int(payload_version)),
            )
            con.commit()
