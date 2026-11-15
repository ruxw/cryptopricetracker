import os
import re
from typing import Set, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

def sanitize_bot_username(raw: str) -> str:
    """
    Sanitize the bot username into standard format regardless of how it is entered in .env:
    Supports:
    - @CurrencingBot
    - t.me/currencingbot
    - https://t.me/currencingbot
    - http://t.me/currencingbot
    - CurrencingBot
    """
    if not raw:
        return "CurrencingBot"
    val = raw.strip()
    # Normalize prefixes
    for prefix in ["https://t.me/", "http://t.me/", "t.me/", "@"]:
        if val.lower().startswith(prefix):
            val = val[len(prefix):]
    return val.strip().strip("/")

# Brand Configuration
BRAND_NAME = "Currencing"

def parse_owner_ids(raw: str) -> Set[int]:
    """Parse comma/space/semicolon/quote-separated numeric Telegram owner IDs."""
    if not raw:
        return set()
    cleaned = raw.replace('"', '').replace("'", "")
    return {int(x) for x in re.split(r"[,;\s]+", cleaned.strip()) if x.isdigit()}

def get_owner_ids() -> Set[int]:
    """Dynamically get all configured owner IDs from multiple possible env vars."""
    keys = ["OWNER_ID", "BOT_OWNER_IDS", "OWNER_IDS", "ADMIN_ID", "ADMIN_IDS", "OWNER", "ADMIN"]
    found: Set[int] = set()
    for key in keys:
        val = os.getenv(key, "")
        if val:
            found.update(parse_owner_ids(val))
    return found

BOT_OWNER_IDS: Set[int] = get_owner_ids()

def is_owner(user_id: Optional[int]) -> bool:
    """Check if given user id is authorized as bot owner."""
    if not user_id:
        return False
    # Check dynamically in case env was populated or reloaded
    return user_id in get_owner_ids()

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BOT_USERNAME = sanitize_bot_username(os.getenv("TELEGRAM_BOT_USERNAME", "CurrencingBot"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Force Join Channels (comma-separated: e.g. @channel1, t.me/channel2, https://t.me/channel3)
FORCE_JOINS_RAW = os.getenv("FORCE_JOINS", os.getenv("Force_joins", "")).strip()

# Persistent Database
DB_PATH = os.getenv("DB_PATH", os.path.join(DATA_DIR, "currencing_bot.db"))

# Market Data Settings
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
BACKGROUND_SYNC_INTERVAL = int(os.getenv("BACKGROUND_SYNC_INTERVAL", "120"))

# Verification Messages
UNVERIFIED_MESSAGE = (
    "Please start me in private first to unlock all features! ❤️\n\n"
    "Click the button below to start me in private and get instant access to live prices, "
    "interactive charts, market overviews, and conversions."
)

GROUP_FALLBACK_MESSAGE = (
    "This group requires me to be added before I can chat here. "
    "Please add me as a member or admin! ❤️"
)
