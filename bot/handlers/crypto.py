"""
Unified crypto command handler.

Provides:
  /crypto <name_or_symbol>   — look up any coin by name or ticker
  /btc, /eth, /sol, /ton,
  /ltc, /xmr, /xrp, /bnb,
  /trx                       — instant per-coin shortcuts
  /top                       — Top 9 crypto overview
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME
from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.services.cache_manager import get_cached_or_render
from bot.services.sponsored import attach_sponsored_content
from bot.graphics.templates import render_coin_stats
from bot.graphics.assets import COINS
from bot.emojis import coin_emoji, E, custom_btn
from bot.handlers.overview import overview_command
from bot.database import (
    is_subscribed, toggle_subscription, is_user_verified,
    record_coin_lookup, save_cached_card_file_id
)

logger = logging.getLogger(__name__)

# Single unified loading text for currency cards
LOADING_TEXT = "Checking latest rates..."

_USAGE = (
    "<b>Usage:</b>\n"
    "/crypto &lt;coin name&gt;\n"
    "<i>ex /crypto btc</i>"
)

async def make_crypto_card_keyboard(symbol: str, user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """
    Build column-oriented action keyboard below every generated crypto card:
    Row 1: Subscribe / Unsubscribe for daily rates in DM
    Row 2: 7-Day Chart
    Row 3: All-Time High Record
    """
    sym = symbol.upper()
    subbed = False
    if user_id:
        try:
            subbed = await is_subscribed(user_id, sym)
        except Exception:
            subbed = False

    if subbed:
        sub_text = f"Subscribed to {sym} (Tap to Unsub)"
        sub_icon = "unsub"
    else:
        sub_text = f"Subscribe to {sym} Daily Rates"
        sub_icon = "bell"

    kb_rows = [
        [custom_btn(sub_text, callback_data=f"sub:{sym}", icon=sub_icon)],
        [custom_btn(f"{sym} 7-Day Chart", callback_data=f"stats_{sym}", coin=sym)],
        [custom_btn(f"{sym} ATH Record", callback_data=f"ath_{sym}", icon="ath")]
    ]
    return InlineKeyboardMarkup(kb_rows)

async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user clicking the Subscribe/Unsubscribe daily rate button."""
    query = update.callback_query
    user = update.effective_user
    if not user:
        await query.answer()
        return

    data = query.data or ""
    parts = data.split(":")
    if len(parts) < 2:
        await query.answer()
        return

    symbol = parts[1].upper()

    # Check if user has started the bot in DM
    verified = await is_user_verified(user.id)
    if not verified:
        bot_username = context.bot.username or BOT_USERNAME
        await query.answer(
            "⚠️ Please start me in private first so I can send your daily updates to your DM!",
            show_alert=True
        )
        return

    now_subbed = await toggle_subscription(user.id, symbol)
    if now_subbed:
        await query.answer(
            f"✅ Subscribed to {symbol} daily rates!\nYou will receive daily rate updates in your DM.",
            show_alert=True
        )
    else:
        await query.answer(
            f"🔕 Unsubscribed from {symbol} daily updates.",
            show_alert=True
        )

    # Update keyboard on message if possible
    try:
        new_kb = await make_crypto_card_keyboard(symbol, user.id)
        _, sp_markup = await attach_sponsored_content(reply_markup=new_kb)
        await query.message.edit_reply_markup(reply_markup=sp_markup)
    except Exception:
        pass

async def _send_coin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> None:
    """Shared helper: fetch data and send the coin-stats image card in reply to the user."""
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    status = await context.bot.send_message(
        chat_id=chat_id,
        text=LOADING_TEXT,
        reply_to_message_id=reply_msg_id
    )

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data["current_price"]
        daily_change = coin_data["change_24h"]
        weekly_change = coin_data["change_7d"]
        sparkline_prices = coin_data["sparkline"]

        user = update.effective_user
        user_id = user.id if user else None
        if user:
            await record_coin_lookup(user.id, symbol, price, chat_id=update.effective_chat.id)

        # Fast non-blocking rendering with in-memory caching
        image_buf = await get_cached_or_render(
            render_coin_stats,
            symbol,
            price,
            daily_change,
            weekly_change,
            sparkline_prices,
            ttl=15.0
        )

        card_kb = await make_crypto_card_keyboard(symbol, user_id)
        _, sp_markup = await attach_sponsored_content(reply_markup=card_kb)

        sent_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )

        # Cache Telegram photo file_id for instant visual card in inline queries
        if sent_msg and sent_msg.photo:
            await save_cached_card_file_id(symbol, sent_msg.photo[-1].file_id)

    except Exception as e:
        logger.error("Error generating coin stats for %s: %s", symbol, e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to load data for <b>{symbol}</b>. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
    finally:
        try:
            await status.delete()
        except Exception:
            pass

async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/crypto <name_or_symbol> — look up any coin."""
    if not await check_user_authorization(update, context):
        return

    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    args = context.args or []
    if not args:
        await update.message.reply_text(_USAGE, parse_mode=ParseMode.HTML, reply_to_message_id=reply_msg_id)
        return

    raw = " ".join(args)
    symbol = resolve_coin(raw)
    if not symbol:
        symbol = raw.strip().upper()
        if symbol not in COINS:
            await update.message.reply_text(
                f"{E('cross')} Unknown coin <code>{raw}</code>.\n\n{_USAGE}",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=reply_msg_id
            )
            return

    await _send_coin_stats(update, context, symbol)

async def coin_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> None:
    """Shared handler for /btc, /eth, /sol, /ton, /ltc, /xmr, /xrp, /bnb, /trx shortcuts."""
    if not await check_user_authorization(update, context):
        return
    await _send_coin_stats(update, context, symbol)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/top — Top 9 crypto market overview."""
    await overview_command(update, context)
