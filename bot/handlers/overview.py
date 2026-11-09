import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.graphics.templates import render_market_overview

logger = logging.getLogger(__name__)

def get_overview_keyboard() -> InlineKeyboardMarkup:
    """Clean navigation keyboard for market overview."""
    keyboard = [
        [
            InlineKeyboardButton("₿ BTC", callback_data="stats_BTC"),
            InlineKeyboardButton("Ξ ETH", callback_data="stats_ETH"),
            InlineKeyboardButton("◎ SOL", callback_data="stats_SOL"),
        ],
        [
            InlineKeyboardButton("💎 GRAM", callback_data="stats_GRAM"),
            InlineKeyboardButton("Ł LTC", callback_data="stats_LTC"),
            InlineKeyboardButton("ɱ XMR", callback_data="stats_XMR"),
        ],
        [
            InlineKeyboardButton("✕ XRP", callback_data="stats_XRP"),
            InlineKeyboardButton("BNB", callback_data="stats_BNB"),
            InlineKeyboardButton("▲ TRX", callback_data="stats_TRX"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_overview"),
            InlineKeyboardButton("💱 Converter", callback_data="nav_convert_menu"),
        ],
        [
            InlineKeyboardButton("ATH Records", callback_data="nav_ath_menu"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def overview_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /overview or /market command."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    status_msg = await context.bot.send_message(chat_id, "⏳ _Generating live Market Overview card..._", parse_mode=ParseMode.MARKDOWN)

    try:
        overview_data = await crypto_service.get_all_overview_data()
        image_buf = render_market_overview(overview_data)

        kb = get_overview_keyboard()

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_markup=kb
        )
    except Exception as e:
        logger.error("Error generating market overview: %s", e)
        await context.bot.send_message(chat_id, "❌ Error generating market overview. Please try again.")
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
        image_buf = render_market_overview(overview_data)

        kb = get_overview_keyboard()

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_markup=kb
        )
    except Exception as e:
        logger.error("Error in overview callback: %s", e)
        await context.bot.send_message(chat_id, "❌ Could not refresh overview. Please try again.")
