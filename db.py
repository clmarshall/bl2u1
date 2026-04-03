"""Lightweight SQLite persistence for the inventory feature."""

import json
import os
import sqlite3
from datetime import datetime, timezone

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS inventory_items (
    id              TEXT PRIMARY KEY,
    original_name   TEXT NOT NULL,
    stored_name     TEXT NOT NULL,
    upload_date     TEXT NOT NULL,
    file_size       INTEGER NOT NULL,
    filament_count  INTEGER NOT NULL DEFAULT 0,
    filament_colors TEXT NOT NULL DEFAULT '[]',
    filament_types  TEXT NOT NULL DEFAULT '[]',
    was_converted   INTEGER NOT NULL DEFAULT 0,
    source_printer  TEXT NOT NULL DEFAULT ''
);
"""

_db_path: str = ''


def init_db(db_path: str) -> None:
    """Create the database and table if they don't exist."""
    global _db_path
    _db_path = db_path
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    with _connect() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute(_CREATE_TABLE)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def add_item(
    item_id: str,
    original_name: str,
    stored_name: str,
    file_size: int,
    filament_count: int = 0,
    filament_colors: list | None = None,
    filament_types: list | None = None,
    was_converted: bool = False,
    source_printer: str = '',
) -> dict:
    """Insert a new inventory item. Returns the created row as a dict."""
    upload_date = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        con.execute(
            "INSERT INTO inventory_items "
            "(id, original_name, stored_name, upload_date, file_size, "
            " filament_count, filament_colors, filament_types, was_converted, source_printer) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item_id,
                original_name,
                stored_name,
                upload_date,
                file_size,
                filament_count,
                json.dumps(filament_colors or []),
                json.dumps(filament_types or []),
                int(was_converted),
                source_printer,
            ),
        )
    return _row_to_dict_raw(item_id, original_name, stored_name, upload_date,
                            file_size, filament_count, filament_colors or [],
                            filament_types or [], was_converted, source_printer)


def get_item(item_id: str) -> dict | None:
    """Return a single item or None."""
    with _connect() as con:
        row = con.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
    return _deserialize(row) if row else None


def list_items(sort_by: str = 'upload_date', order: str = 'desc') -> list[dict]:
    """Return all inventory items, sorted."""
    allowed_sort = {'upload_date', 'original_name', 'file_size', 'filament_count'}
    if sort_by not in allowed_sort:
        sort_by = 'upload_date'
    if order.lower() not in ('asc', 'desc'):
        order = 'desc'
    with _connect() as con:
        rows = con.execute(
            f"SELECT * FROM inventory_items ORDER BY {sort_by} {order}"
        ).fetchall()
    return [_deserialize(r) for r in rows]


def delete_item(item_id: str) -> bool:
    """Delete an item by ID. Returns True if a row was deleted."""
    with _connect() as con:
        cur = con.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
    return cur.rowcount > 0


def _deserialize(row: sqlite3.Row) -> dict:
    """Convert a DB row to a dict with JSON fields parsed."""
    d = dict(row)
    d['filament_colors'] = json.loads(d.get('filament_colors', '[]'))
    d['filament_types'] = json.loads(d.get('filament_types', '[]'))
    d['was_converted'] = bool(d.get('was_converted', 0))
    return d


def _row_to_dict_raw(item_id, original_name, stored_name, upload_date,
                     file_size, filament_count, filament_colors,
                     filament_types, was_converted, source_printer) -> dict:
    return {
        'id': item_id,
        'original_name': original_name,
        'stored_name': stored_name,
        'upload_date': upload_date,
        'file_size': file_size,
        'filament_count': filament_count,
        'filament_colors': filament_colors,
        'filament_types': filament_types,
        'was_converted': was_converted,
        'source_printer': source_printer,
    }
