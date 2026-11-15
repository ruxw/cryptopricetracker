import logging
import os
import uuid
from typing import List, Optional
from telegram import (
    Update,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultsButton
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import BOT_USERNAME, UNVERIFIED_MESSAGE
from bot.database import is_user_verified, record_interaction, get_cached_card_file_id
from bot.services.crypto_api import crypto_service
from bot.services.force_join import check_user_joined_all, get_force_join_channels
from bot.graphics.assets import COINS, FIAT_CURRENCIES, format_price, format_change
from bot.middlewares.auth import get_start_deep_link
from bot.emojis import E, coin_emoji, custom_btn

logger = logging.getLogger(__name__)

async def build_coin_inline_card(
    coin_item: dict,
    bot_username: str,
    base_web_url: Optional[str] = None
):
    """
    Build a visual image card result for inline mode.
    Uses Telegram cached photo file_id or hosted card PNG if available,
    with custom emojis in caption and custom emoji icons in inline buttons.
    """
    sym = coin_item["symbol"].upper()
    price = coin_item.get("price") if "price" in coin_item else coin_item.get("current_price", 0.0)
    p_str = format_price(price, decimals=COINS.get(sym, {}).get("decimals", 2))
    chg_val = coin_item.get("change_24h", 0.0)
    chg_str = format_change(chg_val)
    name = COINS.get(sym, {}).get("name", sym)

    caption = (
        f"{coin_emoji(sym)} <b>{name} ({sym})</b>\n\n"
        f"• <b>Price:</b> ${p_str} USD\n"
        f"• <b>24h Change:</b> {chg_str}\n\n"
        f"{E('currencing')} <i>Powered by Currencing</i>"
    )

    kb = InlineKeyboardMarkup([
        [
            custom_btn(f"📈 {sym} 7-Day Chart", url=f"https://t.me/{bot_username}?start=stats_{sym}", coin=sym),
            custom_btn(f"🚀 {sym} ATH Record", url=f"https://t.me/{bot_username}?start=ath_{sym}", icon="ath")
        ]
    ])

    # 1. Prefer Telegram cached photo file_id
    cached_file_id = await get_cached_card_file_id(sym)
    if cached_file_id:
        return InlineQueryResultCachedPhoto(
            id=f"coin_{sym.lower()}_{uuid.uuid4().hex[:6]}",
            photo_file_id=cached_file_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )

    # 2. Prefer Render / public HTTP web service URL
    if base_web_url:
        card_url = f"{base_web_url.rstrip('/')}/card/{sym.lower()}.png"
        return InlineQueryResultPhoto(
            id=f"coin_{sym.lower()}_{uuid.uuid4().hex[:6]}",
            photo_url=card_url,
            thumbnail_url=card_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )

    # 3. Fallback to formatted article if neither cached file_id nor public URL is set
    return InlineQueryResultArticle(
        id=f"coin_{sym.lower()}_{uuid.uuid4().hex[:6]}",
        title=f"{name} ({sym}): ${p_str}",
        description=f"24h: {chg_str}",
        input_message_content=InputTextMessageContent(caption, parse_mode=ParseMode.HTML),
        reply_markup=kb
    )

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Telegram Group Guest Mode via Inline Queries.
    Delivers visual cards with custom emojis and action buttons.
    """
    inline_query = update.inline_query
    if not inline_query:
        return

    user = inline_query.from_user
    user_id = user.id
    query_text = inline_query.query.strip().lower()
    bot_username = context.bot.username or BOT_USERNAME
    base_web_url = os.getenv("RENDER_EXTERNAL_URL", os.getenv("BASE_WEB_URL"))

    # MANDATORY VERIFICATION CHECK
    verified = await is_user_verified(user_id)
    if not verified:
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
                UNVERIFIED_MESSAGE,
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=InlineKeyboardMarkup([
                [custom_btn("🚀 Start in Private (Unlock Features)", url=deep_link, icon="gem")]
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
                [custom_btn("📢 Join Channels in Private", url=get_start_deep_link(bot_username), icon="group")]
            ])
        )
        await inline_query.answer([join_article], button=button, cache_time=5, is_personal=True)
        return

    await record_interaction(user_id, "inline_query", query_text)

    results = []

    # 1. Check if query is a conversion request (e.g. "0.3 ltc", "100 sol", "conv 5 eth eur")
    conv_parts = query_text.replace("conv", "").strip().split()
    if len(conv_parts) >= 2:
        try:
            amt = float(conv_parts[0])
            crypto_sym = conv_parts[1].upper()
            fiat_sym = conv_parts[2].upper() if len(conv_parts) > 2 else "USD"
            if crypto_sym in COINS and fiat_sym in FIAT_CURRENCIES:
                res = await crypto_service.convert(crypto_sym, amt, fiat_sym)
                fiat_info = FIAT_CURRENCIES[fiat_sym]
                f_val = f"{fiat_info['symbol']}{format_price(res['fiat_value'], decimals=fiat_info['decimals'])}"
                coin_name = COINS[crypto_sym]["name"]

                msg_text = (
                    f"{E('convert')} <b>Currencing Live Conversion</b>\n\n"
                    f"• <b>Asset:</b> {amt} {coin_name} ({crypto_sym})\n"
                    f"• <b>Value:</b> {f_val} {fiat_sym}\n"
                    f"• <b>Rate:</b> 1 {crypto_sym} = ${format_price(res['usd_price'])} USD\n\n"
                    f"{E('currencing')} <i>Powered by Currencing Market Intelligence</i>"
                )
                kb = InlineKeyboardMarkup([
                    [custom_btn(f"📈 {crypto_sym} Stats", url=f"https://t.me/{bot_username}?start=stats_{crypto_sym}", coin=crypto_sym)],
                    [custom_btn("📊 Full Market Overview", url=f"https://t.me/{bot_username}?start=overview", icon="chart")]
                ])

                results.append(InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"Convert: {amt} {crypto_sym} = {f_val} {fiat_sym}",
                    description=f"Rate: 1 {crypto_sym} = ${format_price(res['usd_price'])} USD",
                    input_message_content=InputTextMessageContent(msg_text, parse_mode=ParseMode.HTML),
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

            caption = (
                f"{E('ath')} <b>All-Time High: {name} ({sym})</b>\n\n"
                f"• <b>Record High:</b> ${p_str} USD\n"
                f"• <b>Recorded Date:</b> {ath_d[:10]}\n\n"
                f"{E('currencing')} <i>Official record tracked by Currencing</i>"
            )
            kb = InlineKeyboardMarkup([
                [custom_btn(f"📈 View {sym} 7-Day Chart", url=f"https://t.me/{bot_username}?start=stats_{sym}", coin=sym)]
            ])

            cached_ath = await get_cached_card_file_id(f"ath_{sym.lower()}")
            if cached_ath:
                results.append(InlineQueryResultCachedPhoto(
                    id=f"ath_{sym.lower()}_{uuid.uuid4().hex[:6]}",
                    photo_file_id=cached_ath,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb
                ))
            else:
                results.append(InlineQueryResultArticle(
                    id=f"ath_{sym.lower()}_{uuid.uuid4().hex[:6]}",
                    title=f"🚀 {name} ({sym}) ATH: ${p_str}",
                    description=f"Recorded: {ath_d[:10]}",
                    input_message_content=InputTextMessageContent(caption, parse_mode=ParseMode.HTML),
                    reply_markup=kb
                ))

    # 3. Specific Coin Query (e.g. "btc", "eth", "sol", "gram")
    upper_query = query_text.upper()
    if upper_query in COINS:
        coin = await crypto_service.get_coin_data(upper_query)
        card_res = await build_coin_inline_card(coin, bot_username, base_web_url)
        results.append(card_res)

    # 4. Default Results: Market Overview Card & Top Coin Items
    if not results:
        # A. Market Overview Card Result
        overview_data = await crypto_service.get_all_overview_data()
        cached_ov = await get_cached_card_file_id("overview")
        overview_lines = [
            f"• <b>{c['symbol']}:</b> ${format_price(c['price'])} ({format_change(c['change_24h'])})"
            for c in overview_data
        ]
        overview_caption = (
            f"{E('chart')} <b>Currencing Market Overview</b>\n\n" +
            "\n".join(overview_lines) +
            f"\n\n{E('currencing')} <i>Powered by Currencing Crypto Intelligence</i>"
        )
        kb_overview = InlineKeyboardMarkup([
            [custom_btn("📊 View Full 3×3 Grid Card", url=f"https://t.me/{bot_username}?start=overview", icon="chart")]
        ])

        if cached_ov:
            results.append(InlineQueryResultCachedPhoto(
                id=f"overview_{uuid.uuid4().hex[:6]}",
                photo_file_id=cached_ov,
                caption=overview_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb_overview
            ))
        else:
            results.append(InlineQueryResultArticle(
                id="overview_summary",
                title="📊 Currencing Market Overview (All Coins)",
                description="Live prices & 24h changes for top 9 cryptocurrencies",
                input_message_content=InputTextMessageContent(overview_caption, parse_mode=ParseMode.HTML),
                reply_markup=kb_overview
            ))

        # B. Individual Coin Visual Cards
        for coin_item in overview_data:
            c_res = await build_coin_inline_card(coin_item, bot_username, base_web_url)
            results.append(c_res)

    await inline_query.answer(results[:15], cache_time=10, is_personal=True)
