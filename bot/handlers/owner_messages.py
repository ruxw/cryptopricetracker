import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import is_owner
from bot.database import (
    get_verified_users_count,
    get_active_groups_count,
    update_sponsored_text,
    update_sponsored_button
)
from bot.services.sponsored import parse_sponsored_button_input
from bot.handlers.sponsored import send_sponsored_dashboard

logger = logging.getLogger(__name__)

async def owner_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle owner stateful wizard messages (Broadcast content, Sponsored text, Sponsored button).
    Returns True if handled, False otherwise.
    """
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not is_owner(user.id):
        return False

    # 1. Broadcast Content Wizard
    if "broadcast_setup" in context.user_data:
        setup = context.user_data["broadcast_setup"]
        setup["message_id"] = message.message_id
        setup["from_chat_id"] = message.chat_id

        target_type = setup["target_type"]
        if target_type == "users":
            count = await get_verified_users_count()
            label = f"All Bot Users ({count})"
        elif target_type == "groups":
            count = await get_active_groups_count()
            label = f"All Deal GCs ({count})"
        else:
            u_count = await get_verified_users_count()
            g_count = await get_active_groups_count()
            count = u_count + g_count
            label = f"Both Users & Deal GCs ({count})"

        await message.reply_text("<b>📢 Broadcast Preview:</b>", parse_mode=ParseMode.HTML)
        # Perfectly copy the message preserving media, stickers, videos, custom emojis & formatting
        await context.bot.copy_message(
            chat_id=message.chat_id,
            from_chat_id=message.chat_id,
            message_id=message.message_id
        )

        confirm_text = (
            f"<b>📢 Broadcast Confirmation</b>\n\n"
            f"• <b>Target:</b> {label}\n"
            f"• <b>Total Recipients:</b> <code>{count}</code>\n\n"
            f"Do you want to broadcast this message?"
        )
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Broadcast", callback_data="bd:confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="bd:cancel"),
            ]
        ])
        await message.reply_text(confirm_text, parse_mode=ParseMode.HTML, reply_markup=markup)
        return True

    # 2. Sponsored Text Wizard
    if context.user_data.get("awaiting_sponsored_text"):
        html_content = message.text_html or message.caption_html or ""
        if not html_content:
            await message.reply_text("⚠️ Empty message. Please send text or press Cancel.")
            return True

        await update_sponsored_text(html_content, enabled=1)
        context.user_data.pop("awaiting_sponsored_text", None)
        await message.reply_text("✅ <b>Sponsored text saved and enabled!</b>", parse_mode=ParseMode.HTML)
        await send_sponsored_dashboard(message)
        return True

    # 3. Sponsored Button Wizard
    if context.user_data.get("awaiting_sponsored_btn"):
        content = (message.text or "").strip()
        parsed = parse_sponsored_button_input(content)
        if not parsed:
            await message.reply_text(
                "⚠️ <b>Invalid format.</b>\n"
                "Please send as:\n<code>#red Join the #1 OTC - t.me/Oncarts</code>",
                parse_mode=ParseMode.HTML
            )
            return True

        style, btn_text, btn_url = parsed
        await update_sponsored_button(style, btn_text, btn_url, enabled=1)
        context.user_data.pop("awaiting_sponsored_btn", None)
        await message.reply_text("✅ <b>Sponsored button saved and enabled!</b>", parse_mode=ParseMode.HTML)
        await send_sponsored_dashboard(message)
        return True

    return False
