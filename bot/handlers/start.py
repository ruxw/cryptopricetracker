import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME
from bot.database import register_private_start, is_user_verified, record_interaction
from bot.middlewares.auth import get_verify_keyboard
from bot.services.force_join import check_user_joined_all, get_force_join_keyboard, get_force_join_message
from bot.services.ephemeral import send_ephemeral
from bot.emojis import E, coin_emoji

logger = logging.getLogger(__name__)

def make_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Generate aesthetic minimal inline keyboard for /start."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="Add bot to chat ↗", url=f"https://t.me/{bot_username}?startgroup=start"),
            InlineKeyboardButton(text="View Help Menu", callback_data="help:menu")
        ]
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with clean aesthetic minimal interface and force sub check."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    bot_username = context.bot.username or BOT_USERNAME
    args = context.args or []
    is_deep_link_verify = len(args) > 0 and args[0].lower() == "verify"
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    if chat.type == ChatType.PRIVATE:
        await register_private_start(user.id, user.username, user.first_name)
        await record_interaction(user.id, "start", " ".join(args))

        # Check Force Sub if configured
        all_joined, missing = await check_user_joined_all(context.bot, user.id)
        if not all_joined:
            text = get_force_join_message()
            kb = get_force_join_keyboard(missing)
            await update.message.reply_text(
                text,
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_msg_id
            )
            return

        user_tag = f"@{user.username}" if user.username else user.first_name
        if is_deep_link_verify:
            greeting = (
                f"{E('check')} <b>Verified, {user.first_name}!</b>\n\n"
                f"Hey <b>{user_tag}</b>, you can now use Currencing everywhere — in private chats and in groups."
            )
        else:
            greeting = (
                f"Hey <b>{user_tag}</b>,\n\n"
                f"🔗 <b>@{bot_username}</b>\n"
                f"Live crypto prices, charts and conversions, plus real-time market intelligence and trading tools.\n\n"
                f"➡️ /help for the full command list."
            )

        await update.message.reply_text(
            greeting,
            parse_mode=ParseMode.HTML,
            reply_markup=make_start_keyboard(bot_username),
            reply_to_message_id=reply_msg_id
        )

    else:
        # Group chat
        verified = await is_user_verified(user.id)
        if not verified:
            kb = get_verify_keyboard(bot_username)
            await update.message.reply_text(
                "Please start me in private first to unlock all features! ❤️",
                reply_markup=kb,
                reply_to_message_id=reply_msg_id
            )
            return

        await record_interaction(user.id, "group_start")
        group_msg = (
            f"{E('gem')} <b>Currencing Active in Group</b>\n\n"
            f"Use commands directly:\n"
            f"• <code>/top</code> — Top 9 crypto overview\n"
            f"• <code>/btc</code>, <code>/eth</code>, <code>/sol</code>, <code>/bnb</code>\n"
            f"• <code>/convert 100 usd btc</code>\n"
            f"• <code>/ath sol</code>\n"
            f"• <code>/chatvibe</code> — Chat's top checked coins"
        )
        await update.message.reply_text(
            group_msg,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with ephemeral self-deleting message and custom emojis."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    verified = await is_user_verified(user.id)
    bot_username = context.bot.username or BOT_USERNAME
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    if not verified:
        kb = get_verify_keyboard(bot_username)
        await update.message.reply_text(
            "Please start me in private first to unlock all features! ❤️",
            reply_markup=kb,
            reply_to_message_id=reply_msg_id
        )
        return

    help_text = (
        f"🔗 <b>@{bot_username} Commands</b>\n\n"
        f"📊 <b>Prices & Charts:</b>\n"
        f"• <code>/top</code> — Top cryptos at a glance\n"
        f"• <code>/crypto &lt;coin&gt;</code> — Live price card for any coin\n"
        f"• <code>/btc</code>, <code>/eth</code>, <code>/sol</code>, <code>/bnb</code> — Ticker shortcuts\n"
        f"• <code>/ath &lt;coin&gt;</code> — All-time high for any coin\n"
        f"• <code>/convert 0.5 btc</code> — Crypto to USD conversion\n"
        f"• <code>/convert $50 to sol</code> — USD to crypto conversion\n\n"
        f"👻 <b>Fun & Meme Commands:</b>\n"
        f"• <code>/cope &lt;coin&gt;</code> — Could be worse — vs the all-time low\n"
        f"• <code>/panic &lt;coin&gt;</code> — Emergency panic index & calming checklist\n"
        f"• <code>/wagmi</code> — Today's top rocket market gainers\n"
        f"• <code>/satoshi</code> — Random quote from Satoshi Nakamoto\n"
        f"• <code>/predict &lt;coin&gt;</code> — 100% expert technical price prediction\n"
        f"• <code>/didyouknow &lt;coin&gt;</code> — Interesting crypto history and trivia\n"
        f"• <code>/me</code> — Your personal usage intelligence recap\n"
        f"• <code>/firstseen &lt;coin&gt;</code> — Price change since you first checked\n"
        f"• <code>/lookup &lt;coin&gt;</code> — Your last check vs the price now\n"
        f"• <code>/chatvibe</code> — This chat's most-checked coins"
    )

    # Send as ephemeral self-deleting message (auto-deletes in 60s to keep chat pristine)
    await send_ephemeral(
        bot=context.bot,
        chat_id=chat.id,
        text=help_text,
        auto_delete_seconds=60,
        reply_to_message_id=reply_msg_id
    )

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback to return to main menu or show help."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    bot_username = context.bot.username or BOT_USERNAME
    help_text = (
        f"🔗 <b>@{bot_username} Commands</b>\n\n"
        f"📊 <b>Prices & Charts:</b>\n"
        f"• <code>/top</code> — Top cryptos at a glance\n"
        f"• <code>/crypto &lt;coin&gt;</code> — Live price card for any coin\n"
        f"• <code>/btc</code>, <code>/eth</code>, <code>/sol</code>, <code>/bnb</code> — Ticker shortcuts\n"
        f"• <code>/ath &lt;coin&gt;</code> — All-time high for any coin\n"
        f"• <code>/convert 0.5 btc</code> — Crypto to USD conversion\n"
        f"• <code>/convert $50 to sol</code> — USD to crypto conversion\n\n"
        f"👻 <b>Fun & Meme Commands:</b>\n"
        f"• <code>/cope &lt;coin&gt;</code> — Could be worse — vs the all-time low\n"
        f"• <code>/panic &lt;coin&gt;</code> — Emergency panic index & calming checklist\n"
        f"• <code>/wagmi</code> — Today's top rocket market gainers\n"
        f"• <code>/satoshi</code> — Random quote from Satoshi Nakamoto\n"
        f"• <code>/predict &lt;coin&gt;</code> — 100% expert technical price prediction\n"
        f"• <code>/didyouknow &lt;coin&gt;</code> — Interesting crypto history and trivia\n"
        f"• <code>/me</code> — Your personal usage intelligence recap\n"
        f"• <code>/firstseen &lt;coin&gt;</code> — Price change since you first checked\n"
        f"• <code>/lookup &lt;coin&gt;</code> — Your last check vs the price now\n"
        f"• <code>/chatvibe</code> — This chat's most-checked coins"
    )

    back_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Add bot to chat ↗", url=f"https://t.me/{bot_username}?startgroup=start")]
    ])
    try:
        await query.message.edit_text(help_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)
    except Exception:
        await query.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

async def check_force_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user clicking '✅ I Have Joined' verification button."""
    query = update.callback_query
    user = update.effective_user
    if not user:
        return

    all_joined, missing = await check_user_joined_all(context.bot, user.id)
    if all_joined:
        await query.answer("✅ Verified! All required channels joined.", show_alert=True)
        text = (
            f"🎉 <b>Access Granted, {user.first_name}!</b>\n\n"
            "All features are unlocked! Track live markets, 7-day charts, and AI conversions.\n\n"
            "Type <code>/top</code> or <code>/btc</code> to get started!"
        )
        try:
            await query.message.edit_text(text, parse_mode=ParseMode.HTML)
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await query.answer("❌ You still haven't joined all required channels! Please join them first.", show_alert=True)
        fj_msg = get_force_join_message()
        fj_kb = get_force_join_keyboard(missing)
        try:
            await query.message.edit_text(fj_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=fj_kb)
        except Exception:
            pass
