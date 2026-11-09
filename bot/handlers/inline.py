import logging
import uuid
from typing import List
from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultsButton
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME, UNVERIFIED_MESSAGE
from bot.database import is_user_verified, record_interaction
from bot.services.crypto_api import crypto_service
from bot.services.force_join import check_user_joined_all, get_force_join_channels
from bot.graphics.assets import COINS, FIAT_CURRENCIES, format_price, format_change
from bot.middlewares.auth import get_start_deep_link

logger = logging.getLogger(__name__)

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Telegram Group Guest Mode via Inline Queries.
    Enables invoking @BotUsername anywhere without adding the bot as a member or admin!
    Strictly verifies private /start authorization in SQLite DB on every single query.
    """
    inline_query = update.inline_query
    if not inline_query:
        return

    user = inline_query.from_user
    user_id = user.id
    query_text = inline_query.query.strip().lower()
    bot_username = context.bot.username or BOT_USERNAME

    # MANDATORY VERIFICATION CHECK
    verified = await is_user_verified(user_id)
    if not verified:
        # User has NOT started the bot privately!
        # Return switch_pm button AND an unverified article result with deep link
        deep_link = get_start_deep_link(bot_username)
        button = InlineQueryResultsButton(
            text="Please start me in private first to unlock all features! ❤️",
            start_parameter="verify"
        )
        unverified_article = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="⚠️ Private Verification Required",
            description="Please start me in private first to unlock all features! ❤️",
            input_message_content=InputTextMessageContent(
                message_text=UNVERIFIED_MESSAGE,
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start in Private (Unlock Features)", url=deep_link)]
            ])
        )
        await inline_query.answer([unverified_article], button=button, cache_time=5, is_personal=True)
        return

    # Check Force-Join Channels
    all_joined, missing = await check_user_joined_all(context.bot, user_id)
    if not all_joined:
        button = InlineQueryResultsButton(
            text="Please join our official channels first! 📢",
            start_parameter="verify"
        )
        ch_names = ", ".join([ch["name"] for ch in missing])
        join_article = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="⚠️ Channel Subscription Required",
            description=f"Please join: {ch_names}",
            input_message_content=InputTextMessageContent(
                "⚠️ **Channel Subscription Required**\n\n"
                "To unlock live crypto prices and charts in Currencing, please join our official channels!",
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channels in Private", url=get_start_deep_link(bot_username))]
            ])
        )
        await inline_query.answer([join_article], button=button, cache_time=5, is_personal=True)
        return

    # User IS verified! Record query activity
    await record_interaction(user_id, "inline_query", query_text)

    results: List[InlineQueryResultArticle] = []

    # 1. Check if query is a conversion request (e.g. "0.3 ltc", "100 sol", "conv 5 eth eur")
    conv_parts = query_text.replace("conv", "").strip().split()
    is_conv = False
    if len(conv_parts) >= 2:
        try:
            amt = float(conv_parts[0])
            crypto_sym = conv_parts[1].upper()
            fiat_sym = conv_parts[2].upper() if len(conv_parts) > 2 else "USD"
            if crypto_sym in COINS and fiat_sym in FIAT_CURRENCIES:
                is_conv = True
                res = await crypto_service.convert(crypto_sym, amt, fiat_sym)
                fiat_info = FIAT_CURRENCIES[fiat_sym]
                f_val = f"{fiat_info['symbol']}{format_price(res['fiat_value'], decimals=fiat_info['decimals'])}"
                coin_name = COINS[crypto_sym]["name"]

                msg_text = (
                    f"💱 **Currencing Live Conversion**\n\n"
                    f"• **Asset:** `{amt} {coin_name} ({crypto_sym})`\n"
                    f"• **Value:** `{f_val} {fiat_sym}`\n"
                    f"• **Rate:** `1 {crypto_sym} = ${format_price(res['usd_price'])} USD`\n\n"
                    f"⚡ _Powered by Currencing Market Intelligence_"
                )
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"📈 {crypto_sym} Stats", url=f"https://t.me/{bot_username}?start=stats_{crypto_sym}")],
                    [InlineKeyboardButton("📊 Full Market Overview", url=f"https://t.me/{bot_username}?start=overview")]
                ])

                results.append(InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"Convert: {amt} {crypto_sym} = {f_val} {fiat_sym}",
                    description=f"Rate: 1 {crypto_sym} = ${format_price(res['usd_price'])} USD",
                    input_message_content=InputTextMessageContent(msg_text, parse_mode=ParseMode.MARKDOWN),
                    reply_markup=kb
                ))
        except Exception:
            pass

    # 2. Check if query is an ATH request (e.g. "ath btc", "ath eth")
    if query_text.startswith("ath"):
        parts = query_text.split()
        sym = parts[1].upper() if len(parts) > 1 else "BTC"
        if sym in COINS:
            coin = await crypto_service.get_coin_data(sym)
            ath_p = coin.get("ath", 0.0)
            ath_d = coin.get("ath_date", "")
            p_str = format_price(ath_p, decimals=COINS[sym]["decimals"])
            name = COINS[sym]["name"]

            msg_text = (
                f"🚀 **Currencing All-Time High Record**\n\n"
                f"• **Asset:** `{name} ({sym})`\n"
                f"• **All-Time High:** `${p_str} USD`\n"
                f"• **Recorded Date:** `{ath_d[:10]}`\n\n"
                f"⚡ _Official record tracked by Currencing_"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📈 View {sym} 7-Day Chart", url=f"https://t.me/{bot_username}?start=stats_{sym}")]
            ])
            results.append(InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"🚀 {name} ({sym}) ATH: ${p_str}",
                description=f"Recorded: {ath_d[:10]}",
                input_message_content=InputTextMessageContent(msg_text, parse_mode=ParseMode.MARKDOWN),
                reply_markup=kb
            ))

    # 3. Specific Coin Query (e.g. "btc", "eth", "sol")
    upper_query = query_text.upper()
    if upper_query in COINS:
        coin = await crypto_service.get_coin_data(upper_query)
        p_str = format_price(coin["current_price"], decimals=COINS[upper_query]["decimals"])
        d_str = format_change(coin["change_24h"])
        w_str = format_change(coin["change_7d"])
        name = COINS[upper_query]["name"]

        msg_text = (
            f"📈 **Currencing Live Stats: {name} ({upper_query})**\n\n"
            f"• **Current Price:** `${p_str} USD`\n"
            f"• **24h Daily Change:** `{d_str}`\n"
            f"• **7d Weekly Change:** `{w_str}`\n\n"
            f"⚡ _Powered by Currencing Crypto Intelligence_"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📈 Open {upper_query} Chart Card", url=f"https://t.me/{bot_username}?start=stats_{upper_query}")],
            [InlineKeyboardButton(f"🚀 {upper_query} All-Time High", url=f"https://t.me/{bot_username}?start=ath_{upper_query}")]
        ])
        results.append(InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"{name} ({upper_query}): ${p_str} ({d_str})",
            description=f"24h: {d_str} | 7d: {w_str}",
            input_message_content=InputTextMessageContent(msg_text, parse_mode=ParseMode.MARKDOWN),
            reply_markup=kb
        ))

    # 4. Default Results: Market Overview & Coin List
    if not results:
        # A. Market Overview Result
        overview_data = await crypto_service.get_all_overview_data()
        overview_lines = [
            f"• **{c['symbol']}:** `${format_price(c['price'])}` ({format_change(c['change_24h'])})"
            for c in overview_data
        ]
        overview_msg = (
            "📊 **Currencing Market Overview**\n"
            "Live snapshot of major tracked assets:\n\n" +
            "\n".join(overview_lines) +
            "\n\n⚡ _Powered by Currencing Crypto Intelligence_"
        )
        kb_overview = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View Full 3×3 Grid Card", url=f"https://t.me/{bot_username}?start=overview")]
        ])
        results.append(InlineQueryResultArticle(
            id="overview_summary",
            title="📊 Currencing Market Overview (All Coins)",
            description="Live prices & 24h changes for BTC, ETH, SOL, GRAM, LTC, XMR, XRP, BNB, TRX",
            input_message_content=InputTextMessageContent(overview_msg, parse_mode=ParseMode.MARKDOWN),
            reply_markup=kb_overview
        ))

        # B. Individual Coin Items
        for coin_item in overview_data:
            sym = coin_item["symbol"]
            p_str = format_price(coin_item["price"], decimals=COINS[sym]["decimals"])
            chg_str = format_change(coin_item["change_24h"])
            name = coin_item["name"]

            c_text = (
                f"📈 **{name} ({sym})**\n\n"
                f"• **Price:** `${p_str} USD`\n"
                f"• **24h Change:** `{chg_str}`\n\n"
                f"⚡ _Powered by Currencing_"
            )
            kb_c = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📈 {sym} 7-Day Chart", url=f"https://t.me/{bot_username}?start=stats_{sym}")],
                [InlineKeyboardButton(f"🚀 {sym} ATH Record", url=f"https://t.me/{bot_username}?start=ath_{sym}")]
            ])
            results.append(InlineQueryResultArticle(
                id=f"coin_{sym.lower()}",
                title=f"{name} ({sym}): ${p_str}",
                description=f"24h Change: {chg_str}",
                input_message_content=InputTextMessageContent(c_text, parse_mode=ParseMode.MARKDOWN),
                reply_markup=kb_c
            ))

    await inline_query.answer(results[:15], cache_time=10, is_personal=True)
