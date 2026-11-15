import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.services.ai_converter import parse_conversion_query_local, parse_conversion_query, execute_conversion

@pytest.mark.asyncio
async def test_parse_conversion_query_local():
    # 1. $100 eth
    res1 = parse_conversion_query_local("$100 eth")
    assert res1 is not None
    assert res1["amount"] == 100.0
    assert res1["from_currency"] == "USD"
    assert res1["to_currency"] == "ETH"

    # 2. 0.5 btc in eur
    res2 = parse_conversion_query_local("0.5 btc in eur")
    assert res2 is not None
    assert res2["amount"] == 0.5
    assert res2["from_currency"] == "BTC"
    assert res2["to_currency"] == "EUR"

    # 3. 50 bucks to sol
    res3 = parse_conversion_query_local("50 bucks to sol")
    assert res3 is not None
    assert res3["amount"] == 50.0
    assert res3["from_currency"] == "USD"
    assert res3["to_currency"] == "SOL"

    # 4. 1000 doge
    res4 = parse_conversion_query_local("1000 doge")
    assert res4 is not None
    assert res4["amount"] == 1000.0
    assert res4["from_currency"] == "DOGE"
    assert res4["to_currency"] == "USD"

    # 5. convert 2 eth to usd
    res5 = parse_conversion_query_local("convert 2 eth to usd")
    assert res5 is not None
    assert res5["amount"] == 2.0
    assert res5["from_currency"] == "ETH"
    assert res5["to_currency"] == "USD"

@pytest.mark.asyncio
async def test_execute_conversion():
    conv = await execute_conversion("100 usd in btc")
    assert conv["crypto_symbol"] == "BTC"
    assert conv["fiat_symbol"] == "USD"
    assert conv["fiat_value"] == 100.0
    assert conv["crypto_amount"] > 0
    assert "BTC" in conv["summary"]
