"""
app.py - Main Flask application
"""

import io
import csv
import json
import base64
import threading
import time
import numpy as np
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, flash, Response)

import database as db

app = Flask(__name__)
app.secret_key = "attendance_secret_key_2024"

# ──────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────
db.init_db()

# ──────────────────────────────────────────────
# In-memory session state (not persisted)
# ──────────────────────────────────────────────
session_state = {
    "session_id": None,
    "engagement_scores": [],   # rolling list of recent scores
    "last_score": 0,
    "face_visible": False,
    "lock": threading.Lock(),
}


# ──────────────────────────────────────────────
# Teaching suggestion engine (rule-based)
# ──────────────────────────────────────────────
def generate_suggestions(scores: list) -> list:
    suggestions = []
    if not scores:
        return [{"type": "info", "icon": "💡",
                 "text": "Start a session to receive teaching suggestions."}]

    avg = sum(scores[-10:]) / len(scores[-10:]) if scores else 50
    recent = scores[-3:] if len(scores) >= 3 else scores
    trend = (recent[-1] - recent[0]) if len(recent) > 1 else 0

    if avg < 40:
        suggestions.append({
            "type": "warning", "icon": "🎯",
            "text": "Engagement estimate is low. Consider a short interactive activity or group discussion.",
            "reason": f"Average engagement score is {avg:.0f}/100."
        })
    if trend < -10:
        suggestions.append({
            "type": "danger", "icon": "📉",
            "text": "Engagement appears to be dropping. Try asking a question or conducting a quick quiz.",
            "reason": "Engagement score has declined recently."
        })
    if avg > 70:
        suggestions.append({
            "type": "success", "icon": "🌟",
            "text": "Great engagement! This is a good time to introduce a challenging new concept.",
            "reason": f"Average engagement score is {avg:.0f}/100."
        })
    if 40 <= avg <= 60:
        suggestions.append({
            "type": "info", "icon": "🎙️",
            "text": "Moderate engagement detected. Consider inviting students to share their thoughts.",
            "reason": "Engagement is at a moderate level."
        })
    if len(scores) > 15 and all(s < 30 for s in scores[-5:]):
        suggestions.append({
            "type": "danger", "icon": "⏰",
            "text": "Extended period of very low activity detected. A short break might help.",
            "reason": "Consistently low scores over the last several readings."
        })

    if not suggestions:
        suggestions.append({
            "type": "info", "icon": "✅",
            "text": "Session is progressing normally. Keep monitoring engagement.",
            "reason": ""
        })
    return suggestions


# ──────────────────────────────────────────────
# Routes — Dashboard
# ──────────────────────────────────────────────
@app.route("/")
def dashboard():
    stats = db.get_dashboard_stats()
    recent = db.get_recent_attendance(10)
    active = stats["active_session"]
    engagement_data = []
    avg_engagement = 0
    suggestions = []

    if active:
        snaps = db.get_engagement_for_session(active["id"])
        engagement_data = [
            {"time": s["recorded_at"][-8:], "score": s["score"]}
            for s in snaps[-30:]
        ]
        avg_engagement = db.get_avg_engagement(active["id"])
        with session_state["lock"]:
            scores_copy = list(session_state["engagement_scores"])
        suggestions = generate_suggestions(scores_copy)
    else:
        suggestions = generate_suggestions([])

    return render_template("dashboard.html",
                           stats=stats,
                           recent=recent,
                           engagement_data=json.dumps(engagement_data),
                           avg_engagement=avg_engagement,
                           suggestions=suggestions,
                           active_session=active)


# ──────────────────────────────────────────────
# Routes — Students
# ──────────────────────────────────────────────
@app.route("/students")
def students():
    all_students = db.get_all_students()
    return render_template("students.html", students=all_students)


@app.route("/students/add", methods=["POST"])
def add_student():
    student_id = request.form.get("student_id", "").strip()
    name = request.form.get("name", "").strip()
    if not student_id or not name:
        flash("Both Student ID and Name are required.", "danger")
        return redirect(url_for("students"))
    ok, msg = db.add_student(student_id, name)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("students"))


@app.route("/students/delete/<int:sid>", methods=["POST"])
def delete_student(sid):
    db.delete_student(sid)
    flash("Student removed.", "warning")
    return redirect(url_for("students"))


# ──────────────────────────────────────────────
# Routes — Attendance
# ──────────────────────────────────────────────
@app.route("/attendance")
def attendance():
    active = db.get_active_session()
    all_students = db.get_all_students()
    present = []
    absent = []
    session_id = None

    if active:
        session_id = active["id"]
        present = db.get_attendance_for_session(session_id)
        absent = db.get_absent_students(session_id)

    return render_template("attendance.html",
                           active_session=active,
                           all_students=all_students,
                           present=present,
                           absent=absent,
                           session_id=session_id)


@app.route("/attendance/start", methods=["POST"])
def start_session():
    title = request.form.get("title", "").strip() or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    sid = db.create_session(title)
    with session_state["lock"]:
        session_state["session_id"] = sid
        session_state["engagement_scores"] = []
        session_state["last_score"] = 0
    flash(f"Session '{title}' started!", "success")
    return redirect(url_for("attendance"))


@app.route("/attendance/stop", methods=["POST"])
def stop_session():
    active = db.get_active_session()
    if active:
        db.end_session(active["id"])
        with session_state["lock"]:
            session_state["session_id"] = None
        flash("Session ended.", "info")
    return redirect(url_for("attendance"))


@app.route("/attendance/mark", methods=["POST"])
def mark_attendance():
    session_id = request.form.get("session_id", type=int)
    student_db_id = request.form.get("student_db_id", type=int)
    status = request.form.get("status", "present")
    if not session_id or not student_db_id:
        flash("Invalid request.", "danger")
        return redirect(url_for("attendance"))
    ok, msg = db.mark_attendance(session_id, student_db_id, status)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("attendance"))


@app.route("/attendance/mark_all_absent", methods=["POST"])
def mark_all_absent():
    session_id = request.form.get("session_id", type=int)
    if not session_id:
        flash("No active session.", "danger")
        return redirect(url_for("attendance"))
    absent_students = db.get_absent_students(session_id)
    for s in absent_students:
        db.mark_attendance(session_id, s["id"], "absent")
    flash(f"Marked {len(absent_students)} student(s) as absent.", "info")
    return redirect(url_for("attendance"))


# ──────────────────────────────────────────────
# Routes — Reports
# ──────────────────────────────────────────────
@app.route("/reports")
def reports():
    date_filter = request.args.get("date", "")
    history = db.get_attendance_history(date_filter if date_filter else None)
    sessions = db.get_all_sessions()
    total_students = len(db.get_all_students())

    # Build chart data: dates vs present counts
    chart_data = {}
    for h in history:
        d = h["date"]
        if d not in chart_data:
            chart_data[d] = 0
        chart_data[d] += h["present_count"]

    chart_labels = list(chart_data.keys())[-14:]
    chart_values = [chart_data[l] for l in chart_labels]

    return render_template("reports.html",
                           history=history,
                           sessions=sessions,
                           total_students=total_students,
                           chart_labels=json.dumps(chart_labels),
                           chart_values=json.dumps(chart_values),
                           date_filter=date_filter)


@app.route("/reports/export")
def export_csv():
    rows = db.get_full_attendance_export()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "date", "session_title", "student_id", "student_name", "status", "marked_at"
    ])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"}
    )


@app.route("/reports/session/<int:session_id>")
def session_detail(session_id):
    session = db.get_session_by_id(session_id)
    if not session:
        flash("Session not found.", "danger")
        return redirect(url_for("reports"))
    present = db.get_attendance_for_session(session_id)
    absent = db.get_absent_students(session_id)
    snaps = db.get_engagement_for_session(session_id)
    engagement_data = [
        {"time": s["recorded_at"][-8:], "score": s["score"]}
        for s in snaps
    ]
    avg_eng = db.get_avg_engagement(session_id)
    return render_template("session_detail.html",
                           session=session,
                           present=present,
                           absent=absent,
                           engagement_data=json.dumps(engagement_data),
                           avg_engagement=avg_eng)


# ──────────────────────────────────────────────
# API — Engagement snapshot (called from JS)
# ──────────────────────────────────────────────
@app.route("/api/engagement", methods=["POST"])
def api_engagement():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not session_id:
        active = db.get_active_session()
        if active:
            session_id = active["id"]

    if not session_id:
        return jsonify({"ok": False, "msg": "No active session"}), 400

    face_visible = int(data.get("face_visible", 0))
    head_movement = float(data.get("head_movement", 0))
    audio_activity = float(data.get("audio_activity", 0))

    # Compute a simple engagement score
    score = compute_engagement_score(face_visible, head_movement, audio_activity)

    db.save_engagement_snapshot(session_id, score, face_visible, head_movement, audio_activity)

    with session_state["lock"]:
        session_state["engagement_scores"].append(score)
        session_state["last_score"] = score
        if len(session_state["engagement_scores"]) > 200:
            session_state["engagement_scores"] = session_state["engagement_scores"][-200:]

    return jsonify({"ok": True, "score": score})


def compute_engagement_score(face_visible: int, head_movement: float, audio_activity: float) -> float:
    """
    Simple rule-based engagement score (0–100).
    - face_visible contributes 50 points
    - head_movement (0–1) contributes 30 points (some movement = engaged, too much = distracted)
    - audio_activity (0–1) contributes 20 points
    All inputs are clipped to valid ranges.
    """
    face_score = 50 if face_visible else 0

    # Head movement: bell curve — moderate movement is ideal
    hm = max(0.0, min(1.0, head_movement))
    if hm < 0.05:
        hm_score = 5   # too still
    elif hm < 0.4:
        hm_score = 30  # active
    else:
        hm_score = max(5, 30 - int(hm * 30))  # too much movement

    audio = max(0.0, min(1.0, audio_activity))
    audio_score = audio * 20

    total = face_score + hm_score + audio_score
    return round(min(100, max(0, total)), 1)


@app.route("/api/suggestions")
def api_suggestions():
    with session_state["lock"]:
        scores_copy = list(session_state["engagement_scores"])
    suggestions = generate_suggestions(scores_copy)
    return jsonify(suggestions)


@app.route("/api/status")
def api_status():
    active = db.get_active_session()
    stats = db.get_dashboard_stats()
    with session_state["lock"]:
        last_score = session_state["last_score"]
    return jsonify({
        "active_session": dict(active) if active else None,
        "stats": stats,
        "last_engagement": last_score,
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
