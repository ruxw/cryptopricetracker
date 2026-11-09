import asyncio
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.constants import ChatMemberStatus

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.services.force_join import (
    parse_channel_target, get_force_join_channels,
    check_user_joined_all, get_force_join_keyboard
)

def test_channel_parsing():
    # 1. Test @username format
    t1 = parse_channel_target("@CryptoSignals", 1)
    assert t1["chat_id"] == "@CryptoSignals"
    assert t1["url"] == "https://t.me/CryptoSignals"

    # 2. Test t.me/username format
    t2 = parse_channel_target("t.me/CurrencingChat", 2)
    assert t2["chat_id"] == "@CurrencingChat"
    assert t2["url"] == "https://t.me/CurrencingChat"

    # 3. Test https://t.me/link format
    t3 = parse_channel_target("https://t.me/CryptoNewsHub", 3)
    assert t3["chat_id"] == "@CryptoNewsHub"
    assert t3["url"] == "https://t.me/CryptoNewsHub"

    # 4. Test column button layout (1 button per row)
    channels = [t1, t2, t3]
    kb = get_force_join_keyboard(channels)
    # Total rows = 3 channels + 1 "I Have Joined" row = 4 rows
    assert len(kb.inline_keyboard) == 4, f"Expected 4 rows in column, got {len(kb.inline_keyboard)}"
    for r in kb.inline_keyboard:
        assert len(r) == 1, "Each channel must be on its own line (single column)!"
    print("✓ Channel parsing & column keyboard verified")

@pytest.mark.asyncio
async def test_membership_check():
    mock_bot = AsyncMock()

    # User is member
    mock_member = MagicMock()
    mock_member.status = ChatMemberStatus.MEMBER
    mock_bot.get_chat_member.return_value = mock_member

    # When FORCE_JOINS is set in environment
    os.environ["FORCE_JOINS"] = "@test_channel_1, t.me/test_channel_2"
    from bot import config
    config.FORCE_JOINS_RAW = os.environ["FORCE_JOINS"]

    all_joined, missing = await check_user_joined_all(mock_bot, 123456)
    assert all_joined is True
    assert len(missing) == 0

    # User left one channel
    mock_left = MagicMock()
    mock_left.status = ChatMemberStatus.LEFT
    mock_bot.get_chat_member.side_effect = [mock_member, mock_left]

    all_joined2, missing2 = await check_user_joined_all(mock_bot, 123456)
    assert all_joined2 is False
    assert len(missing2) == 1
    print("✓ Membership check logic verified")

    # Cleanup env
    os.environ.pop("FORCE_JOINS", None)
    config.FORCE_JOINS_RAW = ""

if __name__ == "__main__":
    test_channel_parsing()
    asyncio.run(test_membership_check())
