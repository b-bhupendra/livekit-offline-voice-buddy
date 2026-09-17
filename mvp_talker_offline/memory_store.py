"""Local Persistent Memory and RAG Store for English Conversational Buddy.
Uses SQLite for zero-dependency, ultra-low-latency local storage.
Tracks:
- Conversation sessions and topic milestones
- Dialogue turns and context
- Grammar feedback, recasting, and practice progress
- User profile and learning goals
"""

import os
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "memory.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            topic TEXT,
            grammar_focus TEXT,
            summary TEXT,
            last_utterance TEXT
        )
        """)

        # Dialogue turns table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """)

        # Grammar feedback & mistake tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS grammar_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_said TEXT NOT NULL,
            corrected_recast TEXT NOT NULL,
            grammar_point TEXT
        )
        """)

        # User profile & preferences
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        # Default profile entries
        cursor.execute("""
        INSERT OR IGNORE INTO profile (key, value, updated_at)
        VALUES 
            ('user_name', 'Bhupendra', datetime('now')),
            ('target_language', 'English', datetime('now')),
            ('proficiency_goal', 'Fluent, natural conversational speaking and accurate tenses', datetime('now')),
            ('preferred_topics', 'Technology, travel, daily routines, career, philosophy', datetime('now'))
        """)

        conn.commit()


# Initialize on import
init_db()


def start_session(session_id: str, topic: str = "General English Conversation", grammar_focus: str = "Natural Phrasing & Tenses"):
    """Records the start of a new conversational session."""
    now = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO sessions (session_id, started_at, topic, grammar_focus, summary)
        VALUES (?, ?, ?, ?, ?)
        """, (session_id, now, topic, grammar_focus, f"Session started practicing {topic} focusing on {grammar_focus}."))
        conn.commit()


def record_turn(session_id: str, role: str, content: str):
    """Records a single conversational turn (user or assistant)."""
    if not content or not content.strip():
        return
    now = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO turns (session_id, timestamp, role, content)
        VALUES (?, ?, ?, ?)
        """, (session_id, now, role, content.strip()))
        
        # Update last utterance on session
        cursor.execute("""
        UPDATE sessions SET last_utterance = ?, ended_at = ?
        WHERE session_id = ?
        """, (content.strip()[:200], now, session_id))
        conn.commit()


def log_grammar_recast(session_id: str, user_said: str, corrected_recast: str, grammar_point: str = "General Grammar"):
    """Records a grammar correction or recast point for progress tracking."""
    now = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO grammar_logs (session_id, timestamp, user_said, corrected_recast, grammar_point)
        VALUES (?, ?, ?, ?, ?)
        """, (session_id, now, user_said.strip(), corrected_recast.strip(), grammar_point.strip()))
        conn.commit()


def update_session_summary(session_id: str, topic: str, grammar_focus: str, summary: str):
    """Updates session recap and next step recommendations."""
    now = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE sessions 
        SET topic = ?, grammar_focus = ?, summary = ?, ended_at = ?
        WHERE session_id = ?
        """, (topic, grammar_focus, summary, now, session_id))
        conn.commit()


def get_last_session() -> Optional[Dict[str, Any]]:
    """Fetches the most recently completed or previous session info."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT session_id, started_at, ended_at, topic, grammar_focus, summary, last_utterance
        FROM sessions
        ORDER BY started_at DESC
        LIMIT 2
        """)
        rows = cursor.fetchall()
        if not rows:
            return None
        # Return the latest one that has a summary or topic
        for row in rows:
            return dict(row)
        return dict(rows[0])


def search_conversation_history(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """RAG search across past dialogue turns and summaries."""
    tokens = [t.strip().lower() for t in query.split() if len(t.strip()) > 3]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if not tokens:
            cursor.execute("""
            SELECT session_id, timestamp, role, content 
            FROM turns 
            ORDER BY id DESC 
            LIMIT ?
            """, (limit,))
        else:
            like_clause = " OR ".join(["content LIKE ?" for _ in tokens])
            params = [f"%{token}%" for token in tokens] + [limit]
            cursor.execute(f"""
            SELECT session_id, timestamp, role, content 
            FROM turns 
            WHERE {like_clause}
            ORDER BY id DESC 
            LIMIT ?
            """, params)
        return [dict(row) for row in cursor.fetchall()]


def get_learning_progress() -> Dict[str, Any]:
    """Summarizes past grammar points practiced and total sessions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM sessions")
        total_sessions = cursor.fetchone()["count"]

        cursor.execute("""
        SELECT grammar_point, COUNT(*) as occurrences
        FROM grammar_logs
        GROUP BY grammar_point
        ORDER BY occurrences DESC
        LIMIT 5
        """)
        grammar_points = [dict(row) for row in cursor.fetchall()]

        cursor.execute("""
        SELECT topic, summary, started_at
        FROM sessions
        WHERE summary IS NOT NULL
        ORDER BY started_at DESC
        LIMIT 3
        """)
        recent_topics = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT key, value FROM profile")
        profile = {row["key"]: row["value"] for row in cursor.fetchall()}

        return {
            "total_sessions": total_sessions,
            "grammar_focus_areas": grammar_points,
            "recent_topics": recent_topics,
            "user_profile": profile,
        }
