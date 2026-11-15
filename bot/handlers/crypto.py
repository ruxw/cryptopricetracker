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
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.services.cache_manager import get_cached_or_render
from bot.services.sponsored import attach_sponsored_content
from bot.graphics.templates import render_coin_stats
from bot.graphics.assets import COINS
from bot.emojis import coin_emoji, E
from bot.handlers.overview import overview_command

logger = logging.getLogger(__name__)

# Single unified loading text across the bot
LOADING_TEXT = "Fetching current crypto prices"

_USAGE = (
    "<b>Usage:</b> <code>/crypto &lt;coin&gt;</code>\n\n"
    "<b>Supported Cryptocurrencies:</b>\n"
    "• Top: <code>btc</code>, <code>eth</code>, <code>sol</code>, <code>bnb</code>, <code>xrp</code>, <code>doge</code>, <code>ada</code>, <code>avax</code>, <code>ton</code>, <code>trx</code>, <code>ltc</code>, <code>xmr</code>\n"
    "• Memes: <code>doge</code>, <code>shib</code>, <code>pepe</code>\n\n"
    "<b>Shortcuts:</b> <code>/btc</code>, <code>/eth</code>, <code>/sol</code>, <code>/top</code>"
)

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

        # Ultra-fast non-blocking rendering with in-memory caching
        image_buf = await get_cached_or_render(
            render_coin_stats,
            symbol,
            price,
            daily_change,
            weekly_change,
            sparkline_prices,
            ttl=15.0
        )

        _, sp_markup = await attach_sponsored_content()

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
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
