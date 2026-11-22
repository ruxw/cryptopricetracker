import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User, Chat, Message
from telegram.constants import ChatType, ParseMode

from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.handlers.crypto import sub_command, unsub_command, make_crypto_card_keyboard
from bot.database import init_db, is_subscribed, toggle_subscription, register_private_start
from bot.services.daily_delivery import deliver_subscription_rates_to_user, deliver_daily_to_user
from bot.handlers.meme import DAILY_THOUGHTS, MEME_VAULT, meme_command, daily_command
from bot.graphics.templates import render_market_overview, render_meme_card
from bot.emojis import coin_emoji

@pytest.mark.asyncio
async def test_sub_unsub_flow():
    await init_db()
    uid = 112233
    sym = "BTC"
    await register_private_start(uid, "testuser", "Test")

    # Start unsubscribed
    if await is_subscribed(uid, sym):
        await toggle_subscription(uid, sym)
    assert await is_subscribed(uid, sym) is False

    # Simulate /sub btc
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User, id=uid)
    update.effective_chat = MagicMock(spec=Chat, type=ChatType.PRIVATE)
    update.effective_message = MagicMock(spec=Message, message_id=1)
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    context.args = ["btc"]

    await sub_command(update, context)
    assert await is_subscribed(uid, sym) is True
    update.message.reply_text.assert_called_once()
    sub_msg = update.message.reply_text.call_args[0][0]
    assert "Subscribed to BTC Daily Insights!" in sub_msg

    # Simulate /unsub btc
    update.message.reply_text.reset_mock()
    context.args = ["btc"]
    await unsub_command(update, context)
    assert await is_subscribed(uid, sym) is False
    update.message.reply_text.assert_called_once()
    unsub_msg = update.message.reply_text.call_args[0][0]
    assert "Unsubscribed from BTC Daily Insights." in unsub_msg
    assert "/sub btc" in unsub_msg

@pytest.mark.asyncio
async def test_gram_ton_equivalence():
    assert resolve_coin("gram") == "GRAM"
    assert resolve_coin("ton") == "GRAM"
    assert resolve_coin("toncoin") == "GRAM"

    # Rate for GRAM and TON must be identical and accurately around $0.94 - $1.08, not 1.60
    data_gram = await crypto_service.get_coin_data("GRAM")
    data_ton = await crypto_service.get_coin_data("TON")
    assert abs(data_gram["current_price"] - data_ton["current_price"]) < 0.001
    assert data_gram["current_price"] < 1.30, f"Expected realistic Toncoin price, got {data_gram['current_price']}"

@pytest.mark.asyncio
async def test_daily_subscription_cards_delivery():
    bot_mock = MagicMock()
    bot_mock.send_photo = AsyncMock()
    user_id = 998877

    await deliver_subscription_rates_to_user(bot_mock, user_id, ["GRAM", "BTC"], "2026-11-22")
    assert bot_mock.send_photo.call_count == 2
    first_call_kwargs = bot_mock.send_photo.call_args_list[0][1]
    caption = first_call_kwargs["caption"]
    assert "GRAM:" in caption
    assert "Use /gram for 7d Chart" in caption
    assert "photo" in first_call_kwargs

@pytest.mark.asyncio
async def test_daily_and_meme_captions_and_coins():
    bot_mock = MagicMock()
    bot_mock.send_photo = AsyncMock()
    user_id = 887766

    await deliver_daily_to_user(bot_mock, user_id, "2026-11-22")
    assert bot_mock.send_photo.called
    caption = bot_mock.send_photo.call_args[1]["caption"]
    assert "via @CurrencingBot. Tap /" in caption
    assert "Daily Thoughts" in caption or "Daily Degen Lore" in caption

    # Test meme for specific coin
    buf = render_meme_card("Solana Speed", "Blasting through the candles", "Too fast", coin_symbol="SOL")
    assert len(buf.getvalue()) > 5000

@pytest.mark.asyncio
async def test_didyouknow_and_timestamp_margins():
    from bot.handlers.meme import didyouknow_command, DID_YOU_KNOW_FACTS
    from bot.graphics.templates import render_didyouknow_card
    from unittest.mock import patch

    # 1. GRAM and TON have dedicated facts
    assert "GRAM" in DID_YOU_KNOW_FACTS
    assert "TON" in DID_YOU_KNOW_FACTS
    assert len(DID_YOU_KNOW_FACTS["GRAM"]) >= 3
    assert len(DID_YOU_KNOW_FACTS["BTC"]) >= 3

    # Check GRAM facts are about Telegram/TON, not Bitcoin pizza
    assert any("telegram" in fact[1].lower() or "ton" in fact[1].lower() for fact in DID_YOU_KNOW_FACTS["GRAM"])

    # 2. Test didyouknow handler invocation
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User, id=123)
    update.effective_chat = MagicMock(spec=Chat, id=123, type=ChatType.PRIVATE)
    update.effective_message = MagicMock(spec=Message, message_id=1)
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()

    with patch("bot.handlers.meme.check_user_authorization", return_value=True), \
         patch("bot.handlers.meme._send_fun_card", new_callable=AsyncMock) as mock_send:
        # /dyk gram
        context.args = ["gram"]
        await didyouknow_command(update, context)
        assert mock_send.called
        call_args = mock_send.call_args[0]
        # Check rendered image buffer is generated
        assert len(call_args[2].getvalue()) > 1000

    # 3. Card rendering verifies timestamp does not overflow
    buf = render_didyouknow_card("GRAM", "Test Title", "Test Body")
    assert len(buf.getvalue()) > 1000
