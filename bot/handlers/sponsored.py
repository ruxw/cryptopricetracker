import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import is_owner
from bot.database import (
    get_sponsored_settings,
    update_sponsored_text,
    update_sponsored_button,
    toggle_sponsored_text,
    toggle_sponsored_button,
    clear_sponsored_text,
    clear_sponsored_button
)
from bot.services.sponsored import parse_sponsored_button_input, attach_sponsored_content, create_styled_button
from bot.emojis import E

logger = logging.getLogger(__name__)

async def send_sponsored_dashboard(message, query=None) -> None:
    """Render the master /sponsored dashboard for owners."""
    sp = await get_sponsored_settings()
    text_st = "🟢 ON" if sp["text_enabled"] else "🔴 OFF"
    btn_st = "🟢 ON" if sp["button_enabled"] else "🔴 OFF"

    preview_text = sp["text_html"] if sp["text_html"] else "<i>None configured</i>"
    if sp["button_text"]:
        style_label = f"[{sp.get('button_style', 'default')}]"
        btn_preview = f"{style_label} {sp['button_text']} ➔ {sp['button_url']}"
    else:
        btn_preview = "<i>None configured</i>"

    text = (
        f"<b>📢 Global Sponsored Content Management</b>\n\n"
        f"• <b>Quotation Text:</b> {text_st}\n"
        f"• <b>Inline Button:</b> {btn_st}\n\n"
        f"<b>Current Text:</b>\n{preview_text}\n\n"
        f"<b>Current Button:</b>\n<code>{btn_preview}</code>"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{'🔴 Disable' if sp['text_enabled'] else '🟢 Enable'} Text", callback_data="sp:toggle_text"),
            InlineKeyboardButton(f"{'🔴 Disable' if sp['button_enabled'] else '🟢 Enable'} Button", callback_data="sp:toggle_btn"),
        ],
        [
            InlineKeyboardButton("📝 Set Text (Quote)", callback_data="sp:set_text"),
            InlineKeyboardButton("🔗 Set Button", callback_data="sp:set_btn"),
        ],
        [
            InlineKeyboardButton("👁️ Preview", callback_data="sp:preview"),
            InlineKeyboardButton("❌ Close", callback_data="sp:close"),
        ],
        [
            InlineKeyboardButton("🗑️ Clear Text", callback_data="sp:clear_text"),
            InlineKeyboardButton("🗑️ Clear Button", callback_data="sp:clear_btn"),
        ],
    ])

    if query:
        try:
            await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)

async def sponsored_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner command /sponsored."""
    user = update.effective_user
    if not user or not is_owner(user.id):
        await update.message.reply_text(f"{E('cross')} Unauthorized. This command is restricted to bot owners.")
        return

    await send_sponsored_dashboard(update.effective_message)

async def sponsored_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sponsored dashboard interactive callbacks."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user or not is_owner(user.id):
        await query.answer("❌ Owner access required.", show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1]

    if action == "toggle_text":
        await toggle_sponsored_text()
        await send_sponsored_dashboard(query.message, query=query)

    elif action == "toggle_btn":
        await toggle_sponsored_button()
        await send_sponsored_dashboard(query.message, query=query)

    elif action == "clear_text":
        await clear_sponsored_text()
        await send_sponsored_dashboard(query.message, query=query)

    elif action == "clear_btn":
        await clear_sponsored_button()
        await send_sponsored_dashboard(query.message, query=query)

    elif action == "close":
        context.user_data.pop("awaiting_sponsored_text", None)
        context.user_data.pop("awaiting_sponsored_btn", None)
        try:
            await query.message.delete()
        except Exception:
            pass

    elif action == "preview":
        dummy_text = "<b>Example Bot Response</b>\nHere is how sponsored content looks across bot messages:"
        dummy_text, dummy_markup = await attach_sponsored_content(dummy_text, None)
        await query.message.reply_text(dummy_text, parse_mode=ParseMode.HTML, reply_markup=dummy_markup)

    elif action == "set_text":
        context.user_data["awaiting_sponsored_text"] = True
        context.user_data.pop("awaiting_sponsored_btn", None)
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sp:cancel")]])
        await query.message.edit_text(
            "<b>📝 Set Sponsored Text:</b>\n\n"
            "Send or quote any message now (using Ctrl+Shift+. or any text formatting).\n"
            "Bold, italics, links, blockquotes, and Telegram custom emojis will be preserved exactly.\n\n"
            "Click Cancel below to abort.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_kb
        )

    elif action == "set_btn":
        context.user_data["awaiting_sponsored_btn"] = True
        context.user_data.pop("awaiting_sponsored_text", None)
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sp:cancel")]])
        await query.message.edit_text(
            "<b>🔗 Set Sponsored Inline Button:</b>\n\n"
            "Send your button configuration in this format:\n"
            "<code>#color Button Text - https://link</code>\n\n"
            "<b>Supported color tags:</b>\n"
            "• <code>#red</code> (danger style)\n"
            "• <code>#green</code> (success style)\n"
            "• <code>#blue</code> (primary style)\n\n"
            "<b>Example:</b>\n"
            "<code>#red Join the #1 OTC - t.me/Oncarts</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_kb
        )

    elif action == "cancel":
        context.user_data.pop("awaiting_sponsored_text", None)
        context.user_data.pop("awaiting_sponsored_btn", None)
        await send_sponsored_dashboard(query.message, query=query)
