import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.cache_manager import get_cached_or_render
from bot.graphics.templates import render_market_overview
from bot.emojis import E

logger = logging.getLogger(__name__)

LOADING_TEXT = "Fetching current crypto prices"

async def overview_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /top or /overview command (Top 9 Cryptocurrencies)."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=LOADING_TEXT,
        reply_to_message_id=reply_msg_id
    )

    try:
        overview_data = await crypto_service.get_all_overview_data()
        image_buf = await get_cached_or_render(render_market_overview, overview_data, ttl=15.0)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id
        )
    except Exception as e:
        logger.error("Error generating Top market overview: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Error generating Top overview. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def overview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for overview without keyboard clutter."""
    query = update.callback_query
    await query.answer()

    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    try:
        if query.data == "refresh_overview":
            await crypto_service.refresh_market_data(force=True)

        overview_data = await crypto_service.get_all_overview_data()
        image_buf = await get_cached_or_render(render_market_overview, overview_data, ttl=15.0)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf
        )
    except Exception as e:
        logger.error("Error in overview callback: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Could not refresh Top overview. Please try again.",
            parse_mode=ParseMode.HTML
        )
