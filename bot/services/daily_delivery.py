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

from bot.database import (
    get_eligible_daily_users, record_daily_delivery,
    get_all_subscriptions_by_user, get_user_subscriptions
)
from bot.services.crypto_api import crypto_service
from bot.graphics.templates import render_daily_quote, render_meme_card
from bot.graphics.assets import format_price, format_change
from bot.emojis import E, coin_emoji

logger = logging.getLogger(__name__)

async def deliver_daily_to_user(bot: Bot, user_id: int, today_str: str) -> None:
    """Deliver daily thought or meme card to a single user in DM."""
    from bot.handlers.meme import DAILY_THOUGHTS, MEME_VAULT

    try:
        # Alternates or chooses between daily thought and funny meme
        choose_quote = (hash(f"{user_id}_{today_str}") % 2 == 0)

        if choose_quote:
            quote, author, source = random.choice(DAILY_THOUGHTS)
            image_buf = render_daily_quote(quote, author, source)
            caption = (
                f"{E('currencing')} <b>Daily Crypto Intelligence</b> · <i>{today_str}</i>\n\n"
                f"“{quote}”\n"
                f"— <b>{author}</b>\n\n"
                f"<i>Delivered daily by @CurrencingBot. Tap /daily or /top for more.</i>"
            )
        else:
            title, body, punchline = random.choice(MEME_VAULT)
            image_buf = render_meme_card(title, body, punchline)
            caption = (
                f"{E('meme')} <b>Daily Crypto Degen Lore</b> · <i>{today_str}</i>\n\n"
                f"<b>{title}</b>\n"
                f"{body}\n\n"
                f"👉 <b>{punchline}</b>\n\n"
                f"<i>Delivered daily by @CurrencingBot. Tap /meme or /top for more.</i>"
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
        # Deactivate user
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
    """Deliver daily rate updates for user's subscribed currencies in DM."""
    if not symbols:
        return

    try:
        lines = []
        for sym in symbols:
            try:
                data = await crypto_service.get_coin_data(sym)
                p_str = format_price(data["current_price"])
                chg_str = format_change(data["change_24h"])
                lines.append(f"• {coin_emoji(sym)} <b>{sym}:</b> ${p_str} USD ({chg_str})")
            except Exception:
                pass

        if not lines:
            return

        msg = (
            f"🔔 <b>Your Daily Subscribed Currency Rates</b> · <i>{today_str}</i>\n\n"
            + "\n".join(lines) +
            f"\n\n{E('currencing')} <i>Real-time intelligence from @CurrencingBot</i>\n"
            f"<i>Use /crypto &lt;symbol&gt; to view interactive 7-day charts.</i>"
        )

        await bot.send_message(
            chat_id=user_id,
            text=msg,
            parse_mode=ParseMode.HTML
        )
        await record_daily_delivery(user_id, today_str, "currency_rates")
        logger.info("Delivered subscription rates to user %d for %s", user_id, symbols)

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
