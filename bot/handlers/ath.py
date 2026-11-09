import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.graphics.templates import render_all_time_high
from bot.graphics.assets import COINS, format_price
from bot.emojis import coin_fallback, ui_fallback

logger = logging.getLogger(__name__)

def get_ath_keyboard(current_symbol: str) -> InlineKeyboardMarkup:
    """Return navigation keyboard for ATH records."""
    default_row = ["BTC", "ETH", "SOL"] if current_symbol not in ["BTC", "ETH", "SOL"] else ["DOGE", "GRAM", "XRP"]
    alt_row = ["BNB", "ADA", "AVAX"] if current_symbol not in ["BNB", "ADA", "AVAX"] else ["PEPE", "SHIB", "SUI"]

    row1 = [InlineKeyboardButton(f"{coin_fallback(s)} {s}", callback_data=f"ath_{s}") for s in default_row if s != current_symbol][:3]
    row2 = [InlineKeyboardButton(f"{coin_fallback(s)} {s}", callback_data=f"ath_{s}") for s in alt_row if s != current_symbol][:3]

    keyboard = [
        row1,
        row2,
        [
            InlineKeyboardButton(f"{ui_fallback('stats')} Chart & Stats", callback_data=f"stats_{current_symbol}"),
            InlineKeyboardButton(f"{ui_fallback('chart')} Overview", callback_data="nav_overview")
        ],
        [
            InlineKeyboardButton("All Tracked Coins", callback_data="nav_ath_menu"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ath_picker_keyboard() -> InlineKeyboardMarkup:
    """Clean keyboard to select coin for ATH."""
    keyboard = [
        [
            InlineKeyboardButton(f"{coin_fallback('BTC')} Bitcoin", callback_data="ath_BTC"),
            InlineKeyboardButton(f"{coin_fallback('ETH')} Ethereum", callback_data="ath_ETH"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('SOL')} Solana", callback_data="ath_SOL"),
            InlineKeyboardButton(f"{coin_fallback('BNB')} BNB", callback_data="ath_BNB"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('XRP')} XRP", callback_data="ath_XRP"),
            InlineKeyboardButton(f"{coin_fallback('DOGE')} Dogecoin", callback_data="ath_DOGE"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('ADA')} Cardano", callback_data="ath_ADA"),
            InlineKeyboardButton(f"{coin_fallback('AVAX')} Avalanche", callback_data="ath_AVAX"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('GRAM')} Gram (TON)", callback_data="ath_GRAM"),
            InlineKeyboardButton(f"{coin_fallback('TRX')} Tron", callback_data="ath_TRX"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('LTC')} Litecoin", callback_data="ath_LTC"),
            InlineKeyboardButton(f"{coin_fallback('XMR')} Monero", callback_data="ath_XMR"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('SHIB')} Shiba Inu", callback_data="ath_SHIB"),
            InlineKeyboardButton(f"{coin_fallback('PEPE')} Pepe", callback_data="ath_PEPE"),
        ],
        [
            InlineKeyboardButton(f"{ui_fallback('chart')} Market Overview", callback_data="nav_overview"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def ath_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ath [symbol] command."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    raw = args[0] if args else "btc"
    symbol = resolve_coin(raw) or raw.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"Select a cryptocurrency to view its All-Time High record:",
            reply_markup=get_ath_picker_keyboard()
        )
        return

    status_msg = await context.bot.send_message(chat_id, f"⏳ _Retrieving {symbol} All-Time High record..._", parse_mode=ParseMode.MARKDOWN)
    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        ath_price = coin_data.get("ath", 0.0)
        ath_date = coin_data.get("ath_date", "")

        image_buf = render_all_time_high(
            symbol=symbol,
            ath_price=ath_price,
            ath_date=ath_date
        )

        name = coin_data.get("name", symbol)
        p_str = format_price(ath_price, decimals=COINS[symbol]["decimals"])
        date_str = ath_date
        try:
            dt = datetime.fromisoformat(ath_date.replace("Z", "+00:00"))
            date_str = dt.strftime("%B %d, %Y")
        except Exception:
            pass

        caption = (
            f"🚀 **{name} ({symbol}) All-Time High Record**\n"
            f"• **Peak ATH Price:** `${p_str}`\n"
            f"• **Recorded Date:** `{date_str}`\n\n"
            f"_Official record powered by Currencing:_"
        )
        kb = get_ath_keyboard(symbol)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except Exception as e:
        logger.error("Error generating ATH card for %s: %s", symbol, e)
        await context.bot.send_message(chat_id, f"❌ Failed to load ATH for {symbol}.")
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def ath_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for ATH."""
    query = update.callback_query
    await query.answer()

    if not await check_user_authorization(update, context):
        return

    data = query.data
    chat_id = update.effective_chat.id

    if data == "nav_ath_menu":
        await context.bot.send_message(
            chat_id,
            "🚀 **Select a cryptocurrency to view its All-Time High record:**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ath_picker_keyboard()
        )
        return

    symbol = data.replace("ath_", "").upper() if data.startswith("ath_") else "BTC"
    if symbol not in COINS:
        symbol = "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        image_buf = render_all_time_high(
            symbol=symbol,
            ath_price=coin_data.get("ath", 0.0),
            ath_date=coin_data.get("ath_date", "")
        )

        name = coin_data.get("name", symbol)
        p_str = format_price(coin_data.get("ath", 0.0), decimals=COINS[symbol]["decimals"])
        date_str = coin_data.get("ath_date", "")
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            date_str = dt.strftime("%B %d, %Y")
        except Exception:
            pass

        caption = (
            f"🚀 **{name} ({symbol}) All-Time High Record**\n"
            f"• **Peak ATH Price:** `${p_str}`\n"
            f"• **Recorded Date:** `{date_str}`\n\n"
            f"_Official record powered by Currencing:_"
        )
        kb = get_ath_keyboard(symbol)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except Exception as e:
        logger.error("Error in ATH callback: %s", e)
        await context.bot.send_message(chat_id, f"❌ Failed to load ATH for {symbol}.")
