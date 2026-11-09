import logging
from typing import Optional, Callable, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME, UNVERIFIED_MESSAGE
from bot.database import is_user_verified, record_interaction
from bot.services.force_join import (
    check_user_joined_all, get_force_join_keyboard, get_force_join_message, get_force_join_channels
)

logger = logging.getLogger(__name__)

def get_start_deep_link(bot_username: str) -> str:
    """Generate deep link to start bot in private chat."""
    username = bot_username.lstrip("@")
    return f"https://t.me/{username}?start=verify"

def get_verify_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Return inline keyboard with deep link to start privately."""
    url = get_start_deep_link(bot_username)
    keyboard = [
        [InlineKeyboardButton("🚀 Start Bot in Private", url=url)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_user_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Mandatory checks:
    1. Verify persistent private /start authorization in SQLite DB.
    2. Verify user has joined all required force-join channels/groups (if configured).
    """
    user = update.effective_user
    if not user:
        return False

    # 1. Check persistent database status
    verified = await is_user_verified(user.id)
    if not verified:
        bot_username = context.bot.username or BOT_USERNAME
        kb = get_verify_keyboard(bot_username)

        if update.callback_query:
            await update.callback_query.answer("Please start the bot privately first! ❤️", show_alert=True)
            if update.effective_chat:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=UNVERIFIED_MESSAGE,
                        reply_markup=kb
                    )
                except Exception as e:
                    logger.debug("Could not send unverified prompt: %s", e)
        elif update.message:
            try:
                await update.message.reply_text(
                    text=UNVERIFIED_MESSAGE,
                    reply_markup=kb
                )
            except Exception as e:
                logger.debug("Could not reply unverified prompt: %s", e)

        return False

    # 2. Check Force-Join Channels (if any are configured)
    all_joined, missing = await check_user_joined_all(context.bot, user.id)
    if not all_joined:
        fj_msg = get_force_join_message()
        fj_kb = get_force_join_keyboard(missing)

        if update.callback_query:
            await update.callback_query.answer("Please join our official channels first! 📢", show_alert=True)
            if update.effective_chat:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=fj_msg,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=fj_kb
                    )
                except Exception as e:
                    logger.debug("Could not send force-join prompt: %s", e)
        elif update.message:
            try:
                await update.message.reply_text(
                    text=fj_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=fj_kb
                )
            except Exception as e:
                logger.debug("Could not reply force-join prompt: %s", e)

        return False

    # User is verified and joined all required channels
    query_type = "command" if update.message else "callback" if update.callback_query else "other"
    await record_interaction(user.id, query_type)
    return True
