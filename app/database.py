from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    full_name TEXT,
    consent_given INTEGER NOT NULL DEFAULT 0,
    consent_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    confidence REAL NOT NULL,
    classifier_type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS enrollment_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    child_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    experience TEXT NOT NULL,
    trial_time TEXT,
    status TEXT NOT NULL DEFAULT 'sent',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS absence_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    absence_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def database_path() -> Path:
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(database_path())
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
        ensure_column(connection, "users", "consent_given", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "users", "consent_at", "TEXT")


def ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def upsert_user(user: Any) -> int:
    telegram_id = int(getattr(user, "id"))
    username = getattr(user, "username", None)
    full_name = getattr(user, "full_name", None)
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (telegram_id, username, full_name),
        )
        row = connection.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
    return int(row[0])


def save_message(user: Any, text: str) -> int:
    user_id = upsert_user(user)
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO messages (user_id, text) VALUES (?, ?)",
            (user_id, text),
        )
        return int(cursor.lastrowid)


def save_classification(message_id: int, label: str, confidence: float) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO classifications (message_id, label, confidence, classifier_type)
            VALUES (?, ?, ?, ?)
            """,
            (message_id, label, float(confidence), settings.classifier_type),
        )


def save_enrollment_request(data: dict[str, Any], user: Any) -> None:
    user_id = upsert_user(user)
    group = data.get("group") or {}
    trial_time = group.get("time")
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO enrollment_requests
                (user_id, child_name, age, experience, trial_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                str(data.get("child_name") or ""),
                int(data.get("age") or 0),
                str(data.get("experience") or ""),
                trial_time,
            ),
        )


def save_absence_report(absence_text: str, user: Any) -> None:
    user_id = upsert_user(user)
    with connect() as connection:
        connection.execute(
            "INSERT INTO absence_reports (user_id, absence_text) VALUES (?, ?)",
            (user_id, absence_text),
        )


def has_user_consent(user: Any) -> bool:
    user_id = upsert_user(user)
    with connect() as connection:
        row = connection.execute(
            "SELECT consent_given FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return bool(row and row[0])


def save_user_consent(user: Any) -> None:
    user_id = upsert_user(user)
    with connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET consent_given = 1,
                consent_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,),
        )
