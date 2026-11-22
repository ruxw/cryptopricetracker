"""
Unified crypto command handler.

Provides:
  /crypto <name_or_symbol>   — look up any coin by name or ticker
  /btc, /eth, /sol, /ton,
  /ltc, /xmr, /xrp, /bnb,
  /trx                       — instant per-coin shortcuts
  /top                       — Top crypto overview
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatType
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

async def make_crypto_card_keyboard(
    symbol: str,
    user_id: Optional[int] = None,
    is_group: bool = False,
    bot_username: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    Build action keyboard below every generated crypto card:
    - In group chats: provides deep-link URL button routing ANY member directly to the bot.
    - In private DM: toggle callback button showing current subscription status.
    """
    sym = symbol.upper()
    if sym == "TON":
        sym = "GRAM"
    b_user = bot_username or BOT_USERNAME

    if is_group:
        btn = custom_btn(
            f"Daily Rates · Tap to Sub/Unsub",
            url=f"https://t.me/{b_user}?start=sub_{sym}",
            coin=sym
        )
        return InlineKeyboardMarkup([[btn]])

    subbed = False
    if user_id:
        try:
            subbed = await is_subscribed(user_id, sym)
        except Exception:
            subbed = False

    if subbed:
        sub_text = f"Subscribed to {sym} (Tap to Unsub)"
        btn = custom_btn(sub_text, callback_data=f"sub:{sym}", icon="check")
    else:
        sub_text = f"Subscribe to {sym} Daily Rates"
        btn = custom_btn(sub_text, callback_data=f"sub:{sym}", coin=sym)

    return InlineKeyboardMarkup([[btn]])

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
    if symbol == "TON":
        symbol = "GRAM"

    bot_username = context.bot.username or BOT_USERNAME

    # In group chats, immediately route the user to bot DM with deep link
    if update.effective_chat and update.effective_chat.type != ChatType.PRIVATE:
        await query.answer(url=f"https://t.me/{bot_username}?start=sub_{symbol}")
        return

    # In private DM with the bot:
    await query.answer()
    now_subbed = await toggle_subscription(user.id, symbol)
    if now_subbed:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"{E('check')} <b>Subscribed to {symbol} Daily Insights!</b>\n\n"
                f"You have subscribed for daily insights of <b>{symbol}</b>. "
                f"You will receive daily rate cards directly in this chat."
            ),
            parse_mode=ParseMode.HTML
        )
    else:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"🔕 <b>Unsubscribed from {symbol} Daily Insights.</b>\n\n"
                f"Whenever you want to subscribe again for daily insights, just type <code>/sub {symbol.lower()}</code> and all set!"
            ),
            parse_mode=ParseMode.HTML
        )

    # Update keyboard on message in DM
    try:
        new_kb = await make_crypto_card_keyboard(symbol, user.id, is_group=False, bot_username=bot_username)
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

        is_group = bool(update.effective_chat and update.effective_chat.type != ChatType.PRIVATE)
        card_kb = await make_crypto_card_keyboard(
            symbol,
            user_id,
            is_group=is_group,
            bot_username=context.bot.username or BOT_USERNAME
        )
        sp_caption, sp_markup = await attach_sponsored_content(reply_markup=card_kb)

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
    """/top — Top crypto market overview."""
    await overview_command(update, context)

async def sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sub <currency> — Subscribe to daily insights for a coin."""
    if not await check_user_authorization(update, context):
        return

    user = update.effective_user
    args = context.args or []
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/sub &lt;currency&gt;\n<i>ex: /sub btc</i>\n\nTo unsubscribe: <code>/unsub &lt;currency&gt;</code>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw = args[0]
    sym = resolve_coin(raw) or raw.strip().upper()
    if sym == "TON":
        sym = "GRAM"

    already_subbed = await is_subscribed(user.id, sym)
    if not already_subbed:
        await toggle_subscription(user.id, sym)

    await update.message.reply_text(
        f"{E('check')} <b>Subscribed to {sym} Daily Insights!</b>\n\n"
        f"You have subscribed for daily insights of <b>{sym}</b>. You will receive daily rate cards and market updates directly in your DM.\n\n"
        f"<i>To check live rates anytime: /crypto {sym.lower()}</i>",
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_msg_id
    )

async def unsub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unsub <currency> — Unsubscribe from daily insights for a coin."""
    if not await check_user_authorization(update, context):
        return

    user = update.effective_user
    args = context.args or []
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/unsub &lt;currency&gt;\n<i>ex: /unsub btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw = args[0]
    sym = resolve_coin(raw) or raw.strip().upper()
    if sym == "TON":
        sym = "GRAM"

    already_subbed = await is_subscribed(user.id, sym)
    if already_subbed:
        await toggle_subscription(user.id, sym)

    await update.message.reply_text(
        f"🔕 <b>Unsubscribed from {sym} Daily Insights.</b>\n\n"
        f"Whenever you want to subscribe again for daily insights, just type <code>/sub {sym.lower()}</code> and all set!",
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_msg_id
    )
