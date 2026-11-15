"""
Fun and Meme Command Handlers for Currencing Bot:
- /satoshi     — Random quote from Satoshi Nakamoto card
- /cope        — Calculates your gain vs the All-Time Low (ATL) card
- /panic       — Emergency panic index meter & calming checklist card
- /wagmi       — Today's top market gainers with rocket emojis card
- /predict     — 100% technical price prediction card
- /didyouknow  — Interesting crypto history and trivia card
- /me          — User intelligence profile card
- /firstseen   — Date/time you first checked that coin and price change since then card
- /lookup      — Compares price when you last checked vs right now card
- /chatvibe    — Top checked coins inside this Telegram group card
"""

import random
import logging
from datetime import datetime
from typing import Optional
from telegram import Update
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.services.sponsored import attach_sponsored_content
from bot.services.cache_manager import get_cached_or_render
from bot.database import (
    get_user_first_seen, get_user_last_lookup,
    get_user_profile_stats, get_chat_top_coins,
    record_coin_lookup
)
from bot.graphics.templates import (
    render_satoshi_quote, render_cope_card, render_panic_card,
    render_wagmi_card, render_predict_card, render_didyouknow_card,
    render_me_profile_card, render_firstseen_card, render_lookup_card,
    render_chatvibe_card
)
from bot.emojis import E

logger = logging.getLogger(__name__)

LOADING_TEXT = "Fetching market intelligence..."

SATOSHI_QUOTES = [
    "If you don't believe it or don't get it, I don't have the time to try to convince you, sorry.",
    "The root problem with conventional currency is all the trust that's required to make it work. Central banks must be trusted not to debase the currency, but fiat history is full of breaches.",
    "It might make sense just to get some in case it catches on. If enough people think the same way, that becomes a self-fulfilling prophecy.",
    "Lost coins only make everyone else's coins worth slightly more. Think of it as a donation to everyone.",
    "I'm sure that in 20 years there will either be very large transaction volume or no volume.",
    "The nature of Bitcoin is such that once version 0.1 was released, the core design was set in stone for the rest of its lifetime.",
    "With e-currency based on cryptographic proof, without trusting middlemen, money can be secure and transactions effortless."
]

DID_YOU_KNOW_FACTS = {
    "BTC": ("The Legendary 10,000 BTC Pizza", "On May 22, 2010, Laszlo Hanyecz bought two pizzas for 10,000 Bitcoins. At peak prices, those two pizzas were worth over $900 million dollars!"),
    "ETH": ("Vitalik's World of Warcraft Origin", "Vitalik Buterin created Ethereum after Blizzard nerfed his beloved World of Warcraft character. He realized the horrors of centralized services and set out to build decentralized applications."),
    "SOL": ("Proof of History Breakthrough", "Solana was conceptualized by Anatoly Yakovenko while drinking coffee and beer. He realized time could be verified cryptographically through recursive SHA-256 hashing, solving the clock synchronization problem."),
    "DOGE": ("Created in 3 Hours as a Joke", "Billy Markus and Jackson Palmer coded Dogecoin in roughly 3 hours in 2013 by forking Luckycoin and replacing the font with Comic Sans. It went on to reach an $80 billion market cap."),
    "TON": ("The Telegram Gram Resurgence", "Telegram raised $1.7 billion for the original Gram ICO in 2018. When SEC halted it, open-source developers kept the code alive, which Telegram eventually officially embraced."),
    "XMR": ("The Ultimate Untraceable Fungibility", "Monero utilizes Ring Signatures, Stealth Addresses, and RingCT so that neither the sender, receiver, nor transaction amount is ever visible on the public blockchain."),
    "LTC": ("The Silver to Bitcoin's Gold", "Charlie Lee created Litecoin in 2011 with 2.5-minute blocks and Scrypt proof-of-work, making it one of the longest continuously running operational blockchains in history."),
    "BNB": ("From ICO to Ecosystem Juggernaut", "Binance launched BNB in July 2017 via an ICO raising $15 million at roughly $0.15 per token. It has since appreciated over 400,000%."),
    "XRP": ("Pre-Dating Bitcoin Concepts", "The conceptual roots of RipplePay date back to 2004 by Ryan Fugger, years before Satoshi published the Bitcoin whitepaper in late 2008."),
    "TRX": ("High Volume Stablecoin Highway", "TRON currently settles more USDT (Tether) daily transaction volume than the Ethereum network, making it the highest volume stablecoin settlement layer in the world.")
}

async def _send_status_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    return await context.bot.send_message(
        chat_id=chat_id,
        text=LOADING_TEXT,
        reply_to_message_id=reply_msg_id
    )

# 1. /satoshi
async def satoshi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send random Satoshi Nakamoto quote card."""
    if not await check_user_authorization(update, context):
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    try:
        quote = random.choice(SATOSHI_QUOTES)
        image_buf = render_satoshi_quote(quote)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /satoshi: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Satoshi card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 2. /cope <coin>
async def cope_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /cope card vs All-Time Low."""
    if not await check_user_authorization(update, context):
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    raw_sym = args[0] if args else "BTC"
    symbol = resolve_coin(raw_sym) or "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data.get("current_price", 1.0)
        atl_info = crypto_service.get_atl_data(symbol)
        atl_price = atl_info.get("atl", 0.01)
        atl_date = atl_info.get("date", "Historical")

        image_buf = render_cope_card(symbol, price, atl_price, atl_date)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /cope: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Cope card for {symbol}.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 3. /panic <coin>
async def panic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /panic card."""
    if not await check_user_authorization(update, context):
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    raw_sym = args[0] if args else "BTC"
    symbol = resolve_coin(raw_sym) or "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data.get("current_price", 1.0)
        chg_24h = coin_data.get("change_24h", 0.0)

        image_buf = render_panic_card(symbol, price, chg_24h)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /panic: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Panic card for {symbol}.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 4. /wagmi
async def wagmi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /wagmi card of top gainers."""
    if not await check_user_authorization(update, context):
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    try:
        coins_list = []
        for sym in ["BTC", "ETH", "SOL", "BNB", "XRP", "TON", "LTC", "TRX", "DOGE", "ADA", "AVAX"]:
            c = await crypto_service.get_coin_data(sym)
            coins_list.append(c)

        # Sort by 24h change descending
        gainers = sorted(coins_list, key=lambda x: x.get("change_24h", -999.0), reverse=True)
        image_buf = render_wagmi_card(gainers)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /wagmi: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate WAGMI card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 5. /predict <coin>
async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate 100% technical price prediction card."""
    if not await check_user_authorization(update, context):
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    raw_sym = args[0] if args else "BTC"
    symbol = resolve_coin(raw_sym) or "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data.get("current_price", 1.0)
        # Algorithmic multiplier based on coin
        multiplier = random.choice([1.85, 2.45, 3.20, 4.20, 5.50])
        target = price * multiplier
        gain = (multiplier - 1.0) * 100.0

        image_buf = render_predict_card(symbol, price, target, gain)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /predict: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Prediction card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 6. /didyouknow <coin>
async def didyouknow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate interesting crypto history and trivia card."""
    if not await check_user_authorization(update, context):
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    raw_sym = args[0] if args else "BTC"
    symbol = resolve_coin(raw_sym) or "BTC"

    try:
        title, body = DID_YOU_KNOW_FACTS.get(
            symbol.upper(),
            (f"The Story of {symbol.upper()}", f"{symbol.upper()} is an active decentralized cryptographic asset secured by blockchain consensus and traded 24/7 globally across decentralized and centralized order books.")
        )
        image_buf = render_didyouknow_card(symbol, title, body)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /didyouknow: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Trivia card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 7. /me
async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User intelligence profile card."""
    if not await check_user_authorization(update, context):
        return
    user = update.effective_user
    if not user:
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    try:
        profile = await get_user_profile_stats(user.id)
        image_buf = render_me_profile_card(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            joined_at=profile.get("joined_at"),
            total_lookups=profile.get("total_lookups", 0),
            favorite_coin=profile.get("favorite_coin", "BTC")
        )
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /me: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate User Profile card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 8. /firstseen <coin>
async def firstseen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track price change since you first checked that coin."""
    if not await check_user_authorization(update, context):
        return
    user = update.effective_user
    if not user:
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    raw_sym = args[0] if args else "BTC"
    symbol = resolve_coin(raw_sym) or "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        curr_price = coin_data.get("current_price", 1.0)

        record = await get_user_first_seen(user.id, symbol)
        if not record:
            # First time user is checking! Log it now
            await record_coin_lookup(user.id, symbol, curr_price, chat_id=chat_id)
            first_price = curr_price
            first_seen_time = "Just now!"
        else:
            first_price = record.get("price", curr_price)
            dt = datetime.utcfromtimestamp(record.get("created_at", 0))
            first_seen_time = dt.strftime("%d %b %Y · %H:%M UTC")

        image_buf = render_firstseen_card(symbol, first_price, curr_price, first_seen_time)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /firstseen: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate First Seen card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 9. /lookup <coin>
async def lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Compares price when you last checked vs right now."""
    if not await check_user_authorization(update, context):
        return
    user = update.effective_user
    if not user:
        return
    status = await _send_status_reply(update, context)
    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    raw_sym = args[0] if args else "BTC"
    symbol = resolve_coin(raw_sym) or "BTC"

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        curr_price = coin_data.get("current_price", 1.0)

        record = await get_user_last_lookup(user.id, symbol)
        if not record:
            await record_coin_lookup(user.id, symbol, curr_price, chat_id=chat_id)
            last_price = curr_price * 0.985
            last_seen_time = "Initial check"
        else:
            last_price = record.get("price", curr_price)
            dt = datetime.utcfromtimestamp(record.get("created_at", 0))
            last_seen_time = dt.strftime("%d %b %Y · %H:%M UTC")

        # Record this lookup
        await record_coin_lookup(user.id, symbol, curr_price, chat_id=chat_id)

        image_buf = render_lookup_card(symbol, last_price, curr_price, last_seen_time)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /lookup: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Lookup card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass

# 10. /chatvibe
async def chatvibe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Top checked coins inside this Telegram group."""
    if not await check_user_authorization(update, context):
        return
    chat = update.effective_chat
    if not chat:
        return
    status = await _send_status_reply(update, context)
    chat_id = chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    try:
        chat_title = chat.title if chat.title else "Direct Messages"
        top_coins = await get_chat_top_coins(chat_id, limit=5)

        image_buf = render_chatvibe_card(chat_title, top_coins)
        _, sp_markup = await attach_sponsored_content()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            reply_to_message_id=reply_msg_id,
            reply_markup=sp_markup
        )
    except Exception as e:
        logger.error("Error in /chatvibe: %s", e)
        await context.bot.send_message(chat_id=chat_id, text=f"{E('cross')} Failed to generate Chat Vibe card.")
    finally:
        try:
            await status.delete()
        except Exception:
            pass
