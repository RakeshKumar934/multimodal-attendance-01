"""
database.py - SQLite database setup and helper functions
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "attendance.db")


def get_connection():
    """Return a database connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all required tables if they do not exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    # Students table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Sessions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            date        TEXT NOT NULL,
            started_at  TEXT NOT NULL,
            ended_at    TEXT,
            is_active   INTEGER DEFAULT 1
        )
    """)

    # Attendance table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL,
            student_id      INTEGER NOT NULL,
            status          TEXT DEFAULT 'present',   -- present | absent | manual
            marked_at       TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(session_id, student_id),
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # Engagement snapshots table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS engagement_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL,
            score           REAL NOT NULL,
            face_visible    INTEGER DEFAULT 0,
            head_movement   REAL DEFAULT 0,
            audio_activity  REAL DEFAULT 0,
            recorded_at     TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# Student helpers
# ──────────────────────────────────────────────

def add_student(student_id: str, name: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO students (student_id, name) VALUES (?, ?)",
            (student_id.strip(), name.strip())
        )
        conn.commit()
        return True, "Student added successfully."
    except sqlite3.IntegrityError:
        return False, f"Student ID '{student_id}' already exists."
    finally:
        conn.close()


def get_all_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_student(student_db_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_db_id,))
    conn.commit()
    conn.close()


def get_student_by_id(student_db_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_db_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ──────────────────────────────────────────────
# Session helpers
# ──────────────────────────────────────────────

def create_session(title: str):
    now = datetime.now()
    conn = get_connection()
    # Close any previously open sessions
    conn.execute("UPDATE sessions SET is_active=0, ended_at=? WHERE is_active=1",
                 (now.strftime("%Y-%m-%d %H:%M:%S"),))
    cur = conn.execute(
        "INSERT INTO sessions (title, date, started_at) VALUES (?, ?, ?)",
        (title, now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return session_id


def end_session(session_id: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET is_active=0, ended_at=? WHERE id=?",
        (now, session_id)
    )
    conn.commit()
    conn.close()


def get_active_session():
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE is_active=1 ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_sessions():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_by_id(session_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ──────────────────────────────────────────────
# Attendance helpers
# ──────────────────────────────────────────────

def mark_attendance(session_id: int, student_db_id: int, status: str = "present"):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO attendance (session_id, student_id, status, marked_at)
               VALUES (?, ?, ?, datetime('now','localtime'))""",
            (session_id, student_db_id, status)
        )
        conn.commit()
        return True, "Attendance marked."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_attendance_for_session(session_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.*, s.name, s.student_id as sid
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.session_id = ?
        ORDER BY a.marked_at
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_absent_students(session_id: int):
    """Return students NOT in the attendance table for a given session."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, s.student_id as sid, s.name
        FROM students s
        WHERE s.id NOT IN (
            SELECT student_id FROM attendance WHERE session_id = ?
        )
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_history(date_filter: str = None):
    conn = get_connection()
    if date_filter:
        rows = conn.execute("""
            SELECT se.date, se.title, se.id as session_id,
                   COUNT(a.id) as present_count
            FROM sessions se
            LEFT JOIN attendance a ON se.id = a.session_id AND a.status != 'absent'
            WHERE se.date = ?
            GROUP BY se.id
            ORDER BY se.started_at DESC
        """, (date_filter,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT se.date, se.title, se.id as session_id,
                   COUNT(a.id) as present_count
            FROM sessions se
            LEFT JOIN attendance a ON se.id = a.session_id AND a.status != 'absent'
            GROUP BY se.id
            ORDER BY se.started_at DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_full_attendance_export():
    """All attendance records joined with student and session info."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT se.date, se.title as session_title,
               s.student_id as student_id, s.name as student_name,
               a.status, a.marked_at
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN sessions se ON a.session_id = se.id
        ORDER BY se.date DESC, s.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Engagement helpers
# ──────────────────────────────────────────────

def save_engagement_snapshot(session_id: int, score: float,
                              face_visible: int, head_movement: float,
                              audio_activity: float):
    conn = get_connection()
    conn.execute("""
        INSERT INTO engagement_snapshots
            (session_id, score, face_visible, head_movement, audio_activity)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, score, face_visible, head_movement, audio_activity))
    conn.commit()
    conn.close()


def get_engagement_for_session(session_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT score, face_visible, head_movement, audio_activity, recorded_at
        FROM engagement_snapshots
        WHERE session_id = ?
        ORDER BY recorded_at
    """, (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_avg_engagement(session_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT AVG(score) as avg_score FROM engagement_snapshots WHERE session_id=?",
        (session_id,)
    ).fetchone()
    conn.close()
    val = row["avg_score"] if row and row["avg_score"] is not None else 0
    return round(val, 1)


def get_recent_attendance(limit: int = 10):
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.marked_at, s.name, s.student_id as sid,
               se.title as session_title, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN sessions se ON a.session_id = se.id
        ORDER BY a.marked_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dashboard_stats():
    conn = get_connection()
    total_students = conn.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"]
    active_session = get_active_session()
    present_today = 0
    absent_today = 0
    session_id = None
    if active_session:
        session_id = active_session["id"]
        present_today = conn.execute(
            "SELECT COUNT(*) as c FROM attendance WHERE session_id=? AND status='present'",
            (session_id,)
        ).fetchone()["c"]
        absent_today = total_students - present_today
    conn.close()
    return {
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": max(absent_today, 0),
        "active_session": active_session,
        "session_id": session_id,
    }
