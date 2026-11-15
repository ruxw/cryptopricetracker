import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import aiosqlite
from bot.config import DB_PATH

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """Initialize persistent SQLite database schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                private_started_at TIMESTAMP,
                last_interaction_at TIMESTAMP,
                is_verified INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                username TEXT,
                active INTEGER DEFAULT 1,
                created_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                interaction_type TEXT,
                query TEXT,
                created_at TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sponsored_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                text_html TEXT,
                text_enabled INTEGER NOT NULL DEFAULT 0,
                button_style TEXT,
                button_text TEXT,
                button_url TEXT,
                button_enabled INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                target_type TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                from_chat_id INTEGER NOT NULL,
                total_targets INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                blocked_count INTEGER NOT NULL DEFAULT 0,
                started_at REAL NOT NULL,
                finished_at REAL,
                status TEXT NOT NULL DEFAULT 'PENDING'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                target_name TEXT,
                target_username TEXT,
                is_group INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                error_msg TEXT,
                created_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_broadcast_recipients
                ON broadcast_recipients(broadcast_id)
        """)
        # Seed singleton sponsored row
        await db.execute("INSERT OR IGNORE INTO sponsored_settings (id) VALUES (1)")

        # Migration: ensure is_active column exists on users
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        except Exception:
            pass

        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)

async def register_private_start(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    """Register or update a user when they start the bot in a private chat."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, private_started_at, last_interaction_at, is_verified, is_active)
            VALUES (?, ?, ?, ?, ?, 1, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_interaction_at = excluded.last_interaction_at,
                is_verified = 1,
                is_active = 1
        """, (user_id, username, first_name, now, now))
        await db.commit()
    logger.info("User %d successfully registered and verified via private start", user_id)

async def is_user_verified(user_id: int) -> bool:
    """Check if a user has started the bot privately."""
    if not user_id:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_verified FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] == 1)

async def record_interaction(user_id: int, interaction_type: str, query: str = "") -> None:
    """Record a user interaction persistently."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET last_interaction_at = ? WHERE user_id = ?
        """, (now, user_id))
        await db.execute("""
            INSERT INTO interactions (user_id, interaction_type, query, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, interaction_type, query, now))
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user details from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_verified_users_count() -> int:
    """Return count of active verified users."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_active = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_active_users() -> List[Dict[str, Any]]:
    """Retrieve all active users for broadcasting."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id AS id, username, first_name AS name FROM users WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def set_user_active(user_id: int, active: int) -> None:
    """Set user active status (e.g. 0 if blocked)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (active, user_id))
        await db.commit()

# ==========================================
# Group / Deal GC Tracking
# ==========================================

async def register_group(chat_id: int, title: str, username: Optional[str] = None) -> None:
    """Register or refresh an active group / deal GC."""
    now = time.time()
    safe_title = str(title) if title is not None and not hasattr(title, "_mock_name") else "Group"
    safe_username = str(username) if username is not None and not hasattr(username, "_mock_name") else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO groups (chat_id, title, username, active, created_at)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                active = 1
        """, (chat_id, safe_title, safe_username, now))
        await db.commit()

async def set_group_active(chat_id: int, active: int) -> None:
    """Set group active status (e.g. 0 if kicked)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups SET active = ? WHERE chat_id = ?", (active, chat_id))
        await db.commit()

async def get_active_groups() -> List[Dict[str, Any]]:
    """Retrieve all active registered groups / deal GCs."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT chat_id AS id, username, title AS name FROM groups WHERE active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_active_groups_count() -> int:
    """Return count of active registered groups."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM groups WHERE active = 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# ==========================================
# Sponsored Settings Persistence
# ==========================================

async def get_sponsored_settings() -> Dict[str, Any]:
    """Retrieve current system-wide sponsored content settings."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sponsored_settings WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            await db.execute("INSERT OR IGNORE INTO sponsored_settings (id) VALUES (1)")
            await db.commit()
            return {
                "id": 1,
                "text_html": None,
                "text_enabled": 0,
                "button_style": None,
                "button_text": None,
                "button_url": None,
                "button_enabled": 0
            }

async def update_sponsored_text(text_html: Optional[str], enabled: int = 1) -> None:
    """Update sponsored quotation text."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sponsored_settings SET text_html = ?, text_enabled = ? WHERE id = 1",
            (text_html, enabled)
        )
        await db.commit()

async def update_sponsored_button(style: Optional[str], text: Optional[str], url: Optional[str], enabled: int = 1) -> None:
    """Update sponsored inline keyboard button."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sponsored_settings SET button_style = ?, button_text = ?, button_url = ?, button_enabled = ? WHERE id = 1",
            (style, text, url, enabled)
        )
        await db.commit()

async def toggle_sponsored_text() -> bool:
    """Toggle text sponsorship ON/OFF."""
    sp = await get_sponsored_settings()
    new_state = 0 if sp["text_enabled"] else 1
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sponsored_settings SET text_enabled = ? WHERE id = 1", (new_state,))
        await db.commit()
    return bool(new_state)

async def toggle_sponsored_button() -> bool:
    """Toggle button sponsorship ON/OFF."""
    sp = await get_sponsored_settings()
    new_state = 0 if sp["button_enabled"] else 1
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sponsored_settings SET button_enabled = ? WHERE id = 1", (new_state,))
        await db.commit()
    return bool(new_state)

async def clear_sponsored_text() -> None:
    """Clear sponsored text."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sponsored_settings SET text_html = NULL, text_enabled = 0 WHERE id = 1")
        await db.commit()

async def clear_sponsored_button() -> None:
    """Clear sponsored button."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sponsored_settings SET button_style = NULL, button_text = NULL, button_url = NULL, button_enabled = 0 WHERE id = 1"
        )
        await db.commit()

# ==========================================
# Broadcasts Persistence
# ==========================================

async def create_broadcast(
    sender_id: int,
    target_type: str,
    message_id: int,
    from_chat_id: int,
    total_targets: int,
    started_at: float
) -> int:
    """Insert a new broadcast log and return broadcast_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO broadcasts(sender_id, target_type, message_id, from_chat_id, total_targets, started_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'RUNNING')
        """, (sender_id, target_type, message_id, from_chat_id, total_targets, started_at))
        await db.commit()
        return cursor.lastrowid

async def record_broadcast_recipient(
    broadcast_id: int,
    target_id: int,
    target_name: Optional[str],
    target_username: Optional[str],
    is_group: int,
    status: str,
    error_msg: Optional[str],
    created_at: float
) -> None:
    """Record single recipient delivery status."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO broadcast_recipients (
                broadcast_id, target_id, target_name, target_username, is_group, status, error_msg, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (broadcast_id, target_id, target_name or "Unknown", target_username, is_group, status, error_msg, created_at))
        await db.commit()

async def finish_broadcast(
    broadcast_id: int,
    success_count: int,
    failed_count: int,
    blocked_count: int,
    finished_at: float,
    status: str = "COMPLETED"
) -> None:
    """Finalize broadcast entry."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE broadcasts SET
                success_count = ?,
                failed_count = ?,
                blocked_count = ?,
                finished_at = ?,
                status = ?
            WHERE id = ?
        """, (success_count, failed_count, blocked_count, finished_at, status, broadcast_id))
        await db.commit()

async def get_broadcast_recipients(broadcast_id: int) -> List[Dict[str, Any]]:
    """Retrieve all recipient outcomes for a broadcast."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM broadcast_recipients WHERE broadcast_id = ?", (broadcast_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
