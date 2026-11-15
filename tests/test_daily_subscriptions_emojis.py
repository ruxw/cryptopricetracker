import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message, User, Chat, InlineKeyboardMarkup
from telegram.constants import ParseMode

from bot.emojis import E, coin_emoji, custom_btn, btn_icon, btn_coin_icon
from bot.database import (
    init_db, add_subscription, remove_subscription,
    is_subscribed, toggle_subscription, get_user_subscriptions,
    save_cached_card_file_id, get_cached_card_file_id
)
from bot.graphics.templates import render_daily_quote, render_meme_card, render_satoshi_quote
from bot.handlers.meme import DAILY_THOUGHTS, MEME_VAULT, SATOSHI_QUOTES
from bot.handlers.crypto import make_crypto_card_keyboard
from bot.handlers.inline import build_coin_inline_card

@pytest.mark.asyncio
async def test_custom_emojis_two_ways():
    """Verify that custom emojis work in 2 different ways: HTML text tags & button icon_custom_emoji_id."""
    # 1. In HTML text: <tg-emoji emoji-id="...">fallback</tg-emoji>
    btc_text = coin_emoji("BTC")
    assert "<tg-emoji" in btc_text
    assert 'emoji-id="5969756601567943062"' in btc_text

    brand_text = E("currencing")
    assert "<tg-emoji" in brand_text

    # 2. In InlineKeyboardButton: icon_custom_emoji_id attribute
    btn = custom_btn("BTC Live", callback_data="stats_BTC", coin="BTC")
    assert btn.text == "BTC Live"
    assert btn.callback_data == "stats_BTC"
    assert getattr(btn, "icon_custom_emoji_id", None) == "5969756601567943062"

    btn_bell = custom_btn("Subscribe", callback_data="sub:BTC", icon="bell")
    assert getattr(btn_bell, "icon_custom_emoji_id", None) == "5451732530048802485"

@pytest.mark.asyncio
async def test_subscriptions_and_cards():
    """Verify subscription toggle and card caching."""
    await init_db()
    uid = 998877

    # Initially not subscribed
    assert await is_subscribed(uid, "SOL") is False

    # Toggle to true
    now_sub = await toggle_subscription(uid, "SOL")
    assert now_sub is True
    assert await is_subscribed(uid, "SOL") is True
    assert "SOL" in await get_user_subscriptions(uid)

    # Toggle to false
    now_sub = await toggle_subscription(uid, "SOL")
    assert now_sub is False
    assert await is_subscribed(uid, "SOL") is False

    # Keyboard has subscribe column buttons
    kb = await make_crypto_card_keyboard("SOL", uid)
    assert len(kb.inline_keyboard) == 3
    assert "Subscribe to SOL" in kb.inline_keyboard[0][0].text

    # Cache file_id
    await save_cached_card_file_id("SOL", "FILE_ID_SOL_PHOTO")
    assert await get_cached_card_file_id("SOL") == "FILE_ID_SOL_PHOTO"

@pytest.mark.asyncio
async def test_fun_pools_and_templates():
    """Verify expanded pools for satoshi, daily, and meme and card generation."""
    assert len(SATOSHI_QUOTES) >= 30
    assert len(DAILY_THOUGHTS) >= 30
    assert len(MEME_VAULT) >= 30

    b1 = render_satoshi_quote(SATOSHI_QUOTES[0])
    assert len(b1.getvalue()) > 1000

    q, a, s = DAILY_THOUGHTS[0]
    b2 = render_daily_quote(q, a, s)
    assert len(b2.getvalue()) > 1000

    title, body, punch = MEME_VAULT[0]
    b3 = render_meme_card(title, body, punch)
    assert len(b3.getvalue()) > 1000

@pytest.mark.asyncio
async def test_inline_card_generation():
    """Verify inline query generates visual photo cards when file_id is available."""
    await init_db()
    await save_cached_card_file_id("BTC", "TELEGRAM_PHOTO_FILE_ID_123")

    coin_item = {"symbol": "BTC", "price": 95000.0, "change_24h": 3.5}
    res = await build_coin_inline_card(coin_item, "CurrencingBot")

    from telegram import InlineQueryResultCachedPhoto
    assert isinstance(res, InlineQueryResultCachedPhoto)
    assert res.photo_file_id == "TELEGRAM_PHOTO_FILE_ID_123"
    assert "Bitcoin" in res.caption
    assert "t.me/CurrencingBot" in res.reply_markup.inline_keyboard[0][0].url
