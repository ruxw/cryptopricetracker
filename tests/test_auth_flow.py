import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.database import init_db, register_private_start, is_user_verified
from bot.services.crypto_api import crypto_service
from bot.handlers.inline import inline_query_handler
from bot.handlers.group import group_fallback_handler
from bot.config import UNVERIFIED_MESSAGE, GROUP_FALLBACK_MESSAGE

async def run_auth_tests():
    await init_db()

    unverified_uid = 1122334455
    verified_uid = 5544332211
    await register_private_start(verified_uid, "verified_user", "Alice")

    # 1. Test unverified user in inline query
    mock_unverified_user = MagicMock(id=unverified_uid, is_bot=False)
    mock_inline_query = AsyncMock()
    mock_inline_query.from_user = mock_unverified_user
    mock_inline_query.query = "btc"

    mock_update = MagicMock()
    mock_update.inline_query = mock_inline_query
    mock_context = MagicMock()
    mock_context.bot.username = "CurrencingBot"

    await inline_query_handler(mock_update, mock_context)

    # Verify that answer was called with button/switch_pm to private start
    mock_inline_query.answer.assert_called_once()
    args, kwargs = mock_inline_query.answer.call_args
    assert "button" in kwargs, "Unverified user must receive switch_pm/verify button!"
    assert kwargs["button"].start_parameter == "verify"
    print("✓ Unverified user blocked in inline mode & prompted to start in private")

    # 2. Test verified user in inline query
    mock_verified_user = MagicMock(id=verified_uid, is_bot=False)
    mock_inline_query_v = AsyncMock()
    mock_inline_query_v.from_user = mock_verified_user
    mock_inline_query_v.query = "btc"

    mock_update_v = MagicMock()
    mock_update_v.inline_query = mock_inline_query_v

    # Make bot.get_chat_member awaitable and return a "member" status
    from unittest.mock import AsyncMock as _AM
    mock_member = MagicMock()
    mock_member.status = "member"
    mock_context.bot.get_chat_member = _AM(return_value=mock_member)

    await inline_query_handler(mock_update_v, mock_context)
    mock_inline_query_v.answer.assert_called_once()
    args_v, kwargs_v = mock_inline_query_v.answer.call_args
    results = args_v[0]
    assert len(results) > 0, "Verified user should receive inline results"
    print(f"✓ Verified user received {len(results)} inline results")

    # 3. Test group fallback handler
    mock_msg = AsyncMock()
    mock_msg.text = "@currencingbot can you trade for me?"
    mock_chat = MagicMock()
    mock_chat.id = -100998877
    mock_chat.type = "group"

    mock_update_grp = MagicMock()
    mock_update_grp.message = mock_msg
    mock_update_grp.effective_chat = mock_chat
    mock_update_grp.effective_user = mock_verified_user

    await group_fallback_handler(mock_update_grp, mock_context)
    mock_msg.reply_text.assert_called_once()
    call_text = mock_msg.reply_text.call_args[0][0]
    assert GROUP_FALLBACK_MESSAGE in call_text
    print("✓ Group fallback message properly returned when bot mentioned in group")

    await crypto_service.close()
    print("All Auth & Guest Mode tests PASSED!")

import pytest

@pytest.mark.asyncio
async def test_auth_and_guest_mode():
    await run_auth_tests()
