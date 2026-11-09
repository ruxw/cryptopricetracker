import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME
from bot.database import register_private_start, is_user_verified, record_interaction
from bot.middlewares.auth import get_verify_keyboard
from bot.services.force_join import check_user_joined_all, get_force_join_keyboard, get_force_join_message

logger = logging.getLogger(__name__)

def get_main_menu_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Clean minimal main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("Market Overview", callback_data="nav_overview"),
            InlineKeyboardButton("All-Time Highs", callback_data="nav_ath_menu"),
        ],
        [
            InlineKeyboardButton("Crypto Converter", callback_data="nav_convert_menu"),
            InlineKeyboardButton("Help", callback_data="nav_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command in private and group chats."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    bot_username = context.bot.username or BOT_USERNAME
    args = context.args or []
    is_deep_link_verify = len(args) > 0 and args[0].lower() == "verify"

    if chat.type == ChatType.PRIVATE:
        # Register and verify user in persistent SQLite database
        await register_private_start(user.id, user.username, user.first_name)
        await record_interaction(user.id, "start", " ".join(args))

        if is_deep_link_verify:
            greeting = (
                f"✅ **Verified, {user.first_name}!**\n\n"
                "You can now use Currencing everywhere — in private and in groups."
            )
        else:
            greeting = (
                f"**Currencing** — Crypto prices, charts & conversions.\n\n"
                f"Hi {user.first_name}! Choose a feature or type a command.\n\n"
                f"`/btc` `/eth` `/sol` `/top` `/ath btc` `/convert 0.5 btc`"
            )

        kb = get_main_menu_keyboard(bot_username)
        await update.message.reply_text(greeting, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

    else:
        # Command received in a group chat
        verified = await is_user_verified(user.id)
        if not verified:
            kb = get_verify_keyboard(bot_username)
            await update.message.reply_text(
                "Please start me in private first to unlock all features! ❤️",
                reply_markup=kb
            )
            return

        await record_interaction(user.id, "group_start")
        group_msg = (
            f"⚡ **Currencing in Groups**\n\n"
            f"Invoke anywhere via `@`:\n"
            f"• `@{bot_username}` — Market overview\n"
            f"• `@{bot_username} btc` — Bitcoin live chart\n"
            f"• `@{bot_username} 0.3 ltc` — Convert 0.3 LTC to USD\n"
            f"• `@{bot_username} ath eth` — Ethereum ATH"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View Market Overview", callback_data="nav_overview")],
            [InlineKeyboardButton("🔎 Try Inline Now", switch_inline_query_current_chat="")]
        ])
        await update.message.reply_text(group_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    user = update.effective_user
    if not user:
        return

    verified = await is_user_verified(user.id)
    bot_username = context.bot.username or BOT_USERNAME

    if not verified:
        kb = get_verify_keyboard(bot_username)
        await update.message.reply_text(
            "Please start me in private first to unlock all features! ❤️",
            reply_markup=kb
        )
        return

    help_text = (
        "**Currencing — Commands**\n\n"
        "**Top Coins**\n"
        "`/btc` `/eth` `/sol` `/bnb` `/xrp` `/ada` `/avax` `/ton` `/trx` `/ltc` `/xmr`\n\n"
        "**Meme Coins**\n"
        "`/doge` `/shib` `/pepe`\n\n"
        "**Market & Analytics**\n"
        "`/top` — 3×3 market overview\n"
        "`/crypto <coin>` — any coin by name or ticker\n"
        "`/ath <coin>` — all-time high record\n"
        "`/convert 0.5 btc` — 0.5 BTC in USD\n"
        "`/convert $100 eth` — how much ETH $100 buys\n\n"
        f"**Inline in groups:** `@{bot_username} btc`"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 3×3 Grid", callback_data="nav_overview"),
            InlineKeyboardButton("📈 Charts", callback_data="nav_stats_menu")
        ],
        [
            InlineKeyboardButton("💱 Converter", callback_data="nav_convert_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="nav_start")
        ]
    ])
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback to return to main menu."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    bot_username = context.bot.username or BOT_USERNAME
    text = (
        f"⚡ **Currencing — Crypto Intelligence & Statistics**\n\n"
        f"Welcome, **{user.first_name}**! Track live market data, 7-day price charts, "
        "ATH records, and instant conversions.\n\n"
        "👇 **Tap an option below:**"
    )
    kb = get_main_menu_keyboard(bot_username)
    await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def check_force_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user clicking '✅ I Have Joined' verification button."""
    query = update.callback_query
    user = update.effective_user
    if not user:
        return

    all_joined, missing = await check_user_joined_all(context.bot, user.id)
    if all_joined:
        await query.answer("✅ Verified! All required channels joined.", show_alert=True)
        bot_username = context.bot.username or BOT_USERNAME
        text = (
            f"🎉 **Access Granted, {user.first_name}!**\n\n"
            "All features are unlocked! You can now track live markets, view 7-day charts, and convert currencies.\n\n"
            "👇 **Tap an option below:**"
        )
        kb = get_main_menu_keyboard(bot_username)
        try:
            await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        await query.answer("❌ You still haven't joined all required channels! Please join them first.", show_alert=True)
        fj_msg = get_force_join_message()
        fj_kb = get_force_join_keyboard(missing)
        try:
            await query.message.edit_text(fj_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=fj_kb)
        except Exception:
            pass
