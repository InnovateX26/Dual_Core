"""
Query Logger — SQLite-based logging for all agricultural assistant queries.
Tracks queries, languages, response times, and provides analytics.
"""

import sqlite3
import os
import time
from datetime import datetime
from typing import Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "query_logs.db")


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_logger():
    """Create the logs table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                detected_language TEXT,
                language_confidence REAL,
                context_ids TEXT,
                response TEXT,
                response_time_ms INTEGER,
                model_used TEXT DEFAULT 'claude',
                error TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON query_logs(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_language ON query_logs(detected_language)
        """)
        conn.commit()
    finally:
        conn.close()


def log_query(
    user_message: str,
    detected_language: str,
    language_confidence: float,
    context_ids: list[str],
    response: str,
    response_time_ms: int,
    model_used: str = "claude",
    error: Optional[str] = None,
):
    """Log a query and its response."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO query_logs
                (timestamp, user_message, detected_language, language_confidence,
                 context_ids, response, response_time_ms, model_used, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                user_message,
                detected_language,
                language_confidence,
                ",".join(context_ids) if context_ids else "",
                response,
                response_time_ms,
                model_used,
                error,
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"[QueryLogger] Error logging query: {e}")
    finally:
        conn.close()


def get_stats() -> dict:
    """Get aggregated query statistics."""
    conn = _get_connection()
    try:
        # Total queries
        total = conn.execute("SELECT COUNT(*) as count FROM query_logs").fetchone()["count"]

        # Queries by language
        lang_rows = conn.execute(
            "SELECT detected_language, COUNT(*) as count FROM query_logs "
            "GROUP BY detected_language ORDER BY count DESC"
        ).fetchall()

        language_breakdown = {row["detected_language"]: row["count"] for row in lang_rows}

        # Average response time
        avg_time = conn.execute(
            "SELECT AVG(response_time_ms) as avg_ms FROM query_logs WHERE error IS NULL"
        ).fetchone()["avg_ms"]

        # Recent queries (last 10)
        recent = conn.execute(
            "SELECT timestamp, user_message, detected_language, response_time_ms "
            "FROM query_logs ORDER BY id DESC LIMIT 10"
        ).fetchall()

        recent_queries = [
            {
                "timestamp": row["timestamp"],
                "message": row["user_message"][:100],
                "language": row["detected_language"],
                "response_time_ms": row["response_time_ms"],
            }
            for row in recent
        ]

        # Error count
        errors = conn.execute(
            "SELECT COUNT(*) as count FROM query_logs WHERE error IS NOT NULL"
        ).fetchone()["count"]

        return {
            "total_queries": total,
            "language_breakdown": language_breakdown,
            "avg_response_time_ms": round(avg_time, 0) if avg_time else 0,
            "recent_queries": recent_queries,
            "error_count": errors,
        }
    finally:
        conn.close()
