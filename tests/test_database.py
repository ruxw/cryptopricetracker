import asyncio
import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.database import (
    init_db, register_private_start, is_user_verified,
    record_interaction, get_user, get_verified_users_count
)

async def run_tests():
    await init_db()

    import time
    test_uid = int(time.time() * 1000)
    # 1. Unregistered user must not be verified
    assert await is_user_verified(test_uid) is False, "Unregistered user should not be verified!"

    # 2. Register user via private /start
    await register_private_start(test_uid, "crypto_trader", "Satoshi")

    # 3. User must now be verified persistently
    assert await is_user_verified(test_uid) is True, "Registered user must be verified!"

    # 4. User details stored persistently
    user = await get_user(test_uid)
    assert user is not None
    assert user["username"] == "crypto_trader"
    assert user["first_name"] == "Satoshi"
    assert user["is_verified"] == 1

    # 5. Record interaction
    await record_interaction(test_uid, "command", "/stats BTC")

    # 6. Count verified users
    count = await get_verified_users_count()
    assert count >= 1

    print("All persistent database verification tests PASSED!")

import pytest

@pytest.mark.asyncio
async def test_persistent_database_verification():
    await run_tests()
