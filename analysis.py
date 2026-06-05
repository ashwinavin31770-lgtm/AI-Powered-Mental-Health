from __future__ import annotations

from collections import Counter

EMOTION_KEYWORDS = {
    "anxious": ["anxious", "panic", "worried", "overthinking", "nervous", "restless", "fear", "stressed", "overwhelmed"],
    "sad": ["sad", "down", "empty", "hopeless", "crying", "lonely", "grief", "worthless", "tired"],
    "angry": ["angry", "furious", "irritated", "annoyed", "frustrated", "upset"],
    "calm": ["calm", "peaceful", "grounded", "steady", "relieved", "okay", "grateful"],
    "happy": ["happy", "good", "joyful", "excited", "hopeful", "lighter", "proud"],
    "exhausted": ["exhausted", "burned out", "drained", "fatigued", "sleepy", "numb"],
}

CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "self harm",
    "self-harm",
    "want to die",
    "end my life",
    "not worth living",
    "hurt myself",
]

COPING_LIBRARY = {
    "anxious": [
        {"title": "Box Breathing", "body": "Inhale 4 seconds, hold 4, exhale 4, hold 4. Repeat 4 rounds to reduce physical tension."},
        {"title": "Name Five Things", "body": "Ground yourself by naming five things you see, four you feel, three you hear, two you smell, and one you taste."},
    ],
    "sad": [
        {"title": "Micro-connection", "body": "Send one small message to someone safe. Support can begin with a single sentence."},
        {"title": "Self-compassion reframe", "body": "Write down the thought hurting most right now, then answer it as you would for a close friend."},
    ],
    "angry": [
        {"title": "Pause Before Reply", "body": "Step away from the trigger for two minutes and unclench your jaw, shoulders, and hands before responding."},
        {"title": "Fast Discharge", "body": "Try a brisk walk, wall push, or 30-second shakeout to release physical activation."},
    ],
    "calm": [
        {"title": "Protect the Progress", "body": "Note what helped you feel stable today so you can repeat it intentionally."},
        {"title": "Gentle Habit Anchor", "body": "Stack one healthy habit onto an existing routine, such as hydration after brushing your teeth."},
    ],
    "happy": [
        {"title": "Savoring Practice", "body": "Write down what is going well and why it matters. Positive moments become more durable when noticed clearly."},
        {"title": "Future Buffer", "body": "Use this higher-energy moment to prepare one small support tool for a harder day."},
    ],
    "exhausted": [
        {"title": "Lower the Bar", "body": "Pick the smallest useful next step, not the perfect one. Recovery often starts with gentleness."},
        {"title": "Basic Needs Reset", "body": "Check water, food, rest, and screen exposure. Burnout often worsens when the basics slip."},
    ],
}


def normalize_text(text: str) -> str:
    return text.lower().strip()


def detect_crisis(text: str) -> bool:
    normalized = normalize_text(text)
    return any(keyword in normalized for keyword in CRISIS_KEYWORDS)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def map_emotion_to_mood(emotion: str, intensity: int) -> int:
    mood_map = {
        "happy": 8,
        "calm": 7,
        "anxious": 4,
        "sad": 3,
        "angry": 4,
        "exhausted": 3,
    }
    base = mood_map.get(emotion, 5)
    if emotion in {"happy", "calm"}:
        return min(10, base + intensity // 4)
    return max(1, base - intensity // 5)


def analyze_emotion(text: str) -> dict:
    normalized = normalize_text(text)
    scores = [
        {"emotion": emotion, "score": _count_keyword_hits(normalized, keywords)}
        for emotion, keywords in EMOTION_KEYWORDS.items()
    ]
    scores.sort(key=lambda item: item["score"], reverse=True)

    top = scores[0]
    secondary = scores[1]
    primary_emotion = top["emotion"] if top["score"] > 0 else "calm"
    secondary_emotion = secondary["emotion"] if secondary["score"] > 0 else "calm"
    intensity = min(10, max(2, top["score"] * 3 + secondary["score"]))
    mood_score = map_emotion_to_mood(primary_emotion, intensity)

    return {
        "primary_emotion": primary_emotion,
        "secondary_emotion": secondary_emotion,
        "intensity": intensity,
        "mood_score": mood_score,
        "scores": scores,
    }


def build_chat_reply(text: str, primary_emotion: str, crisis_detected: bool) -> str:
    if crisis_detected:
        return (
            "I'm really glad you said that out loud. I'm not the right support for keeping you safe in this moment. "
            "Please contact local emergency services now if you might act on these thoughts, and reach out to a trusted "
            "person immediately. If you are in the United States, call or text 988. In India, call Tele-MANAS at 14416. "
            "Stay with another person if you can."
        )

    intros = {
        "anxious": "That sounds really heavy, and it makes sense that your mind is having trouble settling.",
        "sad": "I'm sorry this feels so painful right now. You do not have to carry it perfectly.",
        "angry": "It sounds like something has pushed you past your comfortable limit today.",
        "exhausted": "You sound worn down, and that kind of emotional fatigue can make everything feel harder.",
        "happy": "I'm glad there is some lightness here. It is worth noticing moments like this.",
        "calm": "Thank you for checking in. I'm here with you.",
    }

    normalized = normalize_text(text)
    suggestions = COPING_LIBRARY.get(primary_emotion, COPING_LIBRARY["calm"])
    if "sleep" in normalized:
        follow_up = "Would it help if we shift into a short wind-down routine for tonight?"
    elif "work" in normalized or "study" in normalized:
        follow_up = "Would you like help breaking the pressure into one manageable next step?"
    else:
        follow_up = "Would you like a grounding exercise, a journaling prompt, or a small action plan?"

    suggestion = suggestions[0]
    return (
        f"{intros[primary_emotion]} I'm noticing a {primary_emotion} tone in your message. "
        f"A gentle next step could be: {suggestion['title'].lower()} - {suggestion['body']} {follow_up}"
    )


def build_journal_insight(primary_emotion: str, mood_score: int) -> str:
    reflections = {
        "anxious": "Your writing suggests a need for safety, predictability, and a smaller next step. Try reducing the situation to what you can control in the next 10 minutes.",
        "sad": "There is a sadness theme here, but also an opening for self-kindness. Consider naming what hurts and what support would feel least overwhelming.",
        "angry": "This entry carries frustration and tension. It may help to separate what triggered you, what it meant to you, and what boundary is needed now.",
        "exhausted": "Your reflection sounds depleted. Rest may need to come before problem-solving. A lighter plan could be more effective than pushing harder.",
        "happy": "There is warmth and resilience in this entry. Capture the conditions that supported this feeling so you can revisit them intentionally.",
        "calm": "Your writing shows thoughtfulness and balance. This could be a good time to strengthen routines that help you stay grounded.",
    }
    return f"{reflections.get(primary_emotion, reflections['calm'])} Current self-rated mood: {mood_score}/10."


def derive_primary_need(emotion: str) -> str:
    return {
        "anxious": "Grounding",
        "sad": "Connection",
        "angry": "Release",
        "exhausted": "Rest",
        "happy": "Reinforcement",
        "calm": "Reflection",
    }.get(emotion, "Reflection")


def derive_support_trend(mood_scores: list[int]) -> str:
    if len(mood_scores) < 3:
        return "Building baseline"

    split = (len(mood_scores) + 1) // 2
    first_half = mood_scores[:split]
    second_half = mood_scores[split:]
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    delta = second_avg - first_avg

    if delta > 0.8:
        return "Improving"
    if delta < -0.8:
        return "Needs attention"
    return "Steady"


def dominant_emotion(items: list[str]) -> str:
    if not items:
        return "calm"
    return Counter(items).most_common(1)[0][0]