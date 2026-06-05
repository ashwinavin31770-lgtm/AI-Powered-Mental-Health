PRAGMA foreign_keys = ON;

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