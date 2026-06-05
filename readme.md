
# Serenity AI - Mental Health Companion

Serenity AI is a self-contained mental health companion MVP built with HTML, CSS, and JavaScript. It demonstrates how an empathetic AI-style application can support emotional wellbeing through guided conversation, mood detection, journaling, habit tracking, coping recommendations, and crisis-aware escalation.
Serenity AI is a full-stack mental health companion project built with HTML, CSS, JavaScript, FastAPI, and SQLite. It demonstrates how an empathetic AI-style application can support emotional wellbeing through guided conversation, mood detection, journaling, habit tracking, coping recommendations, and crisis-aware escalation.

## Features

- Conversational companion with empathetic, context-aware replies
- Optional webcam expression check-in saved to mood history
- Optional voice check-in with browser speech-to-text and tone hint
- FastAPI backend for chat, journaling, habits, and dashboard APIs
- SQLite database persistence for moods, journals, habits, and messages
- Rule-based emotion detection from text input
- Mood tracking dashboard with recent trend visualization
- Guided journaling with reflection insights
- Personalized coping strategies based on detected emotion
- Habit builder for daily wellness routines
- Crisis phrase detection with emergency support guidance
- Privacy-friendly local browser storage

## Project Structure

- `index.html` - main application layout
- `styles.css` - visual design, responsive layout, and component styling
- `app.js` - client-side state management, emotion analysis, chat logic, journaling, habits, and dashboard rendering
- `frontend.js` - browser-side API client and UI rendering logic
- `backend/app/main.py` - FastAPI application and REST endpoints
- `backend/app/analysis.py` - emotion analysis, journaling insights, coping recommendations, and crisis detection
- `backend/app/database.py` - SQLite setup and connection helpers
- `backend/init_db.py` - database initialization and default seed data
- `backend/schema.sql` - SQL schema for all persisted tables
- `requirements.txt` - Python dependencies

## How To Run

1. Open `index.html` in any modern browser.
2. Start chatting, journaling, and adding habits.
3. Data is stored locally in the browser using `localStorage`.
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Initialize the SQLite database:

```bash
python -m backend.init_db
```

3. Start the API server:

```bash
uvicorn backend.app.main:app --reload
```

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser.

By default, the SQLite file is stored in the local temp directory to avoid OneDrive locking issues in this workspace:

- Windows default: `%LOCALAPPDATA%\Temp\serenity-ai-data\serenity_ai.db`
- Override location: set `SERENITY_DATA_DIR` before starting the app

## AI Logic

- Webcam analysis uses `face-api.js` in the browser as an optional expression hint.
- Voice check-ins use browser speech-to-text plus lightweight audio-energy heuristics as an optional tone hint.
This MVP uses a lightweight rule-based approach instead of external APIs:
This project uses a lightweight rule-based approach instead of external APIs:

- Emotion detection is keyword-driven.
- Mood scoring is inferred from the detected emotional tone.
- Coping recommendations are mapped from the detected emotion.
- Crisis detection checks for high-risk self-harm language and switches to urgent support messaging.
- All chat messages, mood entries, journals, and habits are stored in SQLite.

## Safety Notes

## Suggested Next Enhancements

- Replace rule-based emotion analysis with a production NLP model
- Add secure backend APIs with authentication and encrypted persistence
- Add authentication, consent tracking, and encrypted at-rest persistence
- Add clinician escalation workflows and trusted-contact alerts
- Add voice check-ins and speech emotion recognition
- Add multilingual support and therapist dashboard views