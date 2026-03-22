"""
VCore Agent Chat Platform - Database Layer
SQLite via aiosqlite for async FastAPI compatibility.
"""

import json
import sqlite3
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import DB_PATH, CHANNELS, AGENTS

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  TEXT    NOT NULL,
    agent_id    TEXT    NOT NULL,
    agent_name  TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    msg_type    TEXT    NOT NULL DEFAULT 'text',   -- text | system | reaction
    metadata    TEXT,                               -- JSON blob
    created_at  TEXT    NOT NULL,
    edited_at   TEXT
);

CREATE TABLE IF NOT EXISTS channels (
    id          TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    type        TEXT    NOT NULL DEFAULT 'public',  -- public | private | dm
    description TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS dm_channels (
    id          TEXT    PRIMARY KEY,   -- dm-agentA-agentB (sorted)
    agent_a     TEXT    NOT NULL,
    agent_b     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_messages_agent   ON messages(agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Sync init (called at startup) ─────────────────────────────────────────────

def init_db():
    """Create schema and seed channels synchronously on first run."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        # Seed channels from config
        for ch in CHANNELS:
            conn.execute(
                "INSERT OR IGNORE INTO channels (id, name, type, description, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (ch["id"], ch["name"], ch["type"], ch["description"], _now()),
            )
        conn.commit()


# ── Async helpers ─────────────────────────────────────────────────────────────

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def save_message(
    channel_id: str,
    agent_id: str,
    agent_name: str,
    content: str,
    msg_type: str = "text",
    metadata: Optional[dict] = None,
) -> dict:
    ts = _now()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO messages (channel_id, agent_id, agent_name, content, msg_type, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                channel_id,
                agent_id,
                agent_name,
                content,
                msg_type,
                json.dumps(metadata) if metadata else None,
                ts,
            ),
        )
        await db.commit()
        msg_id = cursor.lastrowid
    return {
        "id": msg_id,
        "channel_id": channel_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "content": content,
        "msg_type": msg_type,
        "metadata": metadata,
        "created_at": ts,
        "edited_at": None,
    }


async def get_messages(channel_id: str, limit: int = 100, before_id: Optional[int] = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if before_id:
            cursor = await db.execute(
                "SELECT * FROM messages WHERE channel_id=? AND id < ? "
                "ORDER BY id DESC LIMIT ?",
                (channel_id, before_id, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM messages WHERE channel_id=? ORDER BY id DESC LIMIT ?",
                (channel_id, limit),
            )
        rows = await cursor.fetchall()
    return [dict(r) for r in reversed(rows)]


async def get_or_create_dm(agent_a: str, agent_b: str) -> str:
    """Return canonical DM channel id (agents sorted alphabetically)."""
    pair = sorted([agent_a, agent_b])
    dm_id = f"dm-{pair[0]}-{pair[1]}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO dm_channels (id, agent_a, agent_b, created_at) VALUES (?, ?, ?, ?)",
            (dm_id, pair[0], pair[1], _now()),
        )
        await db.execute(
            "INSERT OR IGNORE INTO channels (id, name, type, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (dm_id, dm_id, "dm", f"DM: {pair[0]} ↔ {pair[1]}", _now()),
        )
        await db.commit()
    return dm_id


async def get_dm_channels_for_agent(agent_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM dm_channels WHERE agent_a=? OR agent_b=?",
            (agent_id, agent_id),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_all_messages_for_export(date_str: str) -> list:
    """Fetch all messages for a given date (YYYY-MM-DD)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM messages WHERE created_at LIKE ? ORDER BY channel_id, created_at",
            (f"{date_str}%",),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_channel_list() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels ORDER BY type, name")
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
