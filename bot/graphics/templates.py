import io
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw

from bot.graphics.assets import (
    COINS, FIAT_CURRENCIES, COLORS, get_font, hex_to_rgb,
    format_price, format_change, get_fiat_badge
)
from bot.graphics.generator import (
    get_base_background, draw_rounded_rect, draw_footer, draw_historical_chart
)

def render_coin_stats(
    symbol: str,
    price: float,
    daily_change: float,
    weekly_change: float,
    sparkline_prices: List[float],
    date_labels: Optional[List[str]] = None
) -> io.BytesIO:
    """Template 1: Individual coin statistics with 7-day chart."""
    symbol = symbol.upper()
    meta = COINS.get(symbol, {
        "name": symbol,
        "symbol": symbol,
        "color": "#456ee8",
        "decimals": 2,
        "icon": None
    })

    img = get_base_background(1024, 640)

    # Outer frosted card
    draw_rounded_rect(
        img,
        (54, 70, 970, 580),
        radius=36,
        fill=COLORS["card_bg"],
        outline=(255, 255, 255, 140),
        width=2
    )

    draw = ImageDraw.Draw(img)

    # 1. Price on top-left: Currency sign in coin accent color, numbers in dark navy
    coin_color = hex_to_rgb(meta.get("color", "#456ee8"))
    font_price = get_font(72, bold=True, weight="bold")   # Heavy — most prominent
    price_str = format_price(price, decimals=meta.get("decimals", 2))

    # Currency symbol '$'
    sign_text = "$"
    sign_bbox = font_price.getbbox(sign_text)
    sign_w = sign_bbox[2] - sign_bbox[0]
    draw.text((98, 120), sign_text, fill=coin_color, font=font_price)

    # Price numbers
    draw.text((98 + sign_w + 4, 120), price_str, fill=COLORS["navy_text"], font=font_price)

    # 2. Coin Pill on top-right: white capsule with logo + name
    pill_bbox = (645, 112, 925, 186)
    draw_rounded_rect(
        img,
        pill_bbox,
        radius=37,
        fill=COLORS["pill_bg"],
        outline=(255, 255, 255, 220),
        width=1
    )

    # Paste coin icon inside pill
    icon_path = meta.get("icon")
    icon_w = 44
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA")
            icon = icon.resize((icon_w, icon_w), Image.Resampling.LANCZOS)
            img.alpha_composite(icon, (665, 127))
        except Exception:
            icon_w = 0
    else:
        icon_w = 0

    # Coin Name
    font_coin = get_font(32, bold=True, weight="semibold")
    draw.text((665 + icon_w + 14, 131), meta["name"], fill=COLORS["navy_text"], font=font_coin)

    # 3. Badges: Daily Change & Weekly Change
    # Daily Change
    d_is_pos = daily_change >= 0
    d_color = COLORS["green"] if d_is_pos else COLORS["red"]
    font_lbl = get_font(13, bold=True, weight="semibold")  # Label — semibold
    font_val = get_font(28, bold=True, weight="bold")       # Value — bold

    # "DAILY CHANGE" text
    d_lbl = "DAILY CHANGE"
    bbox_d = font_lbl.getbbox(d_lbl)
    tw_d = bbox_d[2] - bbox_d[0]
    draw.text((395 - tw_d // 2, 232), d_lbl, fill=d_color, font=font_lbl)

    # Daily capsule
    draw_rounded_rect(img, (290, 258, 500, 324), radius=33, fill=d_color)
    d_val_str = format_change(daily_change)
    bbox_vd = font_val.getbbox(d_val_str)
    vw_d = bbox_vd[2] - bbox_vd[0]
    draw.text((395 - vw_d // 2, 274), d_val_str, fill=COLORS["white"], font=font_val)

    # Weekly Change
    w_is_pos = weekly_change >= 0
    w_color = COLORS["green"] if w_is_pos else COLORS["red"]

    # "WEEKLY CHANGE" text
    w_lbl = "WEEKLY CHANGE"
    bbox_w = font_lbl.getbbox(w_lbl)
    tw_w = bbox_w[2] - bbox_w[0]
    draw.text((625 - tw_w // 2, 232), w_lbl, fill=w_color, font=font_lbl)

    # Weekly capsule
    draw_rounded_rect(img, (520, 258, 730, 324), radius=33, fill=w_color)
    w_val_str = format_change(weekly_change)
    bbox_vw = font_val.getbbox(w_val_str)
    vw_w = bbox_vw[2] - bbox_vw[0]
    draw.text((625 - vw_w // 2, 274), w_val_str, fill=COLORS["white"], font=font_val)

    # 4. 7-Day Historical Chart
    if not date_labels:
        # Default 8 dates ending today
        today = datetime.now()
        date_labels = [
            (today - timedelta(days=7 - i)).strftime("%b. %d")
            for i in range(8)
        ]

    # Chart line/fill colour: green if weekly positive, red if negative
    chart_positive = weekly_change >= 0
    draw_historical_chart(
        img,
        sparkline_prices,
        bbox=(96, 360, 928, 510),
        date_labels=date_labels,
        is_positive=chart_positive,
    )

    # 5. Footer
    draw_footer(img, y_pos=608)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_market_overview(coins_data: List[Dict[str, Any]]) -> io.BytesIO:
    """Template 2: 3x3 Multi-Coin Market Overview Grid."""
    img = get_base_background(1024, 614)

    # Display up to 9 coins in a 3x3 layout
    display_coins = coins_data[:9]

    # Grid specifications
    tile_w, tile_h = 300, 140
    gap_x, gap_y = 24, 20
    start_x, start_y = 38, 56

    font_name = get_font(22, bold=True)
    font_price = get_font(32, bold=True)
    font_change = get_font(20, bold=True)

    for idx, item in enumerate(display_coins):
        r = idx // 3
        c = idx % 3
        tx0 = start_x + c * (tile_w + gap_x)
        ty0 = start_y + r * (tile_h + gap_y)
        tx1 = tx0 + tile_w
        ty1 = ty0 + tile_h

        # Tile card
        draw_rounded_rect(
            img,
            (tx0, ty0, tx1, ty1),
            radius=24,
            fill=COLORS["card_bg"],
            outline=(255, 255, 255, 150),
            width=1
        )

        draw = ImageDraw.Draw(img)

        sym = item.get("symbol", "").upper()
        meta = COINS.get(sym, {
            "name": item.get("name", sym),
            "symbol": sym,
            "color": "#456ee8",
            "decimals": 2,
            "icon": None
        })

        coin_name = meta["name"]
        icon_path = meta.get("icon")

        # Top row: Centered Icon + Coin Name
        icon_size = 26
        has_icon = icon_path and os.path.exists(icon_path)
        bbox_n = font_name.getbbox(coin_name)
        nw = bbox_n[2] - bbox_n[0]
        total_top_w = (icon_size + 8 + nw) if has_icon else nw
        top_start_x = tx0 + (tile_w - total_top_w) // 2

        if has_icon:
            try:
                icon = Image.open(icon_path).convert("RGBA")
                icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                img.alpha_composite(icon, (top_start_x, ty0 + 15))
            except Exception:
                pass
            text_x = top_start_x + icon_size + 8
        else:
            text_x = top_start_x

        # Coin name in crisp white bold
        draw.text((text_x, ty0 + 16), coin_name, fill=COLORS["white"], font=font_name)

        # Middle row: Price centered
        p_val = item.get("price", 0.0)
        p_decimals = meta.get("decimals", 2)
        p_str = format_price(p_val, decimals=p_decimals)

        accent_col = hex_to_rgb(meta.get("color", "#456ee8"))
        sign_bbox = font_price.getbbox("$")
        sign_w = sign_bbox[2] - sign_bbox[0]
        num_bbox = font_price.getbbox(p_str)
        num_w = num_bbox[2] - num_bbox[0]
        total_price_w = sign_w + 3 + num_w

        px = tx0 + (tile_w - total_price_w) // 2
        py = ty0 + 52
        draw.text((px, py), "$", fill=accent_col, font=font_price)
        draw.text((px + sign_w + 3, py), p_str, fill=COLORS["navy_text"], font=font_price)

        # Bottom row: 24h Change
        chg_val = item.get("change_24h", 0.0)
        chg_is_pos = chg_val >= 0
        chg_col = COLORS["green"] if chg_is_pos else COLORS["red"]
        chg_str = format_change(chg_val)
        chg_bbox = font_change.getbbox(chg_str)
        cw = chg_bbox[2] - chg_bbox[0]
        draw.text((tx0 + (tile_w - cw) // 2, ty0 + 98), chg_str, fill=chg_col, font=font_change)

    # Footer
    draw_footer(img, y_pos=565)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_all_time_high(
    symbol: str,
    ath_price: float,
    ath_date: str
) -> io.BytesIO:
    """Template 3: Individual All-Time High statistics with price and date."""
    symbol = symbol.upper()
    meta = COINS.get(symbol, {
        "name": symbol,
        "symbol": symbol,
        "color": "#f7931a",
        "decimals": 2,
        "icon": None
    })

    img = get_base_background(1024, 640)

    # Outer frosted card
    draw_rounded_rect(
        img,
        (54, 70, 970, 580),
        radius=36,
        fill=COLORS["card_bg"],
        outline=(255, 255, 255, 140),
        width=2
    )

    draw = ImageDraw.Draw(img)

    # Title: ALL-TIME HIGH PRICE
    title_text = "ALL-TIME HIGH PRICE"
    font_title = get_font(20, bold=True)
    tb = font_title.getbbox(title_text)
    tw = tb[2] - tb[0]
    draw.text((512 - tw // 2, 112), title_text, fill=COLORS["white"], font=font_title)

    # Coin pill centered
    coin_pill_bbox = (308, 160, 716, 248)
    draw_rounded_rect(
        img,
        coin_pill_bbox,
        radius=44,
        fill=COLORS["pill_bg"],
        outline=(255, 255, 255, 220),
        width=1
    )

    # Coin logo + name inside pill
    icon_path = meta.get("icon")
    icon_w = 48
    coin_name = meta["name"]
    font_coin = get_font(36, bold=True)
    cb = font_coin.getbbox(coin_name)
    cw = cb[2] - cb[0]

    has_icon = icon_path and os.path.exists(icon_path)
    total_pill_content_w = (icon_w + 14 + cw) if has_icon else cw
    content_start_x = 308 + (408 - total_pill_content_w) // 2

    if has_icon:
        try:
            icon = Image.open(icon_path).convert("RGBA")
            icon = icon.resize((icon_w, icon_w), Image.Resampling.LANCZOS)
            img.alpha_composite(icon, (content_start_x, 180))
        except Exception:
            pass
        name_x = content_start_x + icon_w + 14
    else:
        name_x = content_start_x

    draw.text((name_x, 182), coin_name, fill=COLORS["navy_text"], font=font_coin)

    # Row 1: Price
    # Container
    draw_rounded_rect(
        img,
        (216, 290, 838, 370),
        radius=28,
        fill=(255, 255, 255, 175),
        outline=(255, 255, 255, 200),
        width=1
    )
    # Left pill "Price"
    draw_rounded_rect(
        img,
        (216, 290, 420, 370),
        radius=28,
        fill=COLORS["pill_bg"]
    )
    font_lbl = get_font(28, bold=True)
    lb = font_lbl.getbbox("Price")
    lw = lb[2] - lb[0]
    draw.text((216 + (204 - lw) // 2, 313), "Price", fill=COLORS["navy_text"], font=font_lbl)

    # Right value: $126,080.00
    font_val = get_font(36, bold=True)
    price_str = f"${format_price(ath_price, decimals=meta.get('decimals', 2))}"
    vb = font_val.getbbox(price_str)
    vw = vb[2] - vb[0]
    draw.text((420 + (418 - vw) // 2, 309), price_str, fill=COLORS["navy_text"], font=font_val)

    # Row 2: Date
    # Container
    draw_rounded_rect(
        img,
        (216, 396, 838, 476),
        radius=28,
        fill=(255, 255, 255, 175),
        outline=(255, 255, 255, 200),
        width=1
    )
    # Left pill "Date"
    draw_rounded_rect(
        img,
        (216, 396, 420, 476),
        radius=28,
        fill=COLORS["pill_bg"]
    )
    db = font_lbl.getbbox("Date")
    dw = db[2] - db[0]
    draw.text((216 + (204 - dw) // 2, 419), "Date", fill=COLORS["navy_text"], font=font_lbl)

    # Right date string: formatted nicely like "October 06, 2025"
    date_display = ath_date
    try:
        dt = datetime.fromisoformat(ath_date.replace("Z", "+00:00"))
        date_display = dt.strftime("%B %d, %Y")
    except Exception:
        pass

    font_date = get_font(32, bold=True)
    dt_b = font_date.getbbox(date_display)
    dt_w = dt_b[2] - dt_b[0]
    draw.text((420 + (418 - dt_w) // 2, 416), date_display, fill=COLORS["navy_text"], font=font_date)

    # Footer
    draw_footer(img, y_pos=608)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_conversion(
    crypto_symbol: str,
    crypto_amount: float,
    fiat_symbol: str,
    fiat_value: float,
    reverse: bool = False,
) -> io.BytesIO:
    """Template 4: Cryptocurrency conversion card.

    Normal mode  (reverse=False):
        Row 1 → Coin name + logo | amount of crypto
        Row 2 → fiat value       | fiat currency badge

    Reverse mode (reverse=True, /convert $100 eth):
        Row 1 → Coin name + logo | crypto amount received
        Row 2 → USD paid         | USD badge
        (same layout, different values fed in from the caller)
    """
    crypto_symbol = crypto_symbol.upper()
    fiat_symbol = fiat_symbol.upper()

    meta = COINS.get(crypto_symbol, {
        "name": crypto_symbol,
        "symbol": crypto_symbol,
        "color": "#345d9d",
        "icon": None
    })
    fiat_meta = FIAT_CURRENCIES.get(fiat_symbol, {
        "symbol": "$",
        "name": fiat_symbol,
        "decimals": 2
    })

    img = get_base_background(1024, 640)

    # Outer frosted card
    draw_rounded_rect(
        img,
        (44, 70, 980, 580),
        radius=36,
        fill=COLORS["card_bg"],
        outline=(255, 255, 255, 140),
        width=2
    )

    draw = ImageDraw.Draw(img)

    # Row 1: Selected Asset & Quantity
    # Container: x: 170..854, y: 140..244 (w: 684, h: 104, radius: 36)
    draw_rounded_rect(
        img,
        (170, 140, 854, 244),
        radius=36,
        fill=(240, 244, 255, 180),
        outline=(255, 255, 255, 200),
        width=1
    )
    # Left pill: x: 170..470
    draw_rounded_rect(
        img,
        (170, 140, 470, 244),
        radius=36,
        fill=COLORS["pill_bg"]
    )

    icon_path = meta.get("icon")
    icon_w = 44
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA")
            icon = icon.resize((icon_w, icon_w), Image.Resampling.LANCZOS)
            img.alpha_composite(icon, (200, 170))
        except Exception:
            icon_w = 0
    else:
        icon_w = 0

    font_crypto = get_font(32, bold=True)
    draw.text((200 + icon_w + 14, 172), meta["name"], fill=COLORS["navy_text"], font=font_crypto)

    # Right Amount: e.g. 0.3000
    font_amt = get_font(38, bold=True)
    # Format amount cleanly
    if crypto_amount < 1:
        amt_str = f"{crypto_amount:.4f}"
    elif crypto_amount == int(crypto_amount):
        amt_str = f"{crypto_amount:,.2f}"
    else:
        amt_str = f"{crypto_amount:,.4f}".rstrip("0").rstrip(".")

    ab = font_amt.getbbox(amt_str)
    aw = ab[2] - ab[0]
    draw.text((820 - aw, 169), amt_str, fill=COLORS["navy_text"], font=font_amt)

    # Middle Indicator: ⇅ Value
    # Capsule: x: 426..598, y: 276..336 (w: 172, h: 60, radius: 30)
    draw_rounded_rect(
        img,
        (426, 276, 598, 336),
        radius=30,
        fill=COLORS["pill_bg"],
        outline=(255, 255, 255, 220),
        width=1
    )
    font_mid = get_font(22, bold=True)
    mid_text = "⇅  Value"
    mb = font_mid.getbbox(mid_text)
    mw = mb[2] - mb[0]
    draw.text((512 - mw // 2, 292), mid_text, fill=COLORS["navy_text"], font=font_mid)

    # Row 2: Converted Value & Fiat
    # Container: x: 170..854, y: 368..472 (w: 684, h: 104, radius: 36)
    draw_rounded_rect(
        img,
        (170, 368, 854, 472),
        radius=36,
        fill=(240, 244, 255, 180),
        outline=(255, 255, 255, 200),
        width=1
    )

    # Left Converted Value: e.g. $15.44
    fiat_sign = fiat_meta.get("symbol", "$")
    fiat_dec = fiat_meta.get("decimals", 2)
    val_str = f"{fiat_sign}{format_price(fiat_value, decimals=fiat_dec)}"
    font_val = get_font(38, bold=True)
    draw.text((205, 397), val_str, fill=COLORS["navy_text"], font=font_val)

    # Right pill: x: 554..854
    draw_rounded_rect(
        img,
        (554, 368, 854, 472),
        radius=36,
        fill=COLORS["pill_bg"]
    )

    # Fiat Name + Badge: e.g. "USD ($)"
    font_fiat = get_font(32, bold=True)
    fb = font_fiat.getbbox(fiat_symbol)
    fw = fb[2] - fb[0]

    badge_size = 44
    total_fiat_w = fw + 16 + badge_size
    fiat_start_x = 554 + (300 - total_fiat_w) // 2

    draw.text((fiat_start_x, 400), fiat_symbol, fill=COLORS["navy_text"], font=font_fiat)

    badge = get_fiat_badge(fiat_sign, size=badge_size)
    img.alpha_composite(badge, (fiat_start_x + fw + 16, 398))

    # Footer
    draw_footer(img, y_pos=608)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf
