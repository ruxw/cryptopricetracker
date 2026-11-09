"""
Unified crypto command handler.

Provides:
  /crypto <name_or_symbol>   — look up any coin by name or ticker
  /btc, /eth, /sol, /ton,
  /ltc, /xmr, /xrp, /bnb,
  /trx                       — instant per-coin shortcuts
  /top                       — alias for /overview (3×3 grid)
"""

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.graphics.templates import render_coin_stats
from bot.graphics.assets import COINS
from bot.handlers.overview import overview_command
from bot.handlers.stats import get_coin_stats_keyboard

logger = logging.getLogger(__name__)

# Help text shown when /crypto is called with no args or bad symbol
_USAGE = (
    "Usage: `/crypto <coin>`\n\n"
    "Tracks **14 cryptocurrencies & memes**:\n"
    "• Top: `btc`, `eth`, `sol`, `bnb`, `xrp`, `doge`, `ada`, `avax`, `ton`, `trx`, `ltc`, `xmr`\n"
    "• Memes: `doge`, `shib`, `pepe`\n\n"
    "Quick shortcuts: `/btc`, `/eth`, `/sol`, `/bnb`, `/xrp`, `/doge`, `/ada`, `/avax`, `/ton`, `/trx`, `/ltc`, `/xmr`, `/shib`, `/pepe`, `/top`"
)


async def _send_coin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> None:
    """Shared helper: fetch data and send the coin-stats image card."""
    chat_id = update.effective_chat.id

    status = await context.bot.send_message(
        chat_id,
        f"⏳ _Loading {symbol}…_",
        parse_mode=ParseMode.MARKDOWN
    )
    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        image_buf = render_coin_stats(
            symbol=symbol,
            price=coin_data["current_price"],
            daily_change=coin_data["change_24h"],
            weekly_change=coin_data["change_7d"],
            sparkline_prices=coin_data["sparkline"],
        )

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
        )
    except Exception as e:
        logger.error("Error generating coin stats for %s: %s", symbol, e)
        await context.bot.send_message(chat_id, f"❌ Failed to load data for {symbol}. Please try again.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass


async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/crypto <name_or_symbol> — look up any coin."""
    if not await check_user_authorization(update, context):
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(_USAGE, parse_mode=ParseMode.MARKDOWN)
        return

    raw = " ".join(args)  # allow "open network" etc.
    symbol = resolve_coin(raw)
    if not symbol:
        # Maybe they typed the uppercase symbol directly
        symbol = raw.strip().upper()
        if symbol not in COINS:
            await update.message.reply_text(
                f"Unknown coin `{raw}`.\n\n{_USAGE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    await _send_coin_stats(update, context, symbol)


async def coin_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> None:
    """Shared handler for /btc, /eth, /sol, /ton, /ltc, /xmr, /xrp, /bnb, /trx shortcuts."""
    if not await check_user_authorization(update, context):
        return
    await _send_coin_stats(update, context, symbol)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/top — alias for 3×3 market overview."""
    # Reuse existing overview_command which handles auth internally
    await overview_command(update, context)
