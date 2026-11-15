import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.database import (
    init_db, record_coin_lookup, get_user_first_seen,
    get_user_last_lookup, get_user_profile_stats, get_chat_top_coins
)
from bot.graphics.templates import (
    render_satoshi_quote, render_cope_card, render_panic_card,
    render_wagmi_card, render_predict_card, render_didyouknow_card,
    render_me_profile_card, render_firstseen_card, render_lookup_card,
    render_chatvibe_card
)

@pytest.mark.asyncio
async def test_fun_and_meme_database():
    await init_db()
    user_id = 99887766
    chat_id = -100123456789

    # Record multiple lookups
    await record_coin_lookup(user_id, "SOL", 50.0, chat_id=chat_id)
    await record_coin_lookup(user_id, "SOL", 75.0, chat_id=chat_id)
    await record_coin_lookup(user_id, "BTC", 65000.0, chat_id=chat_id)

    # 1. Test first seen
    fs = await get_user_first_seen(user_id, "SOL")
    assert fs is not None
    assert fs["price"] == 50.0

    # 2. Test last lookup
    ll = await get_user_last_lookup(user_id, "SOL")
    assert ll is not None
    assert ll["price"] in [50.0, 75.0]

    # 3. Test user profile stats
    prof = await get_user_profile_stats(user_id)
    assert prof["user_id"] == user_id
    assert prof["total_lookups"] >= 3
    assert prof["favorite_coin"] == "SOL"

    # 4. Test chat top coins
    top = await get_chat_top_coins(chat_id)
    assert len(top) >= 2
    assert top[0]["symbol"] == "SOL"

def test_fun_and_meme_graphics():
    # Verify all 10 cards generate valid PNG bytes > 20KB
    b1 = render_satoshi_quote("If you don't believe it, I don't have time to convince you.")
    assert len(b1.getvalue()) > 20000

    b2 = render_cope_card("SOL", 72.5, 0.5052, "2020-05-11")
    assert len(b2.getvalue()) > 20000

    b3 = render_panic_card("BTC", 64000.0, -8.5)
    assert len(b3.getvalue()) > 20000

    b4 = render_wagmi_card([{"symbol": "SOL", "name": "Solana", "current_price": 72.5, "change_24h": 14.5}])
    assert len(b4.getvalue()) > 20000

    b5 = render_predict_card("BTC", 64000.0, 150000.0, 134.3)
    assert len(b5.getvalue()) > 20000

    b6 = render_didyouknow_card("BTC", "The Pizza Buy", "10,000 Bitcoins for 2 pizzas.")
    assert len(b6.getvalue()) > 20000

    b7 = render_me_profile_card(123456, "alice", "Alice", "2024-01-01", 10, "SOL")
    assert len(b7.getvalue()) > 20000

    b8 = render_firstseen_card("SOL", 50.0, 72.5, "10 Jan 2024")
    assert len(b8.getvalue()) > 20000

    b9 = render_lookup_card("SOL", 70.0, 72.5, "2 hours ago")
    assert len(b9.getvalue()) > 20000

    b10 = render_chatvibe_card("Crypto Group", [{"symbol": "SOL", "count": 15}])
    assert len(b10.getvalue()) > 20000
