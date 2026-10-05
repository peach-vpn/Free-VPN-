import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from config import DATABASE_FILE, TOTAL_BYTES, EXPIRE_DAYS


def db():
    return sqlite3.connect(DATABASE_FILE)


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            token TEXT UNIQUE NOT NULL,
            used_bytes INTEGER DEFAULT 0,
            total_bytes INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_user(telegram_id):
    conn = db()

    row = conn.execute("""
        SELECT id, telegram_id, username, token,
               used_bytes, total_bytes,
               expires_at, active, created_at
        FROM users
        WHERE telegram_id = ?
    """, (telegram_id,)).fetchone()

    conn.close()
    return row


def get_user_by_token(token):
    conn = db()

    row = conn.execute("""
        SELECT id, telegram_id, username, token,
               used_bytes, total_bytes,
               expires_at, active, created_at
        FROM users
        WHERE token = ?
    """, (token,)).fetchone()

    conn.close()
    return row


def create_user(telegram_id, username):
    existing = get_user(telegram_id)

    if existing:
        return existing

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=EXPIRE_DAYS)
    token = secrets.token_urlsafe(32)

    conn = db()

    conn.execute("""
        INSERT INTO users (
            telegram_id,
            username,
            token,
            used_bytes,
            total_bytes,
            expires_at,
            active,
            created_at
        )
        VALUES (?, ?, ?, 0, ?, ?, 1, ?)
    """, (
        telegram_id,
        username,
        token,
        TOTAL_BYTES,
        expires.isoformat(),
        now.isoformat()
    ))

    conn.commit()
    conn.close()

    return get_user(telegram_id)


def update_username(telegram_id, username):
    conn = db()

    conn.execute("""
        UPDATE users
        SET username = ?
        WHERE telegram_id = ?
    """, (username, telegram_id))

    conn.commit()
    conn.close()


def set_used_bytes(token, used_bytes):
    conn = db()

    conn.execute("""
        UPDATE users
        SET used_bytes = ?
        WHERE token = ?
    """, (max(0, int(used_bytes)), token))

    conn.commit()
    conn.close()


def disable_user(token):
    conn = db()

    conn.execute("""
        UPDATE users
        SET active = 0
        WHERE token = ?
    """, (token,))

    conn.commit()
    conn.close()


def enable_user(token):
    conn = db()

    conn.execute("""
        UPDATE users
        SET active = 1
        WHERE token = ?
    """, (token,))

    conn.commit()
    conn.close()


def format_bytes(value):
    value = float(value)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} PB"
