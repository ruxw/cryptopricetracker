import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
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
                is_verified INTEGER DEFAULT 0
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
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)

async def register_private_start(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    """Register or update a user when they start the bot in a private chat."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, private_started_at, last_interaction_at, is_verified)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_interaction_at = excluded.last_interaction_at,
                is_verified = 1
        """, (user_id, username, first_name, now, now))
        await db.commit()
    logger.info("User %d successfully registered and verified via private start", user_id)

async def is_user_verified(user_id: int) -> bool:
    """
    Check if a user has started the bot privately.
    Queries persistent SQLite DB directly on every check (no in-memory cache).
    """
    if not user_id:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_verified FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == 1:
                return True
            return False

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
            if row:
                return dict(row)
            return None

async def get_verified_users_count() -> int:
    """Return count of verified users."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_verified = 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
