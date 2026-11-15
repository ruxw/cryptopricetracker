import logging
from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME
from bot.database import register_private_start, is_user_verified, record_interaction
from bot.middlewares.auth import get_verify_keyboard
from bot.services.force_join import check_user_joined_all, get_force_join_keyboard, get_force_join_message
from bot.services.ephemeral import send_ephemeral
from bot.emojis import E, coin_emoji

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with clean button-free modern interface."""
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

        if is_deep_link_verify:
            greeting = (
                f"{E('check')} <b>Verified, {user.first_name}!</b>\n\n"
                "You can now use Currencing everywhere — in private and in groups."
            )
        else:
            greeting = (
                f"{E('fire')} <b>Currencing</b> — Ultra-Fast Crypto Intelligence\n\n"
                f"Welcome, <b>{user.first_name}</b>!\n\n"
                f"<b>Top Commands:</b>\n"
                f"• <code>/top</code> — Top 9 crypto market overview\n"
                f"• <code>/btc</code> {coin_emoji('BTC')}, <code>/eth</code> {coin_emoji('ETH')}, <code>/sol</code> {coin_emoji('SOL')}\n"
                f"• <code>/convert $50 to sol</code> {E('convert')}\n"
                f"• <code>/ath btc</code> {E('ath')}\n"
                f"• <code>/help</code> — Full command list"
            )

        await update.message.reply_text(
            greeting,
            parse_mode=ParseMode.HTML,
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
            f"• <code>/ath sol</code>"
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
        f"{E('help')} <b>Currencing — Command Menu</b>\n\n"
        f"<b>Market Overview:</b>\n"
        f"• <code>/top</code> — Top 9 crypto cards (as in Image 5)\n\n"
        f"<b>Instant Price & 7-Day Chart:</b>\n"
        f"• <code>/btc</code> {coin_emoji('BTC')} Bitcoin\n"
        f"• <code>/eth</code> {coin_emoji('ETH')} Ethereum\n"
        f"• <code>/sol</code> {coin_emoji('SOL')} Solana\n"
        f"• <code>/ton</code> {coin_emoji('GRAM')} Gram / TON\n"
        f"• <code>/bnb</code> {coin_emoji('BNB')} BNB\n"
        f"• <code>/xrp</code> {coin_emoji('XRP')} XRP\n"
        f"• <code>/ltc</code> {coin_emoji('LTC')} Litecoin\n"
        f"• <code>/xmr</code> {coin_emoji('XMR')} Monero\n"
        f"• <code>/trx</code> {coin_emoji('TRX')} Tron\n"
        f"• <code>/doge</code> {coin_emoji('DOGE')} Dogecoin\n"
        f"• <code>/shib</code> {coin_emoji('SHIB')} Shiba Inu\n"
        f"• <code>/pepe</code> {coin_emoji('PEPE')} Pepe\n\n"
        f"<b>AI Natural Currency Converter:</b>\n"
        f"• <code>/convert $50 to sol</code>\n"
        f"• <code>/convert 100 usd btc</code>\n"
        f"• <code>/convert 0.5 btc in eur</code>\n"
        f"• <code>/convert 2 eth to usd</code>\n"
        f"• <code>/convert 1000 doge</code>\n\n"
        f"<b>All-Time High (ATH):</b>\n"
        f"• <code>/ath &lt;coin&gt;</code> (e.g. <code>/ath btc</code>, <code>/ath sol</code>)\n\n"
        f"<b>Any Coin Search:</b>\n"
        f"• <code>/crypto &lt;coin&gt;</code>"
    )

    # Send as ephemeral self-deleting message (auto-deletes in 45s to keep chat pristine)
    await send_ephemeral(
        bot=context.bot,
        chat_id=chat.id,
        text=help_text,
        auto_delete_seconds=45,
        reply_to_message_id=reply_msg_id
    )

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback to return to main menu."""
    query = update.callback_query
    await query.answer()
    if update.effective_chat:
        await help_command(update, context)

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
