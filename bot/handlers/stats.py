import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.services.cache_manager import get_cached_or_render
from bot.services.sponsored import attach_sponsored_content
from bot.graphics.templates import render_coin_stats
from bot.graphics.assets import COINS
from bot.emojis import E, coin_emoji, custom_btn
from bot.database import save_cached_card_file_id

logger = logging.getLogger(__name__)

LOADING_TEXT = "Checking latest rates..."

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats [symbol] command."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/stats &lt;coin name&gt;\n<i>ex /stats btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw = args[0]
    symbol = resolve_coin(raw) or raw.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"{E('cross')} Unknown coin <b>{raw}</b>.\n\n"
            "<b>Usage:</b>\n/stats &lt;coin name&gt;\n<i>ex /stats btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=LOADING_TEXT,
        reply_to_message_id=reply_msg_id
    )

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        image_buf = await get_cached_or_render(
            render_coin_stats,
            symbol,
            coin_data["current_price"],
            coin_data["change_24h"],
            coin_data["change_7d"],
            coin_data["sparkline"],
            ttl=15.0
        )

        kb = InlineKeyboardMarkup([
            [custom_btn(f"Subscribe to {symbol} Daily Rates", callback_data=f"sub:{symbol}", coin=symbol)]
        ])
        sp_caption, sp_markup = await attach_sponsored_content(reply_markup=kb)

        send_kwargs = {
            "chat_id": chat_id,
            "photo": image_buf,
            "reply_markup": sp_markup,
        }
        if reply_msg_id:
            send_kwargs["reply_to_message_id"] = reply_msg_id
        if sp_caption:
            send_kwargs["caption"] = sp_caption
            send_kwargs["parse_mode"] = ParseMode.HTML

        sent_msg = await context.bot.send_photo(**send_kwargs)
        if sent_msg and sent_msg.photo:
            await save_cached_card_file_id(symbol, sent_msg.photo[-1].file_id)

    except Exception as e:
        logger.error("Error generating stats for %s: %s", symbol, e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to load stats for <b>{symbol}</b>. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback query handler for stats."""
    query = update.callback_query
    await query.answer()
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    data = query.data or ""
    parts = data.split("_")
    symbol = parts[1].upper() if len(parts) > 1 and parts[1].upper() in COINS else "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        image_buf = await get_cached_or_render(
            render_coin_stats,
            symbol,
            coin_data["current_price"],
            coin_data["change_24h"],
            coin_data["change_7d"],
            coin_data["sparkline"],
            ttl=15.0
        )

        kb = InlineKeyboardMarkup([
            [custom_btn(f"Subscribe to {symbol} Daily Rates", callback_data=f"sub:{symbol}", coin=symbol)]
        ])
        sp_caption, sp_markup = await attach_sponsored_content(reply_markup=kb)

        send_kwargs = {
            "chat_id": chat_id,
            "photo": image_buf,
            "reply_markup": sp_markup,
        }
        if sp_caption:
            send_kwargs["caption"] = sp_caption
            send_kwargs["parse_mode"] = ParseMode.HTML

        sent_msg = await context.bot.send_photo(**send_kwargs)
        if sent_msg and sent_msg.photo:
            await save_cached_card_file_id(symbol, sent_msg.photo[-1].file_id)

    except Exception as e:
        logger.error("Error in stats callback: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Could not load stats for {symbol}.",
            parse_mode=ParseMode.HTML
        )
