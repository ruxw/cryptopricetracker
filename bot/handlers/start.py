import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME
from bot.database import (
    register_private_start, is_user_verified, record_interaction,
    toggle_subscription, is_subscribed
)
from bot.middlewares.auth import get_verify_keyboard
from bot.services.force_join import check_user_joined_all, get_force_join_keyboard, get_force_join_message
from bot.emojis import E, coin_emoji, custom_btn

logger = logging.getLogger(__name__)

def make_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Generate aesthetic minimal inline keyboard for /start with custom emoji icons."""
    return InlineKeyboardMarkup([
        [custom_btn("Add bot to chat ↗", url=f"https://t.me/{bot_username}?startgroup=start", icon="group")],
        [custom_btn("View Help Menu", callback_data="help:menu", icon="help")]
    ])

def get_clean_help_text(bot_username: str) -> str:
    """
    Return clean formatted help menu text without code tags around commands,
    with custom emojis, and including all new commands (/daily, /meme).
    """
    return (
        f"{E('currencing')} <b>@{bot_username} Commands</b>\n\n"
        f"{E('chart')} <b>Prices & Charts:</b>\n"
        f"• /top — Top cryptos at a glance\n"
        f"• /crypto &lt;coin&gt; — Live price card for any coin\n"
        f"• /btc, /eth, /sol, /bnb — Ticker shortcuts\n"
        f"• /ath &lt;coin&gt; — All-time high for any coin\n"
        f"• /convert 0.5 btc — Crypto to USD conversion\n"
        f"• /convert $50 to sol — USD to crypto conversion\n\n"
        f"{E('meme')} <b>Fun & Meme Commands:</b>\n"
        f"• /daily — Daily crypto thought & philosophical quote\n"
        f"• /meme — Daily fun crypto meme & degen truth\n"
        f"• /satoshi — Historical quotes from Satoshi Nakamoto\n"
        f"• /cope &lt;coin&gt; — Could be worse — vs the all-time low\n"
        f"• /panic &lt;coin&gt; — Emergency panic index & calming checklist\n"
        f"• /wagmi — Today's top rocket market gainers\n"
        f"• /predict &lt;coin&gt; — Technical price target prediction\n"
        f"• /dyk, /didyouknow &lt;coin&gt; — Interesting crypto history and trivia\n"
        f"• /me — Your personal usage intelligence recap\n"
        f"• /firstseen &lt;coin&gt; — Price change since you first checked\n"
        f"• /lookup &lt;coin&gt; — Your last check vs the price now\n"
        f"• /chatvibe — This chat's most-checked coins"
    )

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
        if len(args) > 0 and args[0].lower().startswith("sub_"):
            raw_sym = args[0][4:].upper()
            sym = "GRAM" if raw_sym in ("TON", "GRAM") else raw_sym
            sym_cmd = "gram" if sym == "GRAM" else sym.lower()

            already_subbed = await is_subscribed(user.id, sym)
            if not already_subbed:
                await toggle_subscription(user.id, sym)
                greeting = (
                    f"{E('check')} <b>Subscribed to {sym} Daily Insights!</b>\n\n"
                    f"You have subscribed for daily insights of <b>{sym}</b>. "
                    f"You will receive daily rate cards and price insights directly in this chat.\n\n"
                    f"<i>Whenever you want to unsubscribe, type /unsub {sym_cmd} or tap the unsub button on your daily card.</i>"
                )
            else:
                await toggle_subscription(user.id, sym)
                greeting = (
                    f"🔕 <b>Unsubscribed from {sym} Daily Insights.</b>\n\n"
                    f"Whenever you want to subscribe again for daily insights, just type <code>/sub {sym_cmd}</code> and all set!"
                )
        elif len(args) > 0 and args[0].lower().startswith("unsub_"):
            raw_sym = args[0][6:].upper()
            sym = "GRAM" if raw_sym in ("TON", "GRAM") else raw_sym
            sym_cmd = "gram" if sym == "GRAM" else sym.lower()

            already_subbed = await is_subscribed(user.id, sym)
            if already_subbed:
                await toggle_subscription(user.id, sym)
            greeting = (
                f"🔕 <b>Unsubscribed from {sym} Daily Insights.</b>\n\n"
                f"Whenever you want to subscribe again for daily insights, just type <code>/sub {sym_cmd}</code> and all set!"
            )
        elif is_deep_link_verify:
            greeting = (
                f"{E('check')} <b>Verified, {user.first_name}!</b>\n\n"
                f"Hey <b>{user_tag}</b>, you can now use Currencing everywhere — in private chats and in groups."
            )
        else:
            greeting = (
                f"Hey <b>{user_tag}</b>,\n\n"
                f"{E('currencing')} <b>@{bot_username}</b>\n"
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
            f"• /top — Top cryptos at a glance\n"
            f"• /btc, /eth, /sol, /bnb\n"
            f"• /convert 100 usd btc\n"
            f"• /daily — Daily crypto thought\n"
            f"• /meme — Daily fun crypto meme\n"
            f"• /ath sol\n"
            f"• /chatvibe — Chat's top checked coins"
        )
        await update.message.reply_text(
            group_msg,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with permanent message (no self-delete) and clean formatting."""
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

    help_text = get_clean_help_text(bot_username)

    # Sent directly without the self-deleting footer
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_msg_id,
        disable_web_page_preview=True
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
    help_text = get_clean_help_text(bot_username)

    back_kb = InlineKeyboardMarkup([
        [custom_btn("Add bot to chat ↗", url=f"https://t.me/{bot_username}?startgroup=start", icon="group")]
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
            f"{E('check')} <b>Access Granted, {user.first_name}!</b>\n\n"
            "All features are unlocked! Track live markets, 7-day charts, and instant conversions.\n\n"
            "Type /top or /btc to get started!"
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
