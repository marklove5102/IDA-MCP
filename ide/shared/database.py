"""Unified SQLite database store for all IDE configuration.

Tables:
    ide_config       — single-row key-value store for IdeConfig fields
    ida_mcp_config   — single-row key-value store for IdaMcpConfig fields
    model_providers  — one row per LLM model provider
    mcp_servers      — one row per MCP server entry
    skills           — one row per skill entry
"""

from __future__ import annotations

import sqlite3
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any

from shared.paths import ensure_directory, get_ide_user_config_root

DATABASE_FILENAME = "ide.db"

_SCHEMA_VERSION = 1


def _coerce(value: str, target_type: type) -> Any:
    """Coerce a string value from SQLite to the target Python type."""
    if target_type is bool:
        return value.lower() in ("1", "true", "yes")
    if target_type is int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    if target_type is float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    return value

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS _meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ide_config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ida_mcp_config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_providers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL DEFAULT '',
    base_url    TEXT    NOT NULL DEFAULT '',
    api_key     TEXT    NOT NULL DEFAULT '',
    api_mode    TEXT    NOT NULL DEFAULT 'openai_compatible',
    model_name  TEXT    NOT NULL DEFAULT '',
    top_p       REAL    NOT NULL DEFAULT 1.0,
    temperature REAL    NOT NULL DEFAULT 0.7,
    enabled     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS mcp_servers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL DEFAULT '',
    url     TEXT    NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS skills (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL DEFAULT '',
    description TEXT    NOT NULL DEFAULT '',
    enabled     INTEGER NOT NULL DEFAULT 1
);
"""


def _default_db_path() -> Path:
    root = ensure_directory(get_ide_user_config_root())
    return root / DATABASE_FILENAME


class DatabaseStore:
    """Thin wrapper around a single SQLite database for IDE config."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def db_path(self) -> Path:
        return self._db_path

    # --- KV store operations (for single-row configs) ---

    def load_kv(self, table: str) -> dict[str, str]:
        """Load all key-value pairs from a config table."""
        self._validate_table_name(table)
        with self._connect() as conn:
            rows = conn.execute(f"SELECT key, value FROM {table}").fetchall()
        return dict(rows)

    def load_kv_typed(self, table: str, dataclass_cls: type) -> dict[str, Any]:
        """Load KV pairs and coerce string values to match *dataclass_cls* field types.

        Returns a dict suitable for passing to ``SomeDataclass.from_dict(...)``.
        """
        raw = self.load_kv(table)
        if not raw:
            return {}
        field_types: dict[str, type] = {}
        for f in dc_fields(dataclass_cls):
            # Unwrap Optional[X] → X
            ann = f.type
            if isinstance(ann, str):
                # Handle forward refs like "str | None"
                if "| None" in ann or "Optional[" in ann:
                    field_types[f.name] = str
                else:
                    field_types[f.name] = eval(ann)  # noqa: S307
            else:
                import typing
                origin = getattr(ann, "__origin__", None)
                if origin is typing.Union:
                    # Extract non-None type
                    args = [a for a in ann.__args__ if a is not type(None)]
                    field_types[f.name] = args[0] if args else str
                else:
                    field_types[f.name] = ann

        result: dict[str, Any] = {}
        for key, value in raw.items():
            if key not in field_types:
                continue
            result[key] = _coerce(value, field_types[key])
        return result

    def save_kv(self, table: str, data: dict[str, Any]) -> None:
        """Write key-value pairs into a config table (upsert)."""
        self._validate_table_name(table)
        with self._connect() as conn:
            conn.executemany(
                f"INSERT INTO {table} (key, value) VALUES (?, ?) "
                f"ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [(k, self._serialize(v)) for k, v in data.items()],
            )
            conn.commit()

    def delete_kv(self, table: str, keys: list[str]) -> None:
        """Delete specific keys from a config table."""
        if not keys:
            return
        self._validate_table_name(table)
        placeholders = ", ".join("?" for _ in keys)
        with self._connect() as conn:
            conn.execute(
                f"DELETE FROM {table} WHERE key IN ({placeholders})", keys
            )
            conn.commit()

    # --- Row-based operations (for mcp_servers, skills) ---

    def load_rows(self, table: str) -> list[dict[str, Any]]:
        """Load all rows from a table as list of dicts."""
        self._validate_table_name(table)
        with self._connect() as conn:
            cursor = conn.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def insert_row(self, table: str, **values: Any) -> int:
        """Insert a row and return the new rowid."""
        self._validate_table_name(table)
        cols = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        serialized = [self._serialize(v) for v in values.values()]
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                serialized,
            )
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    def update_row(self, table: str, row_id: int, **values: Any) -> bool:
        """Update a row by id. Returns True if a row was updated."""
        self._validate_table_name(table)
        set_clause = ", ".join(f"{k} = ?" for k in values)
        serialized = [self._serialize(v) for v in values.values()] + [row_id]
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE id = ?", serialized
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_row(self, table: str, row_id: int) -> bool:
        """Delete a row by id. Returns True if a row was deleted."""
        self._validate_table_name(table)
        with self._connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM {table} WHERE id = ?", (row_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create tables and set schema version if needed."""
        ensure_directory(self._db_path.parent)
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLES_SQL)
            conn.execute(
                "INSERT OR IGNORE INTO _meta (key, value) VALUES (?, ?)",
                ("schema_version", str(_SCHEMA_VERSION)),
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _serialize(value: Any) -> Any:
        """Convert Python values to SQLite-compatible types."""
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, float):
            return str(value)
        if value is None:
            return ""
        return value

    _VALID_TABLES = frozenset({
        "ide_config",
        "ida_mcp_config",
        "model_providers",
        "mcp_servers",
        "skills",
    })

    @classmethod
    def _validate_table_name(cls, table: str) -> None:
        if table not in cls._VALID_TABLES:
            raise ValueError(f"Invalid table name: {table!r}")
