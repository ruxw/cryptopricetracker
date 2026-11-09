import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.services.crypto_api import crypto_service
from bot.graphics.assets import COINS, FIAT_CURRENCIES, format_price, format_change

async def run_tests():
    print("Testing Crypto API Service...")
    await crypto_service.refresh_market_data(force=True)

    # 1. Verify all 9 coins are supported
    required_coins = ["BTC", "ETH", "SOL", "GRAM", "LTC", "XMR", "XRP", "BNB", "TRX"]
    for sym in required_coins:
        assert sym in COINS, f"Missing coin {sym} in COINS mapping!"
        coin_data = await crypto_service.get_coin_data(sym)
        assert coin_data is not None, f"No data for {sym}!"
        assert coin_data["current_price"] > 0, f"Price for {sym} should be > 0!"
        assert "sparkline" in coin_data, f"Sparkline missing for {sym}!"
        assert len(coin_data["sparkline"]) > 0, f"Sparkline empty for {sym}!"
        print(f"✓ {sym}: ${coin_data['current_price']} (24h: {coin_data['change_24h']}%, ATH: ${coin_data['ath']})")

    # 2. Verify 3x3 overview list
    overview = await crypto_service.get_all_overview_data()
    assert len(overview) == 9, f"Expected 9 coins in overview, got {len(overview)}"
    print("✓ Overview list length: 9")

    # 3. Verify Conversion system
    # Test LTC -> USD
    conv_ltc = await crypto_service.convert("LTC", 0.3, "USD")
    assert conv_ltc["crypto_symbol"] == "LTC"
    assert conv_ltc["crypto_amount"] == 0.3
    assert conv_ltc["fiat_symbol"] == "USD"
    assert conv_ltc["fiat_value"] > 0
    print(f"✓ Conversion 0.3 LTC -> ${conv_ltc['fiat_value']:.2f} USD")

    # Test BTC -> EUR
    conv_btc = await crypto_service.convert("BTC", 1.5, "EUR")
    assert conv_btc["fiat_symbol"] == "EUR"
    assert conv_btc["fiat_value"] > 0
    print(f"✓ Conversion 1.5 BTC -> €{conv_btc['fiat_value']:.2f} EUR")

    # 4. Verify Decimal formatting
    assert format_price(74820.63, 2) == "74,820.63"
    assert format_price(2124.17, 2) == "2,124.17"
    assert format_price(0.3174, 4) == "0.3174"
    assert format_change(-1.36) == "-1.36%"
    assert format_change(2.45) == "+2.45%"
    print("✓ Formatting verified")

    await crypto_service.close()
    print("All Crypto API Service tests PASSED!")

import pytest

@pytest.mark.asyncio
async def test_crypto_api_service():
    await run_tests()
