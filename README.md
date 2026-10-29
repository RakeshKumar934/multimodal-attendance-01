# Multimodal Attendance & Engagement Agent

A beginner-friendly classroom attendance and student engagement monitoring web application built with **Python**, **Flask**, **OpenCV**, and vanilla JavaScript.

---

## Features

| Feature | Description |
|---|---|
| 📊 Dashboard | Live stats, engagement chart, AI teaching suggestions |
| 👥 Students | Add, view, delete student records |
| 📅 Attendance | Start sessions, webcam face detection, manual marking |
| 📈 Reports | History by date, attendance rate, export CSV |
| 🎥 Webcam | Local browser-based face detection (no cloud) |
| 🎙️ Microphone | Optional audio activity detection |
| 💡 Suggestions | Rule-based teaching tips based on engagement trends |

---

## Tech Stack

- **Backend**: Python 3.9+, Flask 2.3+
- **Database**: SQLite (auto-created)
- **Computer Vision**: OpenCV, MediaPipe (optional; browser does detection)
- **Frontend**: Bootstrap 5, Chart.js, Vanilla JS
- **Face Detection**: Browser `FaceDetector` API (Chrome/Edge) with pixel-diff fallback

---

## Project Structure

```
multimedia attendance -887/
├── app.py              # Main Flask application
├── database.py         # SQLite helpers
├── requirements.txt    # Python dependencies
├── README.md
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── students.html
│   ├── attendance.html
│   ├── reports.html
│   └── session_detail.html
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── js/camera.js
└── data/               # SQLite DB stored here (auto-created)
```

---

## Installation

### Prerequisites
- Python 3.9 or higher
- pip

### Step 1 — Create a virtual environment (recommended)

```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `mediapipe` and `opencv-python` are listed for potential server-side use. The app currently uses the browser's built-in `FaceDetector` API for webcam processing, so these are optional for the base prototype. If installation of mediapipe fails, remove it from requirements.txt — the app will still work fully.

### Step 3 — Run the application

```bash
python app.py
```

The application starts on **http://127.0.0.1:5000**

---

## Quick Start Workflow

1. **Open** `http://127.0.0.1:5000` in Chrome or Edge (for best webcam/FaceDetector support).
2. Go to **Students** → add a few students with ID and name.
3. Go to **Attendance** → enter a session title → click **Start Session**.
4. Click **Start Camera** → allow camera/microphone access when prompted.
5. Mark students as present/absent using the ✅ / ❌ buttons.
6. Watch the **Dashboard** for live engagement score and suggestions.
7. Click **End Session** when done.
8. Go to **Reports** → view history → click **Export CSV**.

---

## Privacy & Ethical Notes

- ✅ All webcam frames are processed **locally in your browser** — no video is sent to the server.
- ✅ Only numeric scores (0–100) are transmitted to save engagement snapshots.
- ✅ No raw audio is stored — only an activity level percentage.
- ⚠️ The engagement score is an **experimental estimate** based on face visibility, head movement, and audio activity. It does **not** accurately measure attention, understanding, or emotions.
- ⚠️ Do **not** use this score for disciplinary decisions.

---

## Browser Compatibility

| Browser | Face Detection | Audio |
|---|---|---|
| Chrome 79+ | ✅ Native FaceDetector API | ✅ |
| Edge 79+ | ✅ Native FaceDetector API | ✅ |
| Firefox | ⚠️ Pixel-diff fallback | ✅ |
| Safari | ⚠️ Pixel-diff fallback | ✅ |

> **Tip:** Enable the `FaceDetector` API in Chrome: go to `chrome://flags` → search "experimental web platform features" → Enable.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: mediapipe` | Remove `mediapipe` from requirements.txt and re-run pip install |
| Camera not starting | Check browser permissions; use HTTPS or localhost |
| Port 5000 busy | Change port in app.py: `app.run(port=5001)` |
| DB errors | Delete `data/attendance.db` and restart the app |
