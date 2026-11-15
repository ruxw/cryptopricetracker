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
        # Ensure user_lookups has clean schema with created_at
        try:
            async with db.execute("PRAGMA table_info(user_lookups)") as cur:
                cols = [row[1] for row in await cur.fetchall()]
                if cols and "created_at" not in cols:
                    await db.execute("DROP TABLE user_lookups")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_lookups
                ON user_lookups(user_id, symbol)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_lookups
                ON group_lookups(chat_id, symbol)
        """)
        # Seed singleton sponsored row
        await db.execute("INSERT OR IGNORE INTO sponsored_settings (id) VALUES (1)")

        # Currency subscriptions table for daily price updates in DM
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (user_id, symbol)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user
                ON subscriptions(user_id)
        """)

        # Daily DM delivery tracking (to guarantee users receive daily quotes/memes once per day)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_deliveries (
                user_id INTEGER NOT NULL,
                delivery_date TEXT NOT NULL,
                delivery_type TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (user_id, delivery_date, delivery_type)
            )
        """)

        # Cached Telegram photo file_ids for instant visual cards in inline query mode
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_cards (
                card_key TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Migration: ensure is_active column exists on users
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        except Exception:
            pass

        # Migration: ensure price column exists on lookups if table was created in an older schema
        try:
            await db.execute("ALTER TABLE user_lookups ADD COLUMN price REAL DEFAULT 0.0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE group_lookups ADD COLUMN price REAL DEFAULT 0.0")
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

# ==========================================
# Crypto Lookup History & Analytics
# ==========================================

async def record_coin_lookup(user_id: int, symbol: str, price: float, chat_id: Optional[int] = None) -> None:
    """Record a crypto price lookup for personal history and chat vibes."""
    now = time.time()
    sym = symbol.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_lookups (user_id, symbol, price, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, sym, price, now))
        if chat_id is not None and chat_id < 0:
            await db.execute("""
                INSERT INTO group_lookups (chat_id, user_id, symbol, price, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, user_id, sym, price, now))
        await db.commit()

async def get_user_first_seen(user_id: int, symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve the very first time a user checked a specific coin."""
    sym = symbol.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT price, created_at FROM user_lookups
            WHERE user_id = ? AND symbol = ?
            ORDER BY id ASC LIMIT 1
        """, (user_id, sym)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_user_last_lookup(user_id: int, symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve the previous price lookup for a user (excluding the very latest one if possible)."""
    sym = symbol.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT price, created_at FROM user_lookups
            WHERE user_id = ? AND symbol = ?
            ORDER BY id DESC LIMIT 2
        """, (user_id, sym)) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return None
            if len(rows) > 1:
                return dict(rows[1])
            return dict(rows[0])

async def get_user_profile_stats(user_id: int) -> Dict[str, Any]:
    """Retrieve comprehensive usage recap and intelligence profile for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # User account info
        user_info = None
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                user_info = dict(row)

        # Total lookup count
        total_lookups = 0
        async with db.execute("SELECT COUNT(*) FROM user_lookups WHERE user_id = ?", (user_id,)) as cursor:
            r = await cursor.fetchone()
            total_lookups = r[0] if r else 0

        # Favorite coin
        fav_coin = "BTC"
        fav_count = 0
        async with db.execute("""
            SELECT symbol, COUNT(*) as c FROM user_lookups
            WHERE user_id = ?
            GROUP BY symbol ORDER BY c DESC LIMIT 1
        """, (user_id,)) as cursor:
            r = await cursor.fetchone()
            if r:
                fav_coin = r["symbol"]
                fav_count = r["c"]

        return {
            "user_id": user_id,
            "username": user_info.get("username") if user_info else None,
            "first_name": user_info.get("first_name") if user_info else "Trader",
            "joined_at": user_info.get("private_started_at") if user_info else None,
            "total_lookups": total_lookups,
            "favorite_coin": fav_coin,
            "favorite_count": fav_count
        }

async def get_chat_top_coins(chat_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve top checked coins inside a Telegram group."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT symbol, COUNT(*) as count FROM group_lookups
            WHERE chat_id = ?
            GROUP BY symbol ORDER BY count DESC LIMIT ?
        """, (chat_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# ─── SUBSCRIPTIONS & DAILY DELIVERY HELPERS ───────────────────────────────────

async def add_subscription(user_id: int, symbol: str) -> bool:
    """Add a daily currency rate subscription for a user in DM."""
    now = time.time()
    sym = symbol.upper().strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO subscriptions (user_id, symbol, created_at)
            VALUES (?, ?, ?)
        """, (user_id, sym, now))
        await db.commit()
    logger.info("User %d subscribed to %s daily updates", user_id, sym)
    return True

async def remove_subscription(user_id: int, symbol: str) -> bool:
    """Remove a daily currency rate subscription."""
    sym = symbol.upper().strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM subscriptions WHERE user_id = ? AND symbol = ?
        """, (user_id, sym))
        await db.commit()
    logger.info("User %d unsubscribed from %s daily updates", user_id, sym)
    return True

async def is_subscribed(user_id: int, symbol: str) -> bool:
    """Check if user is subscribed to a coin's daily rates."""
    sym = symbol.upper().strip()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT 1 FROM subscriptions WHERE user_id = ? AND symbol = ?
        """, (user_id, sym)) as cursor:
            return bool(await cursor.fetchone())

async def toggle_subscription(user_id: int, symbol: str) -> bool:
    """Toggle subscription: returns True if now subscribed, False if unsubscribed."""
    sym = symbol.upper().strip()
    if await is_subscribed(user_id, sym):
        await remove_subscription(user_id, sym)
        return False
    else:
        await add_subscription(user_id, sym)
        return True

async def get_user_subscriptions(user_id: int) -> List[str]:
    """Retrieve all currency symbols a user is subscribed to."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT symbol FROM subscriptions WHERE user_id = ? ORDER BY symbol ASC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_all_subscriptions_by_user() -> Dict[int, List[str]]:
    """Retrieve all subscriptions grouped by active user ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT s.user_id, s.symbol FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE u.is_active = 1
            ORDER BY s.user_id, s.symbol
        """) as cursor:
            rows = await cursor.fetchall()
            result: Dict[int, List[str]] = {}
            for uid, sym in rows:
                result.setdefault(uid, []).append(sym)
            return result

async def get_eligible_daily_users(delivery_date: str, delivery_type: str = "daily") -> List[int]:
    """Retrieve all verified active users who have not yet received today's daily DM."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT u.user_id FROM users u
            WHERE u.is_verified = 1 AND u.is_active = 1
            AND u.user_id NOT IN (
                SELECT user_id FROM daily_deliveries
                WHERE delivery_date = ? AND delivery_type = ?
            )
        """, (delivery_date, delivery_type)) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def record_daily_delivery(user_id: int, delivery_date: str, delivery_type: str = "daily") -> None:
    """Record that a user received their daily DM for today."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO daily_deliveries (user_id, delivery_date, delivery_type, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, delivery_date, delivery_type, now))
        await db.commit()

async def get_cached_card_file_id(card_key: str) -> Optional[str]:
    """Get Telegram photo file_id for a card key (e.g. 'btc', 'top_overview')."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT file_id FROM cached_cards WHERE card_key = ?
        """, (card_key.lower(),)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_cached_card_file_id(card_key: str, file_id: str) -> None:
    """Save or update Telegram photo file_id for a card key."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO cached_cards (card_key, file_id, updated_at)
            VALUES (?, ?, ?)
        """, (card_key.lower(), file_id, now))
        await db.commit()
