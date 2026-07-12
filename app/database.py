"""SQLite persistence for the track library."""

import json
import sqlite3
import threading
import time
import uuid
from typing import Any, Optional

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT '',
    album TEXT NOT NULL DEFAULT '',
    genre TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    lyrics TEXT NOT NULL DEFAULT '',
    engine TEXT NOT NULL DEFAULT '',
    duration REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'queued',
    error TEXT NOT NULL DEFAULT '',
    audio_path TEXT NOT NULL DEFAULT '',
    cover_path TEXT NOT NULL DEFAULT '',
    params TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    config.ensure_dirs()
    with _lock, _connect() as conn:
        conn.executescript(SCHEMA)


def create_track(
    title: str,
    artist: str,
    album: str,
    genre: str,
    prompt: str,
    lyrics: str,
    engine: str,
    duration: float,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    track_id = uuid.uuid4().hex[:12]
    row = {
        "id": track_id,
        "title": title,
        "artist": artist,
        "album": album,
        "genre": genre,
        "prompt": prompt,
        "lyrics": lyrics,
        "engine": engine,
        "duration": duration,
        "status": "queued",
        "error": "",
        "audio_path": "",
        "cover_path": "",
        "params": json.dumps(params or {}),
        "created_at": time.time(),
    }
    with _lock, _connect() as conn:
        conn.execute(
            """INSERT INTO tracks (id, title, artist, album, genre, prompt, lyrics,
               engine, duration, status, error, audio_path, cover_path, params, created_at)
               VALUES (:id, :title, :artist, :album, :genre, :prompt, :lyrics,
               :engine, :duration, :status, :error, :audio_path, :cover_path, :params, :created_at)""",
            row,
        )
    return row


def update_track(track_id: str, **fields: Any) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{k} = :{k}" for k in fields)
    fields["id"] = track_id
    with _lock, _connect() as conn:
        conn.execute(f"UPDATE tracks SET {assignments} WHERE id = :id", fields)


def get_track(track_id: str) -> Optional[dict[str, Any]]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    return dict(row) if row else None


def list_tracks() -> list[dict[str, Any]]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM tracks ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def delete_track(track_id: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
