import logging
import os
import re
from typing import List, Dict, Any, Tuple
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

from bot.config import FORCE_JOINS_RAW

logger = logging.getLogger(__name__)

VALID_MEMBER_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.OWNER,
    "creator",  # fallback string
    "administrator",
    "member"
}

def parse_channel_target(item: str, idx: int) -> Dict[str, str]:
    """
    Parse a single channel/group entry.
    Supports formats:
    - @username
    - username
    - t.me/username
    - https://t.me/username
    - -100123456789:https://t.me/+invitehash
    - -100123456789 (chat id)
    """
    raw = item.strip()
    chat_id = raw
    url = raw

    # Handle -100xxx:url format (e.g. -100123456789:https://t.me/+hash)
    if ":" in raw and not raw.startswith("http://") and not raw.startswith("https://"):
        parts = raw.split(":", 1)
        chat_id = parts[0].strip()
        url = parts[1].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        name = f"Channel {idx}"
        return {"chat_id": chat_id, "url": url, "name": name}

    # Clean url & chat_id
    clean = re.sub(r"^https?://", "", raw)
    clean = re.sub(r"^t\.me/", "", clean).lstrip("@").strip("/")

    if raw.startswith("-100") or raw.isdigit():
        chat_id = raw
        url = f"https://t.me/c/{chat_id.replace('-100', '')}/1"
        name = f"Channel {idx}"
    elif "+" in clean or "joinchat" in clean:
        # Private invite link
        chat_id = raw
        url = f"https://t.me/{clean}"
        name = f"Channel {idx}"
    else:
        # Public username
        chat_id = f"@{clean}"
        url = f"https://t.me/{clean}"
        name = f"@{clean}"

    return {"chat_id": chat_id, "url": url, "name": name}

def get_force_join_channels() -> List[Dict[str, str]]:
    """Parse all configured force join channels dynamically from env or config."""
    import bot.config as cfg
    raw_config = os.getenv("FORCE_JOINS", os.getenv("Force_joins", getattr(cfg, "FORCE_JOINS_RAW", ""))).strip()
    if not raw_config:
        return []

    entries = [e.strip() for e in raw_config.split(",") if e.strip()]
    channels = []
    for idx, entry in enumerate(entries, 1):
        if entry:
            channels.append(parse_channel_target(entry, idx))
    return channels

async def check_user_joined_all(bot: Bot, user_id: int) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Check if a user has joined all configured force-join channels.
    Returns (True, []) if all joined or none configured.
    Returns (False, [missing_channels]) otherwise.
    """
    channels = get_force_join_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        chat_id = ch["chat_id"]
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            status = getattr(member, "status", None)
            
            # Check restricted with is_member
            if status == ChatMemberStatus.RESTRICTED:
                is_member = getattr(member, "is_member", True)
                if not is_member:
                    missing.append(ch)
            elif status not in VALID_MEMBER_STATUSES and str(status).lower() not in VALID_MEMBER_STATUSES:
                missing.append(ch)
        except TelegramError as e:
            logger.warning("Could not verify chat membership for chat %s, user %d: %s", chat_id, user_id, e)
            # If the bot is not admin in the channel or cannot access chat, don't hard block user
            # unless it's a known 'User not found' error
            err_msg = str(e).lower()
            if "user not found" in err_msg or "chat not found" in err_msg or "not a member" in err_msg:
                missing.append(ch)
            else:
                # Bot might lack permission to inspect chat, log and continue
                logger.debug("Bypassing channel check due to Telegram API restriction: %s", e)
        except Exception as e:
            # Generic exception (e.g. network error, mock in tests) — don't block the user
            logger.debug("Non-Telegram exception during membership check for %s: %s", chat_id, e)

    return len(missing) == 0, missing

def get_force_join_keyboard(channels: List[Dict[str, str]]) -> InlineKeyboardMarkup:
    """
    Build column keyboard (buttons appear one after another in single-button rows)
    with a final verification button at the bottom.
    """
    keyboard = []
    for idx, ch in enumerate(channels, 1):
        # 1 button per row (column layout)
        keyboard.append([
            InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["url"])
        ])

    # Bottom verification button
    keyboard.append([
        InlineKeyboardButton("✅ I Have Joined", callback_data="check_force_join")
    ])

    return InlineKeyboardMarkup(keyboard)

def get_force_join_message() -> str:
    """Return clean force join prompt message."""
    return (
        "⚠️ **Subscription Required**\n\n"
        "To unlock live prices, 7-day charts, and instant conversions on **Currencing**, "
        "please join our official channels below:\n\n"
        "👉 Tap each button to join, then tap **✅ I Have Joined**!"
    )
