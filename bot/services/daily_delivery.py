"""
Daily DM Delivery Service for Currencing Bot
============================================
Handles automatic daily direct messages to bot users:
1. Daily thought / quote & meme card
2. Daily price digest for user's subscribed currencies
3. Safe error handling (detects blocked bots and updates user active status)
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import List
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError

from bot.config import BOT_USERNAME
from bot.database import (
    get_eligible_daily_users, record_daily_delivery,
    get_all_subscriptions_by_user, get_user_subscriptions
)
from bot.services.crypto_api import crypto_service
from bot.services.cache_manager import get_cached_or_render
from bot.graphics.templates import render_daily_quote, render_meme_card, render_coin_stats
from bot.graphics.assets import format_price, format_change
from bot.emojis import E, coin_emoji
from bot.handlers.crypto import make_crypto_card_keyboard

logger = logging.getLogger(__name__)

async def deliver_daily_to_user(bot: Bot, user_id: int, today_str: str) -> None:
    """Deliver daily thought or meme card to a single user in DM."""
    from bot.handlers.meme import DAILY_THOUGHTS, MEME_VAULT

    try:
        # Alternates or chooses between daily thought and funny meme
        choose_quote = (hash(f"{user_id}_{today_str}") % 2 == 0)
        today_date = datetime.utcnow().strftime("%d/%m")

        if choose_quote:
            quote_item = random.choice(DAILY_THOUGHTS)
            quote, author, source = quote_item[0], quote_item[1], quote_item[2]
            image_buf = render_daily_quote(quote, author, source)
            caption = (
                f"{E('currencing')} <b>Daily Thoughts · {today_date}</b>\n"
                f"via @{BOT_USERNAME}. Tap /meme or /top for more."
            )
        else:
            meme_item = random.choice(MEME_VAULT)
            title, body, punchline = meme_item[0], meme_item[1], meme_item[2]
            coin_sym = meme_item[3] if len(meme_item) > 3 else "DOGE"
            image_buf = render_meme_card(title, body, punchline, coin_symbol=coin_sym)
            caption = (
                f"{E('meme')} <b>Daily Degen Lore · {today_date}</b>\n"
                f"via @{BOT_USERNAME}. Tap /meme or /top for more."
            )

        await bot.send_photo(
            chat_id=user_id,
            photo=image_buf,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        await record_daily_delivery(user_id, today_str, "daily_content")
        logger.info("Delivered daily content card to user %d", user_id)

    except Forbidden:
        logger.info("User %d blocked bot, marking inactive", user_id)
        try:
            import aiosqlite
            from bot.config import DB_PATH
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
                await db.commit()
        except Exception:
            pass
    except Exception as e:
        logger.warning("Could not deliver daily card to user %d: %s", user_id, e)

async def deliver_subscription_rates_to_user(bot: Bot, user_id: int, symbols: List[str], today_str: str) -> None:
    """Deliver daily rate updates for user's subscribed currencies in DM using visual cards."""
    if not symbols:
        return

    date_str = datetime.utcnow().strftime("%d/%m")

    try:
        sent_any = False
        for raw_sym in symbols:
            sym = raw_sym.upper()
            if sym == "TON":
                sym = "GRAM"

            try:
                data = await crypto_service.get_coin_data(sym)
                price = data["current_price"]
                p_str = format_price(price, decimals=2)
                chg_24 = data["change_24h"]
                chg_7 = data["change_7d"]
                sparkline = data["sparkline"]

                image_buf = await get_cached_or_render(
                    render_coin_stats,
                    sym,
                    price,
                    chg_24,
                    chg_7,
                    sparkline,
                    ttl=15.0
                )

                cmd_name = "gram" if sym in ("GRAM", "TON") else sym.lower()
                caption = (
                    f"{coin_emoji(sym)} <b>{sym}:</b> ${p_str} USD · {date_str}\n"
                    f"Use /{cmd_name} for 7d Chart"
                )

                card_kb = await make_crypto_card_keyboard(
                    sym,
                    user_id=user_id,
                    is_group=False,
                    bot_username=BOT_USERNAME
                )

                await bot.send_photo(
                    chat_id=user_id,
                    photo=image_buf,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=card_kb
                )
                sent_any = True
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning("Could not render/deliver card for %s to user %d: %s", sym, user_id, e)

        if sent_any:
            await record_daily_delivery(user_id, today_str, "currency_rates")
            logger.info("Delivered subscription rate cards to user %d for %s", user_id, symbols)

    except Forbidden:
        logger.info("User %d blocked bot, marking inactive", user_id)
    except Exception as e:
        logger.warning("Could not deliver subscriptions to user %d: %s", user_id, e)

async def run_daily_delivery_cycle(bot: Bot) -> None:
    """Execute one scan and delivery pass for eligible users."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Deliver daily thought / meme to verified users
    eligible_users = await get_eligible_daily_users(today_str, "daily_content")
    for uid in eligible_users:
        await deliver_daily_to_user(bot, uid, today_str)
        await asyncio.sleep(0.08)  # Gentle rate limiting

    # 2. Deliver subscribed currency rates
    all_subs = await get_all_subscriptions_by_user()
    for uid, symbols in all_subs.items():
        # Check if already sent today
        import aiosqlite
        from bot.config import DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM daily_deliveries WHERE user_id = ? AND delivery_date = ? AND delivery_type = 'currency_rates'",
                (uid, today_str)
            ) as cur:
                if await cur.fetchone():
                    continue

        await deliver_subscription_rates_to_user(bot, uid, symbols, today_str)
        await asyncio.sleep(0.08)

async def background_daily_delivery_task(bot: Bot) -> None:
    """Continuous background worker that checks and triggers daily DM deliveries."""
    logger.info("Starting background daily DM delivery task...")
    # Initial pause on bot boot before beginning deliveries
    await asyncio.sleep(15)
    while True:
        try:
            await run_daily_delivery_cycle(bot)
        except Exception as e:
            logger.error("Error in daily delivery cycle: %s", e)
        # Check every hour
        await asyncio.sleep(3600)
