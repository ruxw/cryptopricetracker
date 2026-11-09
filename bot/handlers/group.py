import logging
import time
from typing import Dict
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from bot.config import GROUP_FALLBACK_MESSAGE, BOT_USERNAME
from bot.database import is_user_verified
from bot.middlewares.auth import get_verify_keyboard

logger = logging.getLogger(__name__)

# Anti-spam tracker to prevent repeated fallback messages: chat_id -> timestamp
_group_fallback_cooldown: Dict[int, float] = {}
COOLDOWN_SECONDS = 60

async def group_fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle group messages where the bot is mentioned or addressed.
    Checks private start verification, and provides the friendly guest fallback
    without spamming.
    """
    message = update.message
    if not message or not update.effective_chat:
        return

    chat = update.effective_chat
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    user = update.effective_user
    if not user or user.is_bot:
        return

    bot_username = context.bot.username or BOT_USERNAME
    bot_mention = f"@{bot_username.lower()}"
    text = (message.text or message.caption or "").lower()

    # Check if this bot is explicitly mentioned
    if bot_mention in text:
        # Check verification first
        verified = await is_user_verified(user.id)
        if not verified:
            kb = get_verify_keyboard(bot_username)
            await message.reply_text(
                "Please start me in private first to unlock all features! ❤️",
                reply_markup=kb
            )
            return

        # Cooldown check to avoid group spam
        now = time.time()
        last_sent = _group_fallback_cooldown.get(chat.id, 0)
        if now - last_sent < COOLDOWN_SECONDS:
            return
        _group_fallback_cooldown[chat.id] = now

        # Send friendly guest mode guide or add-me fallback
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Use Guest Mode (Inline)", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("➕ Add Me as Member / Admin", url=f"https://t.me/{bot_username}?startgroup=true")]
        ])
        await message.reply_text(GROUP_FALLBACK_MESSAGE, reply_markup=kb)

async def bot_added_to_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot being added as a member or administrator in a group."""
    chat = update.effective_chat
    if not chat:
        return

    bot_username = context.bot.username or BOT_USERNAME
    welcome_text = (
        "👋 **Thank you for adding Currencing to the group!** ❤️\n\n"
        "I provide live cryptocurrency price tracking, interactive 7-day charts, "
        "and market intelligence.\n\n"
        "• Use `/overview` for the 3×3 live market grid\n"
        "• Use `/stats BTC` for detailed coin charts\n"
        "• Use `/convert 0.3 LTC USD` to convert currencies\n"
        f"• Or use `@{bot_username}` for instant inline guest lookups!"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Market Overview", callback_data="nav_overview")],
        [InlineKeyboardButton("🔍 Try Inline Mode", switch_inline_query_current_chat="")]
    ])
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=welcome_text,
            reply_markup=kb
        )
    except Exception as e:
        logger.debug("Failed to send welcome message to group: %s", e)
