const QUICK_REPLIES = [
    "I feel overwhelmed",
    "I am anxious tonight",
    "Help me calm down",
    "I feel lonely",
    "I want to journal",
    "I cannot sleep"
];

const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

const state = {
    summary: {
        total_check_ins: 0,
        streak_count: 0,
        dominant_emotion: "Calm",
        today_emotion: "Balanced",
        risk_status: "Low",
        average_mood: 0,
        primary_need: "Reflection",
        support_trend: "Building baseline"
    },
    chat_messages: [],
    mood_entries: [],
    journal_entries: [],
    habits: [],
    recent_moods: [],
    emotion_counts: {},
    source_counts: {},
    coping_cards: [],
    latest_crisis_at: null,
    latest_crisis_at: null,
    voice_checkins: []
};

const webcamState = {
    stream: null,
    modelsLoaded: false
};
const voiceState = {
    recognition: null,
    audioContext: null,
    analyser: null,
    mediaStream: null,
    mediaSource: null,
    rafId: null,
    samples: [],
    startedAt: null,
    transcript: "",
    detectedEmotion: "calm",
    confidence: 0.5
};


async function api(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
    }

    return response.json();
}

function applyDashboard(payload) {
    state.summary = payload.summary;
    state.chat_messages = payload.chat_messages || [];
    state.mood_entries = payload.mood_entries || [];
    state.journal_entries = payload.journal_entries || [];
    state.habits = payload.habits || [];
    state.recent_moods = payload.recent_moods || [];
    state.emotion_counts = payload.emotion_counts || {};
    state.coping_cards = payload.coping_cards || [];
    state.latest_crisis_at = payload.latest_crisis_at || null;
    state.voice_checkins = payload.voice_checkins || [];
    state.source_counts = payload.source_counts || {};
}

function formatTimestamp(value) {
    return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
    }).format(new Date(value));
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderChat() {
    const chatLog = document.getElementById("chatLog");
    const quickReplies = document.getElementById("quickReplies");

    const messages = state.chat_messages.length
        ? state.chat_messages
        : [{
            id: "welcome",
            role: "assistant",
            content: "Welcome. I'm Serenity AI, a supportive companion for reflection, mood tracking, and gentle coping ideas. How are you feeling right now?",
            created_at: new Date().toISOString()
        }];

    chatLog.innerHTML = messages.map((message) => `
        <article class="message ${message.role}">
            <span class="message-meta">${message.role === "user" ? "You" : message.role === "system" ? "Safety Support" : "Serenity AI"} · ${formatTimestamp(message.created_at)}</span>
            <div>${escapeHtml(message.content)}</div>
        </article>
    `).join("");

    chatLog.scrollTop = chatLog.scrollHeight;
    quickReplies.innerHTML = QUICK_REPLIES.map((reply) => `
        <button class="quick-reply" type="button" data-quick-reply="${escapeHtml(reply)}">${escapeHtml(reply)}</button>
    `).join("");
}

function renderDashboard() {
    document.getElementById("totalCheckIns").textContent = state.summary.total_check_ins;
    document.getElementById("streakCount").textContent = state.summary.streak_count;
    document.getElementById("dominantEmotion").textContent = state.summary.dominant_emotion;
    document.getElementById("todayEmotion").textContent = state.summary.today_emotion;
    document.getElementById("riskStatus").textContent = state.summary.risk_status;
    document.getElementById("averageMood").textContent = `${state.summary.average_mood.toFixed(1)} / 10`;
    document.getElementById("primaryNeed").textContent = state.summary.primary_need;
    document.getElementById("supportTrend").textContent = state.summary.support_trend;

    document.getElementById("chartDateRange").textContent = state.recent_moods.length
        ? `${state.recent_moods[0].created_at.slice(5, 10)} to ${state.recent_moods[state.recent_moods.length - 1].created_at.slice(5, 10)}`
        : "No data yet";

    document.getElementById("moodChart").innerHTML = state.recent_moods.length
        ? state.recent_moods.map((entry) => `
            <div class="chart-bar-row">
                <span>${entry.created_at.slice(5, 10)}</span>
                <div class="chart-track">
                    <div class="chart-fill" style="width: ${entry.mood_score * 10}%"></div>
                </div>
                <strong>${entry.mood_score}</strong>
            </div>
        `).join("")
        : `<p class="hero-text">Start chatting or journaling to see your mood trend here.</p>`;

    const emotionEntries = Object.entries(state.emotion_counts).sort((a, b) => b[1] - a[1]);
    document.getElementById("emotionList").innerHTML = emotionEntries.length
        ? emotionEntries.map(([emotion, count]) => `
            <div class="emotion-pill">
                <span>${escapeHtml(emotion.charAt(0).toUpperCase() + emotion.slice(1))}</span>
                <strong>${count}</strong>
            </div>
        `).join("")
        : `<p class="hero-text">No emotion data yet.</p>`;
}

    const sourceEntries = Object.entries(state.source_counts).sort((a, b) => b[1] - a[1]);
    document.getElementById("sourceList").innerHTML = sourceEntries.length
        ? sourceEntries.map(([source, count]) => `
            <div class="emotion-pill">
                <span>${escapeHtml(source.charAt(0).toUpperCase() + source.slice(1))}</span>
                <strong>${count}</strong>
            </div>
        `).join("")
        : `<p class="hero-text">No source data yet.</p>`;

    const latestVoice = state.voice_checkins?.[0];
    document.getElementById("voiceSummary").innerHTML = latestVoice
        ? `
            <strong>${escapeHtml(latestVoice.detected_emotion.charAt(0).toUpperCase() + latestVoice.detected_emotion.slice(1))}</strong>
            <p class="hero-text">${escapeHtml(latestVoice.transcript)}</p>
            <p class="hero-text">Confidence: ${Math.round(latestVoice.confidence * 100)}%${latestVoice.duration_seconds ? ` · Duration: ${latestVoice.duration_seconds.toFixed(1)}s` : ""}</p>
        `
        : "No voice check-in yet.";

function renderCopingCards() {
    document.getElementById("copingCards").innerHTML = state.coping_cards.map((card) => `
        <article class="coping-card">
            <h4>${escapeHtml(card.title)}</h4>
            <p>${escapeHtml(card.body)}</p>
            <span class="panel-label">Matched to ${escapeHtml(state.summary.today_emotion.toLowerCase())}</span>
        </article>
    `).join("");
}

function renderJournal() {
    const journalList = document.getElementById("journalList");
    journalList.innerHTML = state.journal_entries.length
        ? state.journal_entries.map((entry) => `
            <article class="entry-item">
                <small>${formatTimestamp(entry.created_at)} · Mood ${entry.mood_score}/10 · ${escapeHtml(entry.primary_emotion.charAt(0).toUpperCase() + entry.primary_emotion.slice(1))}</small>
                <h4>${escapeHtml(entry.prompt)}</h4>
                <p>${escapeHtml(entry.entry)}</p>
                <p><strong>Reflection:</strong> ${escapeHtml(entry.insight)}</p>
            </article>
        `).join("")
        : `<p class="hero-text">No journal entries yet. Your reflections will appear here.</p>`;
}

function renderHabits() {
    document.getElementById("habitList").innerHTML = state.habits.map((habit) => `
        <label class="habit-item ${habit.done ? "done" : ""}">
            <input type="checkbox" data-habit-toggle="${habit.id}" ${habit.done ? "checked" : ""}>
            <span>${escapeHtml(habit.text)}</span>
            <button type="button" class="delete-btn" data-habit-delete="${habit.id}">Delete</button>
        </label>
    `).join("");
}

function renderCrisisState() {
    const crisisStatus = document.getElementById("crisisStatus");
    if (state.latest_crisis_at) {
        crisisStatus.classList.remove("safe");
        crisisStatus.textContent = `High-risk language was detected on ${formatTimestamp(state.latest_crisis_at)}. Prioritize urgent human support and emergency resources.`;
        return;
    }
    crisisStatus.classList.add("safe");
    crisisStatus.textContent = "No active crisis language detected.";
}

function renderAll() {
    renderChat();
    renderDashboard();
    renderCopingCards();
    renderJournal();
    renderHabits();
    renderCrisisState();
}

async function bootstrap() {
    const payload = await api("/api/bootstrap");
    applyDashboard(payload);
    renderAll();
}

async function submitChat(text) {
    const trimmed = text.trim();
    if (!trimmed) {
        return;
    }
    const payload = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: trimmed })
    });
    applyDashboard(payload.dashboard);
    renderAll();
}

async function clearChat() {
    const payload = await api("/api/chat", { method: "DELETE" });
    applyDashboard(payload.dashboard);
    renderAll();
}

async function submitJournal(prompt, entry, moodScore) {
    const payload = await api("/api/journal", {
        method: "POST",
        body: JSON.stringify({
            prompt,
            entry,
            mood_score: moodScore
        })
    });
    document.getElementById("journalInsight").textContent = payload.journal_entry.insight;
    applyDashboard(payload.dashboard);
    renderAll();
}

async function createHabit(text) {
    const payload = await api("/api/habits", {
        method: "POST",
        body: JSON.stringify({ text })
    });
    applyDashboard(payload.dashboard);
    renderAll();
}

async function updateHabit(id, done) {
    const payload = await api(`/api/habits/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ done })
    });
    applyDashboard(payload.dashboard);
    renderAll();
}

async function deleteHabit(id) {
    const payload = await api(`/api/habits/${id}`, { method: "DELETE" });
    applyDashboard(payload.dashboard);
    renderAll();
}
function inferVoiceEmotion(transcript, averageVolume, peakVolume) {
    const text = transcript.toLowerCase();
    if (/(anxious|panic|worried|overwhelmed|nervous|stress)/.test(text)) {
        return { emotion: "anxious", confidence: 0.78 };
    }
    if (/(sad|cry|empty|hopeless|lonely|down)/.test(text)) {
        return { emotion: "sad", confidence: 0.8 };
    }
    if (/(angry|annoyed|furious|frustrated|upset)/.test(text)) {
        return { emotion: "angry", confidence: 0.79 };
    }
    if (/(happy|good|great|hopeful|excited|proud)/.test(text)) {
        return { emotion: "happy", confidence: 0.76 };
    }
    if (averageVolume < 0.035 && peakVolume < 0.09) {
        return { emotion: "sad", confidence: 0.58 };
    }
    if (peakVolume > 0.24) {
        return { emotion: "angry", confidence: 0.56 };
    }
    if (averageVolume > 0.09) {
        return { emotion: "anxious", confidence: 0.54 };
    }
    return { emotion: "calm", confidence: 0.52 };
}

function stopVoiceMeters() {
    if (voiceState.rafId) {
        cancelAnimationFrame(voiceState.rafId);
        voiceState.rafId = null;
    }
    if (voiceState.mediaStream) {
        voiceState.mediaStream.getTracks().forEach((track) => track.stop());
        voiceState.mediaStream = null;
    }
    if (voiceState.mediaSource) {
        voiceState.mediaSource.disconnect();
        voiceState.mediaSource = null;
    }
    if (voiceState.audioContext) {
        voiceState.audioContext.close();
        voiceState.audioContext = null;
    }
    voiceState.analyser = null;
}

async function startVoiceCheck() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voiceStatus = document.getElementById("voiceStatus");
    const transcriptField = document.getElementById("voiceTranscript");

    voiceState.samples = [];
    voiceState.transcript = "";
    voiceState.startedAt = performance.now();
    transcriptField.value = "";

    if (!SpeechRecognition) {
        voiceStatus.textContent = "This browser does not support built-in speech-to-text. Try Chrome or Edge.";
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        voiceState.mediaStream = stream;
        voiceState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        voiceState.analyser = voiceState.audioContext.createAnalyser();
        voiceState.analyser.fftSize = 2048;
        voiceState.mediaSource = voiceState.audioContext.createMediaStreamSource(stream);
        voiceState.mediaSource.connect(voiceState.analyser);

        const recognition = new SpeechRecognition();
        recognition.lang = "en-US";
        recognition.interimResults = true;
        recognition.continuous = true;

        recognition.onresult = (event) => {
            let transcript = "";
            for (let i = 0; i < event.results.length; i += 1) {
                transcript += event.results[i][0].transcript + " ";
            }
            voiceState.transcript = transcript.trim();
            transcriptField.value = voiceState.transcript;
        };

        recognition.onerror = () => {
            voiceStatus.textContent = "Speech recognition hit an error. You can still type in the transcript box manually.";
        };

        recognition.onend = () => {
            if (voiceState.recognition === recognition) {
                voiceStatus.textContent = "Voice capture stopped. Review the transcript, then save the result.";
                voiceState.recognition = null;
            }
        };

        voiceState.recognition = recognition;
        recognition.start();

        const buffer = new Uint8Array(voiceState.analyser.fftSize);
        const sampleAudio = () => {
            if (!voiceState.analyser) {
                return;
            }
            voiceState.analyser.getByteTimeDomainData(buffer);
            let sumSquares = 0;
            let peak = 0;
            for (let i = 0; i < buffer.length; i += 1) {
                const centered = (buffer[i] - 128) / 128;
                sumSquares += centered * centered;
                peak = Math.max(peak, Math.abs(centered));
            }
            const rms = Math.sqrt(sumSquares / buffer.length);
            voiceState.samples.push({ rms, peak });
            voiceState.rafId = requestAnimationFrame(sampleAudio);
        };

        sampleAudio();
        voiceStatus.textContent = "Listening now. Speak naturally, then click Stop voice check.";
    } catch (error) {
        console.error(error);
        voiceStatus.textContent = "Microphone access failed. Check browser permissions and try again.";
    }
}

function stopVoiceCheck() {
    if (voiceState.recognition) {
        voiceState.recognition.stop();
        voiceState.recognition = null;
    }
    stopVoiceMeters();

    const transcript = document.getElementById("voiceTranscript").value.trim();
    const samples = voiceState.samples;
    const averageVolume = samples.length
        ? samples.reduce((sum, sample) => sum + sample.rms, 0) / samples.length
        : 0;
    const peakVolume = samples.length
        ? Math.max(...samples.map((sample) => sample.peak))
        : 0;
    const inferred = inferVoiceEmotion(transcript, averageVolume, peakVolume);
    voiceState.detectedEmotion = inferred.emotion;
    voiceState.confidence = inferred.confidence;
    const durationSeconds = voiceState.startedAt ? (performance.now() - voiceState.startedAt) / 1000 : 0;
    voiceState.durationSeconds = durationSeconds;
    voiceState.averageVolume = averageVolume;
    voiceState.peakVolume = peakVolume;

    document.getElementById("voiceStatus").textContent = "Voice capture stopped. Save if the transcript looks correct.";
    document.getElementById("voiceHint").textContent =
        `Voice hint: ${inferred.emotion} (${Math.round(inferred.confidence * 100)}% confidence) · average volume ${averageVolume.toFixed(3)} · peak ${peakVolume.toFixed(3)}.`;
}

async function saveVoiceCheck() {
    const transcript = document.getElementById("voiceTranscript").value.trim();
    if (!transcript) {
        document.getElementById("voiceStatus").textContent = "Record or enter a transcript before saving a voice check-in.";
        return;
    }

    const payload = await api("/api/voice-checkin", {
        method: "POST",
        body: JSON.stringify({
            transcript,
            detected_emotion: voiceState.detectedEmotion || "calm",
            confidence: voiceState.confidence || 0.5,
            average_volume: voiceState.averageVolume ?? null,
            peak_volume: voiceState.peakVolume ?? null,
            duration_seconds: voiceState.durationSeconds ?? null,
            note: "Browser speech-to-text plus audio-energy hint."
        })
    });
    applyDashboard(payload.dashboard);
    renderAll();
    document.getElementById("voiceStatus").textContent = "Voice check-in saved to the dashboard and database.";
}

async function ensureVisionModels() {
    if (webcamState.modelsLoaded) {
        return;
    }

    if (!window.faceapi) {
        throw new Error("Face API library did not load.");
    }

    const modelUrl = "https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/";
    await Promise.all([
        window.faceapi.nets.tinyFaceDetector.loadFromUri(modelUrl),
        window.faceapi.nets.faceExpressionNet.loadFromUri(modelUrl)
    ]);
    webcamState.modelsLoaded = true;
}

async function startCamera() {
    const visionStatus = document.getElementById("visionStatus");
    try {
        await ensureVisionModels();
        webcamState.stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "user" },
            audio: false
        });
        document.getElementById("webcamVideo").srcObject = webcamState.stream;
        visionStatus.textContent = "Camera is live. When you are ready, click Analyze emotion.";
    } catch (error) {
        console.error(error);
        visionStatus.textContent = "Unable to start webcam emotion analysis. Check camera permission and internet access for the model files.";
    }
}

function stopCamera() {
    if (webcamState.stream) {
        webcamState.stream.getTracks().forEach((track) => track.stop());
        webcamState.stream = null;
    }
    document.getElementById("webcamVideo").srcObject = null;
    document.getElementById("visionStatus").textContent = "Camera is off. Start the camera to run a visual mood check.";
}

async function analyzeCameraEmotion() {
    const video = document.getElementById("webcamVideo");
    const canvas = document.getElementById("webcamCanvas");
    const visionStatus = document.getElementById("visionStatus");
    const visionResult = document.getElementById("visionResult");

    if (!video.srcObject) {
        visionStatus.textContent = "Start the camera before analyzing emotion.";
        return;
    }

    await ensureVisionModels();

    const detection = await window.faceapi
        .detectSingleFace(video, new window.faceapi.TinyFaceDetectorOptions())
        .withFaceExpressions();

    if (!detection) {
        visionStatus.textContent = "No face detected clearly enough. Try better lighting and face the camera directly.";
        return;
    }

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const expressions = detection.expressions;
    const topExpression = Object.entries(expressions).sort((a, b) => b[1] - a[1])[0];
    const detectedEmotion = topExpression[0];
    const confidence = Number(topExpression[1].toFixed(4));

    visionStatus.textContent = "Expression detected. Saving webcam check-in to your mood history.";
    visionResult.textContent = `Detected expression: ${detectedEmotion} (${Math.round(confidence * 100)}% confidence).`;

    const payload = await api("/api/vision-checkin", {
        method: "POST",
        body: JSON.stringify({
            detected_emotion: detectedEmotion,
            confidence,
            note: `Webcam check-in detected ${detectedEmotion} with ${Math.round(confidence * 100)}% confidence.`
        })
    });

    applyDashboard(payload.dashboard);
    renderAll();
    visionResult.textContent = `Saved webcam check-in: ${detectedEmotion} (${Math.round(confidence * 100)}% confidence).`;
}

function attachEvents() {
    document.getElementById("chatForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("chatInput");
        await submitChat(input.value);
        input.value = "";
    });

    document.getElementById("quickReplies").addEventListener("click", async (event) => {
        const button = event.target.closest("[data-quick-reply]");
        if (!button) {
            return;
        }
        await submitChat(button.dataset.quickReply);
    });

    document.getElementById("clearChatBtn").addEventListener("click", clearChat);

    document.getElementById("journalForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const prompt = document.getElementById("journalPrompt").value;
        const entry = document.getElementById("journalEntry").value.trim();
        const moodScore = Number(document.getElementById("journalMood").value);
        if (!entry) {
            return;
        }
        await submitJournal(prompt, entry, moodScore);
        document.getElementById("journalEntry").value = "";
    });

    document.getElementById("habitForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = document.getElementById("habitInput");
        const value = input.value.trim();
        if (!value) {
            return;
        }
        await createHabit(value);
        input.value = "";
    });

    document.getElementById("habitList").addEventListener("click", async (event) => {
        const button = event.target.closest("[data-habit-delete]");
        if (!button) {
            return;
        }
        await deleteHabit(button.dataset.habitDelete);
    });

    document.getElementById("habitList").addEventListener("change", async (event) => {
        const checkbox = event.target.closest("[data-habit-toggle]");
        if (!checkbox) {
            return;
        }
        await updateHabit(checkbox.dataset.habitToggle, checkbox.checked);
    });

    document.getElementById("journalMood").addEventListener("input", (event) => {
        document.getElementById("journalMoodValue").textContent = event.target.value;
    });

        document.getElementById("startCameraBtn").addEventListener("click", startCamera);
    document.getElementById("stopCameraBtn").addEventListener("click", stopCamera);
    document.getElementById("analyzeCameraBtn").addEventListener("click", analyzeCameraEmotion);
    document.getElementById("startVoiceBtn").addEventListener("click", startVoiceCheck);
    document.getElementById("stopVoiceBtn").addEventListener("click", stopVoiceCheck);
    document.getElementById("saveVoiceBtn").addEventListener("click", saveVoiceCheck);

    document.querySelectorAll("[data-scroll-target]").forEach((button) => {
        button.addEventListener("click", () => {
            document.getElementById(button.dataset.scrollTarget)?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    });
}

async function init() {
    attachEvents();
    try {
        await bootstrap();
    } catch (error) {
        console.error(error);
        document.getElementById("chatLog").innerHTML = `
            <article class="message system">
                <span class="message-meta">System</span>
                <div>Backend connection failed. Start the FastAPI server with <code>uvicorn backend.app.main:app --reload</code>.</div>
            </article>
        `;
    }
}

init();
