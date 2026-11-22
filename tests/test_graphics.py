import os
import sys
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.graphics.templates import (
    render_coin_stats, render_market_overview, render_all_time_high, render_conversion
)
from bot.graphics.assets import COINS

def test_all_templates():
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Test individual stats for each of the 9 coins
    dummy_prices = [100.0 + i * 0.5 for i in range(168)]
    for sym in COINS.keys():
        buf = render_coin_stats(
            symbol=sym,
            price=1234.56,
            daily_change=-2.45,
            weekly_change=5.82,
            sparkline_prices=dummy_prices
        )
        assert buf is not None
        assert buf.getbuffer().nbytes > 10000
        im = Image.open(buf)
        assert im.size == (1024, 640), f"Invalid size for {sym}: {im.size}"

    print(f"✓ Verified stats template for all {len(COINS)} coins (1024x640)")

    # 2. Test 3x3 Overview Grid
    overview_sample = [
        {"symbol": "BTC", "price": 74820.63, "change_24h": -1.36},
        {"symbol": "ETH", "price": 2124.17, "change_24h": -4.98},
        {"symbol": "SOL", "price": 86.79, "change_24h": -2.91},
        {"symbol": "GRAM", "price": 1.05, "change_24h": -1.1},
        {"symbol": "LTC", "price": 51.44, "change_24h": -0.76},
        {"symbol": "XMR", "price": 599.51, "change_24h": -0.2},
        {"symbol": "XRP", "price": 1.11, "change_24h": -4.68},
        {"symbol": "BNB", "price": 686.71, "change_24h": -1.58},
        {"symbol": "TRX", "price": 0.3174, "change_24h": -0.87},
    ]
    buf_ov = render_market_overview(overview_sample)
    im_ov = Image.open(buf_ov)
    assert im_ov.size == (1024, 614), f"Overview size mismatch: {im_ov.size}"
    print("✓ Verified 3x3 Overview Grid template (1024x614)")

    # 3. Test ATH Template
    buf_ath = render_all_time_high("BTC", 126080.0, "2025-10-06T10:57:42.000Z")
    im_ath = Image.open(buf_ath)
    assert im_ath.size == (1024, 640), f"ATH size mismatch: {im_ath.size}"
    print("✓ Verified ATH Template (1024x640)")

    # 4. Test Conversion Template
    buf_conv = render_conversion("LTC", 0.3, "USD", 15.44)
    im_conv = Image.open(buf_conv)
    assert im_conv.size == (1024, 640), f"Conversion size mismatch: {im_conv.size}"
    print("✓ Verified Conversion Template (1024x640)")

    print("All image generation template tests PASSED!")

if __name__ == "__main__":
    test_all_templates()
