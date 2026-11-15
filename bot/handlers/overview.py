import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.cache_manager import get_cached_or_render
from bot.services.sponsored import attach_sponsored_content
from bot.graphics.templates import render_market_overview
from bot.emojis import E, custom_btn
from bot.database import save_cached_card_file_id

logger = logging.getLogger(__name__)

LOADING_TEXT = "Checking latest rates..."

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

        kb = InlineKeyboardMarkup([
            [custom_btn("🔄 Refresh Overview", callback_data="refresh_overview", icon="refresh")],
            [custom_btn("⚡ Daily Thought", callback_data="fun:daily", icon="currencing"),
             custom_btn("🐸 Fun Meme", callback_data="fun:meme", icon="meme")]
        ])
        _, sp_markup = await attach_sponsored_content(reply_markup=kb)

        sent_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
        if sent_msg and sent_msg.photo:
            await save_cached_card_file_id("overview", sent_msg.photo[-1].file_id)

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
    """Handle callback queries for overview."""
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

        kb = InlineKeyboardMarkup([
            [custom_btn("🔄 Refresh Overview", callback_data="refresh_overview", icon="refresh")],
            [custom_btn("⚡ Daily Thought", callback_data="fun:daily", icon="currencing"),
             custom_btn("🐸 Fun Meme", callback_data="fun:meme", icon="meme")]
        ])
        _, sp_markup = await attach_sponsored_content(reply_markup=kb)

        sent_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_markup=sp_markup
        )
        if sent_msg and sent_msg.photo:
            await save_cached_card_file_id("overview", sent_msg.photo[-1].file_id)

    except Exception as e:
        logger.error("Error in overview callback: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Could not refresh Top overview. Please try again.",
            parse_mode=ParseMode.HTML
        )
