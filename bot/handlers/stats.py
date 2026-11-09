import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.graphics.templates import render_coin_stats
from bot.graphics.assets import COINS, format_price, format_change
from bot.emojis import coin_fallback, ui_fallback

logger = logging.getLogger(__name__)

def get_coin_stats_keyboard(current_symbol: str) -> InlineKeyboardMarkup:
    """Return navigation keyboard for individual coin stats."""
    # Context-sensitive quick-switch options
    default_row = ["BTC", "ETH", "SOL"] if current_symbol not in ["BTC", "ETH", "SOL"] else ["DOGE", "GRAM", "XRP"]
    alt_row = ["BNB", "ADA", "AVAX"] if current_symbol not in ["BNB", "ADA", "AVAX"] else ["PEPE", "SHIB", "SUI"]

    row1 = [InlineKeyboardButton(f"{coin_fallback(s)} {s}", callback_data=f"stats_{s}") for s in default_row if s != current_symbol][:3]
    row2 = [InlineKeyboardButton(f"{coin_fallback(s)} {s}", callback_data=f"stats_{s}") for s in alt_row if s != current_symbol][:3]

    keyboard = [
        row1,
        row2,
        [
            InlineKeyboardButton(f"{ui_fallback('refresh')} Refresh", callback_data=f"refresh_stats_{current_symbol}"),
            InlineKeyboardButton(f"{ui_fallback('ath')} ATH", callback_data=f"ath_{current_symbol}")
        ],
        [
            InlineKeyboardButton(f"{ui_fallback('convert')} Convert", callback_data=f"conv_from_{current_symbol}"),
            InlineKeyboardButton(f"{ui_fallback('chart')} Overview", callback_data="nav_overview")
        ],
        [
            InlineKeyboardButton("All Tracked Coins", callback_data="nav_stats_menu"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stats_picker_keyboard() -> InlineKeyboardMarkup:
    """Clean selector keyboard for choosing any tracked coin."""
    keyboard = [
        [
            InlineKeyboardButton(f"{coin_fallback('BTC')} Bitcoin", callback_data="stats_BTC"),
            InlineKeyboardButton(f"{coin_fallback('ETH')} Ethereum", callback_data="stats_ETH"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('SOL')} Solana", callback_data="stats_SOL"),
            InlineKeyboardButton(f"{coin_fallback('BNB')} BNB", callback_data="stats_BNB"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('XRP')} XRP", callback_data="stats_XRP"),
            InlineKeyboardButton(f"{coin_fallback('DOGE')} Dogecoin", callback_data="stats_DOGE"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('ADA')} Cardano", callback_data="stats_ADA"),
            InlineKeyboardButton(f"{coin_fallback('AVAX')} Avalanche", callback_data="stats_AVAX"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('GRAM')} Gram (TON)", callback_data="stats_GRAM"),
            InlineKeyboardButton(f"{coin_fallback('TRX')} Tron", callback_data="stats_TRX"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('LTC')} Litecoin", callback_data="stats_LTC"),
            InlineKeyboardButton(f"{coin_fallback('XMR')} Monero", callback_data="stats_XMR"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('SHIB')} Shiba Inu", callback_data="stats_SHIB"),
            InlineKeyboardButton(f"{coin_fallback('PEPE')} Pepe", callback_data="stats_PEPE"),
        ],
        [
            InlineKeyboardButton(f"{ui_fallback('chart')} Market Overview", callback_data="nav_overview"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats [symbol] command."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    symbol = args[0].upper() if args else "BTC"

    if symbol not in COINS:
        # Prompt selection
        await update.message.reply_text(
            f"Asset `{symbol}` is not in tracked list.\nSelect a cryptocurrency below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_stats_picker_keyboard()
        )
        return

    status_msg = await context.bot.send_message(chat_id, f"⏳ _Rendering {symbol} 7-day chart & statistics..._", parse_mode=ParseMode.MARKDOWN)
    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        image_buf = render_coin_stats(
            symbol=symbol,
            price=coin_data["current_price"],
            daily_change=coin_data["change_24h"],
            weekly_change=coin_data["change_7d"],
            sparkline_prices=coin_data["sparkline"]
        )

        name = coin_data.get("name", symbol)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
        )
    except Exception as e:
        logger.error("Error generating coin stats for %s: %s", symbol, e)
        await context.bot.send_message(chat_id, f"❌ Failed to load stats for {symbol}. Please try again.")
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for coin stats."""
    query = update.callback_query
    await query.answer()

    if not await check_user_authorization(update, context):
        return

    data = query.data
    chat_id = update.effective_chat.id

    if data == "nav_stats_menu":
        await context.bot.send_message(
            chat_id,
            "📈 **Select a cryptocurrency to view 7-day price statistics & chart:**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_stats_picker_keyboard()
        )
        return

    force_refresh = data.startswith("refresh_stats_")
    if force_refresh:
        symbol = data.replace("refresh_stats_", "").upper()
        await crypto_service.refresh_market_data(force=True)
    elif data.startswith("stats_"):
        symbol = data.replace("stats_", "").upper()
    else:
        symbol = "BTC"

    if symbol not in COINS:
        symbol = "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        image_buf = render_coin_stats(
            symbol=symbol,
            price=coin_data["current_price"],
            daily_change=coin_data["change_24h"],
            weekly_change=coin_data["change_7d"],
            sparkline_prices=coin_data["sparkline"]
        )

        name = coin_data.get("name", symbol)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
        )
    except Exception as e:
        logger.error("Error in stats callback: %s", e)
        await context.bot.send_message(chat_id, f"❌ Failed to load stats for {symbol}.")
