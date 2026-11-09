import os
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

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BOT_USERNAME = sanitize_bot_username(os.getenv("TELEGRAM_BOT_USERNAME", "CurrencingBot"))

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
