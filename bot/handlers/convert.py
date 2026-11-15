import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.ai_converter import execute_conversion
from bot.services.cache_manager import get_cached_or_render
from bot.services.ephemeral import send_ephemeral
from bot.graphics.templates import render_conversion
from bot.emojis import E, coin_emoji

logger = logging.getLogger(__name__)

LOADING_TEXT = "Fetching current crypto prices"

_HELP_TEXT = (
    f"{E('convert')} <b>Currencing AI Converter</b>\n\n"
    "Super fast & easy natural language conversions powered by AI:\n\n"
    "• <code>/convert $50 to sol</code>\n"
    "• <code>/convert 0.5 btc in eur</code>\n"
    "• <code>/convert 100 usd btc</code>\n"
    "• <code>/convert 2 eth to usd</code>\n"
    "• <code>/convert 1000 doge</code>\n"
    "• <code>/convert 50 bucks in ton</code>"
)

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /convert command powered by Gemini AI & smart natural language parser.
    Supports any natural phrasing without button mazes.
    """
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    args = context.args or []

    # If no arguments, show simple memorable ephemeral guide
    if not args:
        await send_ephemeral(
            bot=context.bot,
            chat_id=chat_id,
            text=_HELP_TEXT,
            auto_delete_seconds=45,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_query = " ".join(args)

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=LOADING_TEXT,
        reply_to_message_id=reply_msg_id
    )

    try:
        # Execute natural language conversion via Gemini AI or smart fallback
        conv = await execute_conversion(raw_query)

        crypto_symbol = conv["crypto_symbol"]
        crypto_amount = conv["crypto_amount"]
        fiat_symbol = conv["fiat_symbol"]
        fiat_value = conv["fiat_value"]
        reverse = conv["reverse"]
        summary = conv["summary"]

        # Fast non-blocking cached rendering
        image_buf = await get_cached_or_render(
            render_conversion,
            crypto_symbol,
            crypto_amount,
            fiat_symbol,
            fiat_value,
            reverse,
            ttl=15.0
        )

        c_emoji = coin_emoji(crypto_symbol)
        caption = f"{E('convert')} <b>{summary}</b>"

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
    except Exception as e:
        logger.error("Error in AI conversion: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Conversion failed for <code>{raw_query}</code>. Example: <code>/convert 100 usd btc</code>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback query compatibility handler."""
    query = update.callback_query
    await query.answer()
    if update.effective_chat:
        await send_ephemeral(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            text=_HELP_TEXT,
            auto_delete_seconds=30
        )
