from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .analysis import (
    COPING_LIBRARY,
    analyze_emotion,
    build_chat_reply,
    build_journal_insight,
    derive_primary_need,
    derive_support_trend,
    detect_crisis,
    dominant_emotion,
)
from .database import get_connection, init_db, seed_defaults


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class JournalRequest(BaseModel):
    prompt: str
    entry: str = Field(min_length=1, max_length=10000)
    mood_score: int = Field(ge=1, le=10)


class HabitCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=60)


class HabitUpdateRequest(BaseModel):
    done: bool

class VisionCheckRequest(BaseModel):
    detected_emotion: str
    confidence: float = Field(ge=0, le=1)
    note: Optional[str] = ""


class VoiceCheckRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=6000)
    detected_emotion: str
    confidence: float = Field(ge=0, le=1)
    average_volume: Optional[float] = Field(default=None, ge=0, le=1)
    peak_volume: Optional[float] = Field(default=None, ge=0, le=1)
    duration_seconds: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = ""


app = FastAPI(title="Serenity AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parents[2]
init_db()
seed_defaults()


def _iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]


def _get_recent_moods(limit: int = 7) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source, text, primary_emotion, secondary_emotion, intensity, mood_score,
                   crisis_detected, created_at
            FROM mood_entries
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    recent = [dict(row) for row in reversed(rows)]
    for item in recent:
        item["crisis_detected"] = bool(item["crisis_detected"])
    return recent


def _compute_streak(entries: list[dict]) -> int:
    days = sorted({entry["created_at"][:10] for entry in entries}, reverse=True)
    if not days:
        return 0

    streak = 0
    cursor = datetime.utcnow().date()
    index = 0
    while index < len(days):
        if days[index] == cursor.isoformat():
            streak += 1
            cursor -= timedelta(days=1)
            index += 1
            continue
        if streak == 0 and days[index] == (cursor - timedelta(days=1)).isoformat():
            streak += 1
            cursor -= timedelta(days=2)
            index += 1
            continue
        break
    return streak


def _build_dashboard() -> dict:
    with get_connection() as connection:
        mood_rows = _rows_to_dicts(
            connection.execute(
                """
                SELECT id, source, text, primary_emotion, secondary_emotion, intensity, mood_score,
                       crisis_detected, created_at
                FROM mood_entries
                ORDER BY datetime(created_at) ASC
                """
            ).fetchall()
        )
        chat_rows = _rows_to_dicts(
            connection.execute(
                """
                SELECT id, role, content, primary_emotion, secondary_emotion, intensity, mood_score,
                       crisis_detected, created_at
                FROM chat_messages
                ORDER BY datetime(created_at) ASC
                """
            ).fetchall()
        )
        journal_rows = _rows_to_dicts(
            connection.execute(
                """
                SELECT id, prompt, entry, mood_score, primary_emotion, insight, created_at
                FROM journal_entries
                ORDER BY datetime(created_at) DESC
                """
            ).fetchall()
        )
        habits = _rows_to_dicts(
            connection.execute(
                "SELECT id, text, done, created_at FROM habits ORDER BY datetime(created_at) DESC"
            ).fetchall()
        )

        voice_checkins = _rows_to_dicts(
            connection.execute(
                """
                SELECT id, transcript, detected_emotion, confidence, average_volume, peak_volume,
                       duration_seconds, note, created_at
                FROM voice_checkins
                ORDER BY datetime(created_at) DESC
                """
            ).fetchall()
        )
    for item in mood_rows:
        item["crisis_detected"] = bool(item["crisis_detected"])
    for item in chat_rows:
        item["crisis_detected"] = bool(item["crisis_detected"])
    for habit in habits:
        habit["done"] = bool(habit["done"])

    total_check_ins = len(mood_rows)
    average_mood = round(sum(item["mood_score"] for item in mood_rows) / total_check_ins, 1) if total_check_ins else 0.0
    dominant = dominant_emotion([item["primary_emotion"] for item in mood_rows])
    recent_moods = mood_rows[-7:]
    support_trend = derive_support_trend([item["mood_score"] for item in recent_moods])
    latest_emotion = recent_moods[-1]["primary_emotion"] if recent_moods else "calm"
    risk_active = any(item["crisis_detected"] for item in mood_rows)

    emotion_counts = {}
    source_counts = {}
    for item in mood_rows:
        emotion_counts[item["primary_emotion"]] = emotion_counts.get(item["primary_emotion"], 0) + 1
        source_counts[item["source"]] = source_counts.get(item["source"], 0) + 1

    return {
        "summary": {
            "total_check_ins": total_check_ins,
            "streak_count": _compute_streak(mood_rows),
            "dominant_emotion": dominant.title(),
            "today_emotion": latest_emotion.title(),
            "risk_status": "High" if risk_active else "Low",
            "average_mood": average_mood,
            "primary_need": derive_primary_need(dominant),
            "support_trend": support_trend,
        },
        "chat_messages": chat_rows,
        "mood_entries": mood_rows,
        "journal_entries": journal_rows,
        "habits": habits,
        "voice_checkins": voice_checkins,
        "recent_moods": recent_moods,
        "emotion_counts": emotion_counts,
        "source_counts": source_counts,
        "coping_cards": COPING_LIBRARY.get(latest_emotion, COPING_LIBRARY["calm"]),
        "latest_crisis_at": next((item["created_at"] for item in reversed(mood_rows) if item["crisis_detected"]), None),
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/bootstrap")
def bootstrap() -> dict:
    return _build_dashboard()


@app.post("/api/chat")
def post_chat(payload: ChatRequest) -> dict:
    analysis = analyze_emotion(payload.message)
    crisis_detected = detect_crisis(payload.message)
    user_timestamp = _iso_now()
    assistant_timestamp = _iso_now()

    user_message = {
        "id": str(uuid4()),
        "role": "user",
        "content": payload.message.strip(),
        "primary_emotion": analysis["primary_emotion"],
        "secondary_emotion": analysis["secondary_emotion"],
        "intensity": analysis["intensity"],
        "mood_score": analysis["mood_score"],
        "crisis_detected": crisis_detected,
        "created_at": user_timestamp,
    }

    assistant_role = "system" if crisis_detected else "assistant"
    assistant_message = {
        "id": str(uuid4()),
        "role": assistant_role,
        "content": build_chat_reply(payload.message, analysis["primary_emotion"], crisis_detected),
        "primary_emotion": analysis["primary_emotion"],
        "secondary_emotion": analysis["secondary_emotion"],
        "intensity": analysis["intensity"],
        "mood_score": analysis["mood_score"],
        "crisis_detected": crisis_detected,
        "created_at": assistant_timestamp,
    }

    mood_entry = {
        "id": str(uuid4()),
        "source": "chat",
        "text": payload.message.strip(),
        "primary_emotion": analysis["primary_emotion"],
        "secondary_emotion": analysis["secondary_emotion"],
        "intensity": analysis["intensity"],
        "mood_score": analysis["mood_score"],
        "crisis_detected": crisis_detected,
        "created_at": user_timestamp,
    }

    with get_connection() as connection:
        for message in (user_message, assistant_message):
            connection.execute(
                """
                INSERT INTO chat_messages (
                    id, role, content, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message["id"],
                    message["role"],
                    message["content"],
                    message["primary_emotion"],
                    message["secondary_emotion"],
                    message["intensity"],
                    message["mood_score"],
                    int(message["crisis_detected"]),
                    message["created_at"],
                ),
            )

        connection.execute(
            """
            INSERT INTO mood_entries (
                id, source, text, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mood_entry["id"],
                mood_entry["source"],
                mood_entry["text"],
                mood_entry["primary_emotion"],
                mood_entry["secondary_emotion"],
                mood_entry["intensity"],
                mood_entry["mood_score"],
                int(mood_entry["crisis_detected"]),
                mood_entry["created_at"],
            ),
        )

    return {
        "analysis": analysis,
        "crisis_detected": crisis_detected,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "dashboard": _build_dashboard(),
    }


@app.delete("/api/chat")
def clear_chat() -> dict:
    with get_connection() as connection:
        connection.execute("DELETE FROM chat_messages")
    return {"cleared": True, "dashboard": _build_dashboard()}


@app.post("/api/journal")
def post_journal(payload: JournalRequest) -> dict:
    analysis = analyze_emotion(payload.entry)
    crisis_detected = detect_crisis(payload.entry)
    timestamp = _iso_now()
    journal = {
        "id": str(uuid4()),
        "prompt": payload.prompt,
        "entry": payload.entry.strip(),
        "mood_score": payload.mood_score,
        "primary_emotion": analysis["primary_emotion"],
        "insight": build_journal_insight(analysis["primary_emotion"], payload.mood_score),
        "created_at": timestamp,
    }
    mood_entry = {
        "id": str(uuid4()),
        "source": "journal",
        "text": payload.entry.strip(),
        "primary_emotion": analysis["primary_emotion"],
        "secondary_emotion": analysis["secondary_emotion"],
        "intensity": analysis["intensity"],
        "mood_score": payload.mood_score,
        "crisis_detected": crisis_detected,
        "created_at": timestamp,
    }

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO journal_entries (id, prompt, entry, mood_score, primary_emotion, insight, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                journal["id"],
                journal["prompt"],
                journal["entry"],
                journal["mood_score"],
                journal["primary_emotion"],
                journal["insight"],
                journal["created_at"],
            ),
        )
        connection.execute(
            """
            INSERT INTO mood_entries (
                id, source, text, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mood_entry["id"],
                mood_entry["source"],
                mood_entry["text"],
                mood_entry["primary_emotion"],
                mood_entry["secondary_emotion"],
                mood_entry["intensity"],
                mood_entry["mood_score"],
                int(mood_entry["crisis_detected"]),
                mood_entry["created_at"],
            ),
        )

    return {"journal_entry": journal, "dashboard": _build_dashboard(), "crisis_detected": crisis_detected}



@app.post("/api/vision-checkin")
def post_vision_checkin(payload: VisionCheckRequest) -> dict:
    emotion = payload.detected_emotion.strip().lower() or "calm"
    mood_map = {
        "happy": 8,
        "surprised": 6,
        "neutral": 6,
        "calm": 7,
        "sad": 3,
        "angry": 4,
        "fearful": 3,
        "disgusted": 4,
        "anxious": 4,
    }
    normalized_emotion = {
        "fearful": "anxious",
        "surprised": "calm",
        "neutral": "calm",
        "disgusted": "angry",
    }.get(emotion, emotion)
    mood_score = mood_map.get(emotion, mood_map.get(normalized_emotion, 5))
    timestamp = _iso_now()
    text = payload.note.strip() or f"Webcam emotion check detected {emotion}."

    mood_entry = {
        "id": str(uuid4()),
        "source": "vision",
        "text": text,
        "primary_emotion": normalized_emotion,
        "secondary_emotion": "calm",
        "intensity": max(2, min(10, round(payload.confidence * 10))),
        "mood_score": mood_score,
        "crisis_detected": False,
        "created_at": timestamp,
    }
    assistant_message = {
        "id": str(uuid4()),
        "role": "assistant",
        "content": (
            f"Your optional webcam check suggests a {normalized_emotion} expression with "
            f"{round(payload.confidence * 100)}% confidence. I treat this as a hint, not a fact. "
            "If you want, pair it with a text check-in so we can respond more accurately."
        ),
        "primary_emotion": normalized_emotion,
        "secondary_emotion": "calm",
        "intensity": mood_entry["intensity"],
        "mood_score": mood_score,
        "crisis_detected": False,
        "created_at": timestamp,
    }

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO mood_entries (
                id, source, text, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mood_entry["id"],
                mood_entry["source"],
                mood_entry["text"],
                mood_entry["primary_emotion"],
                mood_entry["secondary_emotion"],
                mood_entry["intensity"],
                mood_entry["mood_score"],
                0,
                mood_entry["created_at"],
            ),
        )
        connection.execute(
            """
            INSERT INTO chat_messages (
                id, role, content, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assistant_message["id"],
                assistant_message["role"],
                assistant_message["content"],
                assistant_message["primary_emotion"],
                assistant_message["secondary_emotion"],
                assistant_message["intensity"],
                assistant_message["mood_score"],
                0,
                assistant_message["created_at"],
            ),
        )

    return {"vision_entry": mood_entry, "dashboard": _build_dashboard()}


@app.post("/api/voice-checkin")
def post_voice_checkin(payload: VoiceCheckRequest) -> dict:
    detected_emotion = payload.detected_emotion.strip().lower() or "calm"
    normalized_emotion = {
        "fearful": "anxious",
        "surprised": "calm",
        "neutral": "calm",
        "disgusted": "angry",
    }.get(detected_emotion, detected_emotion)
    mood_map = {
        "happy": 8,
        "calm": 7,
        "anxious": 4,
        "sad": 3,
        "angry": 4,
        "exhausted": 3,
    }
    timestamp = _iso_now()
    transcript = payload.transcript.strip()
    mood_score = mood_map.get(normalized_emotion, 5)
    intensity = max(2, min(10, round(payload.confidence * 10)))

    voice_row = {
        "id": str(uuid4()),
        "transcript": transcript,
        "detected_emotion": normalized_emotion,
        "confidence": payload.confidence,
        "average_volume": payload.average_volume,
        "peak_volume": payload.peak_volume,
        "duration_seconds": payload.duration_seconds,
        "note": payload.note.strip() if payload.note else "",
        "created_at": timestamp,
    }

    mood_entry = {
        "id": str(uuid4()),
        "source": "voice",
        "text": transcript,
        "primary_emotion": normalized_emotion,
        "secondary_emotion": "calm",
        "intensity": intensity,
        "mood_score": mood_score,
        "crisis_detected": detect_crisis(transcript),
        "created_at": timestamp,
    }

    assistant_message = {
        "id": str(uuid4()),
        "role": "assistant",
        "content": (
            f"I heard: \"{transcript}\". Based on the transcript plus voice cues, the strongest hint looks "
            f"{normalized_emotion} with {round(payload.confidence * 100)}% confidence. I treat voice as a clue, "
            "not a fact, so combining it with a typed check-in gives the safest result."
        ),
        "primary_emotion": normalized_emotion,
        "secondary_emotion": "calm",
        "intensity": intensity,
        "mood_score": mood_score,
        "crisis_detected": mood_entry["crisis_detected"],
        "created_at": timestamp,
    }

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO voice_checkins (
                id, transcript, detected_emotion, confidence, average_volume, peak_volume, duration_seconds, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                voice_row["id"],
                voice_row["transcript"],
                voice_row["detected_emotion"],
                voice_row["confidence"],
                voice_row["average_volume"],
                voice_row["peak_volume"],
                voice_row["duration_seconds"],
                voice_row["note"],
                voice_row["created_at"],
            ),
        )
        connection.execute(
            """
            INSERT INTO mood_entries (
                id, source, text, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mood_entry["id"],
                mood_entry["source"],
                mood_entry["text"],
                mood_entry["primary_emotion"],
                mood_entry["secondary_emotion"],
                mood_entry["intensity"],
                mood_entry["mood_score"],
                int(mood_entry["crisis_detected"]),
                mood_entry["created_at"],
            ),
        )
        connection.execute(
            """
            INSERT INTO chat_messages (
                id, role, content, primary_emotion, secondary_emotion, intensity, mood_score, crisis_detected, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assistant_message["id"],
                assistant_message["role"],
                assistant_message["content"],
                assistant_message["primary_emotion"],
                assistant_message["secondary_emotion"],
                assistant_message["intensity"],
                assistant_message["mood_score"],
                int(assistant_message["crisis_detected"]),
                assistant_message["created_at"],
            ),
        )

    return {"voice_checkin": voice_row, "dashboard": _build_dashboard()}


@app.get("/api/habits")
def get_habits() -> dict:
    with get_connection() as connection:
        habits = _rows_to_dicts(
            connection.execute("SELECT id, text, done, created_at FROM habits ORDER BY datetime(created_at) DESC").fetchall()
        )
    for habit in habits:
        habit["done"] = bool(habit["done"])
    return {"habits": habits}


@app.post("/api/habits")
def create_habit(payload: HabitCreateRequest) -> dict:
    habit = {
        "id": str(uuid4()),
        "text": payload.text.strip(),
        "done": False,
        "created_at": _iso_now(),
    }
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO habits (id, text, done, created_at) VALUES (?, ?, ?, ?)",
            (habit["id"], habit["text"], 0, habit["created_at"]),
        )
    return {"habit": habit, "dashboard": _build_dashboard()}


@app.patch("/api/habits/{habit_id}")
def update_habit(habit_id: str, payload: HabitUpdateRequest) -> dict:
    with get_connection() as connection:
        connection.execute("UPDATE habits SET done = ? WHERE id = ?", (int(payload.done), habit_id))
        row = connection.execute("SELECT id, text, done, created_at FROM habits WHERE id = ?", (habit_id,)).fetchone()
    habit = dict(row) if row else None
    if habit:
        habit["done"] = bool(habit["done"])
    return {"habit": habit, "dashboard": _build_dashboard()}


@app.delete("/api/habits/{habit_id}")
def delete_habit(habit_id: str) -> dict:
    with get_connection() as connection:
        connection.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    return {"deleted": True, "dashboard": _build_dashboard()}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return _build_dashboard()


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/styles.css")
def serve_styles() -> FileResponse:
    return FileResponse(ROOT_DIR / "styles.css")


@app.get("/frontend.js")
def serve_frontend_js() -> FileResponse:
    return FileResponse(ROOT_DIR / "frontend.js")