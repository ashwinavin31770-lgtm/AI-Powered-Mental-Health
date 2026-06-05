from __future__ import annotations

import sqlite3
import tempfile
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = Path(tempfile.gettempdir()) / "serenity-ai-data"
DATA_DIR = Path(os.environ.get("SERENITY_DATA_DIR", DEFAULT_DATA_DIR))
DB_PATH = DATA_DIR / "serenity_ai.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = MEMORY;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    connection.execute("PRAGMA temp_store = MEMORY;")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                primary_emotion TEXT,
                secondary_emotion TEXT,
                intensity INTEGER,
                mood_score INTEGER,
                crisis_detected INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mood_entries (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                primary_emotion TEXT NOT NULL,
                secondary_emotion TEXT NOT NULL,
                intensity INTEGER NOT NULL,
                mood_score INTEGER NOT NULL,
                crisis_detected INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                entry TEXT NOT NULL,
                mood_score INTEGER NOT NULL,
                primary_emotion TEXT NOT NULL,
                insight TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS voice_checkins (
                id TEXT PRIMARY KEY,
                transcript TEXT NOT NULL,
                detected_emotion TEXT NOT NULL,
                confidence REAL NOT NULL,
                average_volume REAL,
                peak_volume REAL,
                duration_seconds REAL,
                note TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def seed_defaults() -> None:
    defaults = [
        "Drink water after waking up",
        "Take three slow breaths before bed",
        "Write one thing I handled well today",
    ]
    with get_connection() as connection:
        existing = connection.execute("SELECT COUNT(*) AS count FROM habits").fetchone()["count"]
        if existing:
            return
        for index, text in enumerate(defaults, start=1):
            connection.execute(
                "INSERT INTO habits (id, text, done, created_at) VALUES (?, ?, 0, datetime('now'))",
                (f"default-habit-{index}", text),
            )