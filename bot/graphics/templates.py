import io
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFilter

from bot.config import BOT_USERNAME
from bot.graphics.assets import (
    COINS, FIAT_CURRENCIES, COLORS, get_font, hex_to_rgb,
    format_price, format_change, get_fiat_badge
)
from bot.graphics.generator import (
    get_themed_background, draw_glass_frame, draw_historical_chart,
    draw_rounded_rect, draw_footer
)

def render_coin_stats(
    symbol: str,
    price: float,
    daily_change: float,
    weekly_change: float,
    sparkline_prices: List[float],
    date_labels: Optional[List[str]] = None
) -> io.BytesIO:
    """Template 1: Individual coin statistics with glassmorphism and 7-day chart."""
    symbol = symbol.upper()
    meta = COINS.get(symbol, {
        "name": symbol,
        "symbol": symbol,
        "color": "#f7931a",
        "decimals": 2,
        "icon": None
    })
    accent_hex = meta.get("color", "#f7931a")
    icon_path = meta.get("icon")

    # 1. Radiant Ambient Gradient + Repeating Watermark Pattern
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)

    # 2. Frosted Glassmorphism Outer Plate + Dark Obsidian Card + Branded Pill
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 3. Price on Top-Left: Currency sign in coin accent color, numbers in bold white
    coin_color = hex_to_rgb(accent_hex)
    font_price = get_font(66, weight="extrabold")
    price_str = format_price(price, decimals=meta.get("decimals", 2))

    sign_text = "$"
    sb = font_price.getbbox(sign_text)
    sw = sb[2] - sb[0]
    draw.text((cx0 + 38, cy0 + 32), sign_text, fill=coin_color, font=font_price)
    draw.text((cx0 + 38 + sw + 6, cy0 + 32), price_str, fill=(255, 255, 255), font=font_price)

    # 4. Coin Pill on Top-Right: porcelain capsule with logo + name
    pill_w = 236
    pill_h = 66
    px1 = cx1 - 38
    px0 = px1 - pill_w
    py0 = cy0 + 28
    py1 = py0 + pill_h
    pill_bbox = (px0, py0, px1, py1)

    pill_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pill_layer)
    p_draw.rounded_rectangle(
        pill_bbox,
        radius=pill_h // 2,
        fill=COLORS["pill_bg"],
        outline=COLORS["pill_border"],
        width=1
    )
    img.alpha_composite(pill_layer)

    # Icon inside pill
    icon_w = 44
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA").resize((icon_w, icon_w), Image.Resampling.LANCZOS)
            img.alpha_composite(icon, (px0 + 15, py0 + 11))
        except Exception:
            icon_w = 0
    else:
        icon_w = 0

    # Coin Name inside pill
    font_pill = get_font(29, weight="bold")
    draw = ImageDraw.Draw(img)
    name_x = px0 + (68 if icon_w > 0 else 24)
    draw.text((name_x, py0 + 15), meta["name"], fill=COLORS["navy_text"], font=font_pill)

    # Metadata Line below coin pill
    f_meta = get_font(13, weight="medium")
    now_utc = datetime.utcnow().strftime("%d %b %Y · %H:%M UTC")
    meta_str = f"{symbol} · USD · {now_utc}"
    mb = f_meta.getbbox(meta_str)
    mw = mb[2] - mb[0]
    draw.text((px1 - mw, py1 + 9), meta_str, fill=COLORS["gray_text"], font=f_meta)

    # 5. Badges: Daily Change & Weekly Change Capsules
    f_badge = get_font(18, weight="bold")

    # Daily Change
    d_is_pos = daily_change >= 0
    d_bg = (14, 42, 28, 230) if d_is_pos else (48, 16, 20, 230)
    d_border = (0, 230, 118, 70) if d_is_pos else (255, 70, 80, 70)
    d_col = COLORS["green"] if d_is_pos else COLORS["red"]
    d_arrow = "▲" if d_is_pos else "▼"
    d_str = f"DAILY  {d_arrow} {format_change(daily_change)}"

    db = f_badge.getbbox(d_str)
    dbw = db[2] - db[0]
    d_box_w = dbw + 36
    daily_bbox = (cx0 + 38, cy0 + 130, cx0 + 38 + d_box_w, cy0 + 184)

    # Weekly Change
    w_is_pos = weekly_change >= 0
    w_bg = (14, 42, 28, 230) if w_is_pos else (48, 16, 20, 230)
    w_border = (0, 230, 118, 70) if w_is_pos else (255, 70, 80, 70)
    w_col = COLORS["green"] if w_is_pos else COLORS["red"]
    w_arrow = "▲" if w_is_pos else "▼"
    w_str = f"WEEKLY  {w_arrow} {format_change(weekly_change)}"

    wb = f_badge.getbbox(w_str)
    wbw = wb[2] - wb[0]
    w_box_w = wbw + 36
    weekly_bbox = (cx0 + 38 + d_box_w + 16, cy0 + 130, cx0 + 38 + d_box_w + 16 + w_box_w, cy0 + 184)

    b_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd_draw = ImageDraw.Draw(b_layer)
    bd_draw.rounded_rectangle(daily_bbox, radius=27, fill=d_bg, outline=d_border, width=1)
    bd_draw.rounded_rectangle(weekly_bbox, radius=27, fill=w_bg, outline=w_border, width=1)
    img.alpha_composite(b_layer)

    draw = ImageDraw.Draw(img)
    draw.text((daily_bbox[0] + 18, daily_bbox[1] + 13), d_str, fill=d_col, font=f_badge)
    draw.text((weekly_bbox[0] + 18, weekly_bbox[1] + 13), w_str, fill=w_col, font=f_badge)

    # 6. 7D High / Low Stats
    f_stat_lbl = get_font(15, weight="semibold")
    f_stat_val = get_font(16, weight="bold")

    if sparkline_prices and len(sparkline_prices) > 1 and (max(sparkline_prices) - min(sparkline_prices) > 0.0001):
        high_val = max(sparkline_prices)
        low_val = min(sparkline_prices)
    else:
        spread = max(0.018, abs(weekly_change) / 100.0)
        high_val = price * (1.0 + spread)
        low_val = price * (1.0 - spread)

    if high_val <= low_val or abs(high_val - low_val) < 0.0001:
        spread = max(0.018, abs(weekly_change) / 100.0)
        high_val = price * (1.0 + spread)
        low_val = price * (1.0 - spread)

    stat_x = cx1 - 225
    draw.text((stat_x, cy0 + 134), "7D HIGH", fill=COLORS["gray_text"], font=f_stat_lbl)
    high_str = f"${format_price(high_val, decimals=meta.get('decimals', 2))}"
    draw.text((stat_x + 84, cy0 + 133), high_str, fill=(255, 255, 255), font=f_stat_val)

    draw.text((stat_x, cy0 + 161), "7D LOW", fill=COLORS["gray_text"], font=f_stat_lbl)
    low_str = f"${format_price(low_val, decimals=meta.get('decimals', 2))}"
    draw.text((stat_x + 84, cy0 + 160), low_str, fill=(255, 255, 255), font=f_stat_val)

    # 7. 7-Day Historical Chart with Spline Line & Gradient Fade
    chart_positive = weekly_change >= 0
    chart_bbox = (cx0 + 20, cy0 + 215, cx1 - 20, cy1 - 42)
    draw_historical_chart(
        img,
        sparkline_prices,
        bbox=chart_bbox,
        date_labels=date_labels,
        is_positive=chart_positive,
    )

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_market_overview(coins_data: List[Dict[str, Any]]) -> io.BytesIO:
    """Template 2: 3x3 Multi-Coin Market Overview Grid with glowing borders and watermarks."""
    width, height = 1024, 614
    # Dark obsidian background with ambient gradient lighting
    bg = Image.new("RGBA", (width, height), (10, 11, 15, 255))

    # Grid specifications: 3x3 layout
    tile_w, tile_h = 292, 146
    gap_x, gap_y = 22, 18
    start_x, start_y = 50, 36

    font_name = get_font(21, weight="bold")
    font_price = get_font(32, weight="extrabold")
    font_chg = get_font(20, weight="bold")

    display_coins = coins_data[:9]

    for idx, item in enumerate(display_coins):
        r = idx // 3
        c = idx % 3
        tx0 = start_x + c * (tile_w + gap_x)
        ty0 = start_y + r * (tile_h + gap_y)
        tx1 = tx0 + tile_w
        ty1 = ty0 + tile_h

        sym = item.get("symbol", "").upper()
        meta = COINS.get(sym, {
            "name": item.get("name", sym),
            "symbol": sym,
            "color": "#f7931a",
            "decimals": 2,
            "icon": None
        })
        acc_hex = meta.get("color", "#f7931a")
        acc_rgb = hex_to_rgb(acc_hex)

        # 1. Ambient Glow Bloom behind card in coin's signature color
        bloom = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bl_draw = ImageDraw.Draw(bloom)
        bl_draw.rounded_rectangle((tx0 - 2, ty0 - 2, tx1 + 2, ty1 + 2), radius=26, fill=acc_rgb + (38,))
        bloom = bloom.filter(ImageFilter.GaussianBlur(8))
        bg = Image.alpha_composite(bg, bloom)

        # 2. Dark Translucent Glass Card Body + Coin Outline
        card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cd_draw = ImageDraw.Draw(card_layer)
        cd_draw.rounded_rectangle(
            (tx0, ty0, tx1, ty1),
            radius=22,
            fill=(18, 20, 26, 235),
            outline=acc_rgb + (145,),
            width=1
        )
        bg = Image.alpha_composite(bg, card_layer)

        # 3. Coin Icon Watermark inside card
        icon_path = meta.get("icon")
        if icon_path and os.path.exists(icon_path):
            try:
                icon_img = Image.open(icon_path).convert("RGBA")
                wm_size = 72
                wm_img = icon_img.resize((wm_size, wm_size), Image.Resampling.LANCZOS)
                _, _, _, a = wm_img.split()
                a_mask = a.point(lambda p: int(p * 0.10))
                w_icon = Image.composite(wm_img, Image.new("RGBA", (wm_size, wm_size), (0, 0, 0, 0)), a_mask)
                bg.alpha_composite(w_icon, (tx0 + (tile_w - wm_size) // 2, ty0 + (tile_h - wm_size) // 2))
            except Exception:
                pass

        # 4. Top Row: Centered Coin Icon (26x26) + Coin Name
        icon_size = 26
        coin_name = meta["name"]
        nb = font_name.getbbox(coin_name)
        nw = nb[2] - nb[0]
        has_icon = icon_path and os.path.exists(icon_path)
        total_top_w = (icon_size + 8 + nw) if has_icon else nw
        top_start_x = tx0 + (tile_w - total_top_w) // 2

        if has_icon:
            try:
                c_icon = Image.open(icon_path).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                bg.alpha_composite(c_icon, (top_start_x, ty0 + 16))
            except Exception:
                pass
            text_x = top_start_x + icon_size + 8
        else:
            text_x = top_start_x

        draw = ImageDraw.Draw(bg)
        draw.text((text_x, ty0 + 17), coin_name, fill=(255, 255, 255), font=font_name)

        # 5. Middle Row: Large Price Centered with Coin-Accented '$'
        p_val = item.get("price", 0.0)
        p_str = format_price(p_val, decimals=meta.get("decimals", 2))

        sb = font_price.getbbox("$")
        sw = sb[2] - sb[0]
        pb = font_price.getbbox(p_str)
        pw = pb[2] - pb[0]
        total_p_w = sw + 4 + pw
        px = tx0 + (tile_w - total_p_w) // 2
        py = ty0 + 54

        draw.text((px, py), "$", fill=acc_rgb, font=font_price)
        draw.text((px + sw + 4, py), p_str, fill=(255, 255, 255), font=font_price)

        # 6. Bottom Row: 24h Percentage Change Centered
        chg = item.get("change_24h", 0.0)
        chg_is_pos = chg >= 0
        chg_col = COLORS["green"] if chg_is_pos else COLORS["red"]
        chg_str = format_change(chg)
        cb = font_chg.getbbox(chg_str)
        cw = cb[2] - cb[0]
        draw.text((tx0 + (tile_w - cw) // 2, ty0 + 102), chg_str, fill=chg_col, font=font_chg)

    # 7. Bottom Branded Pill Badge (t.me/CurrencingBot)
    draw_footer(bg, y_pos=584)

    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_all_time_high(
    symbol: str,
    ath_price: float,
    ath_date: str
) -> io.BytesIO:
    """Template 3: Individual All-Time High statistics with glassmorphism card."""
    symbol = symbol.upper()
    meta = COINS.get(symbol, {
        "name": symbol,
        "symbol": symbol,
        "color": "#f7931a",
        "decimals": 2,
        "icon": None
    })
    accent_hex = meta.get("color", "#f7931a")
    icon_path = meta.get("icon")

    # 1. Themed Background + Watermark Pattern
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)

    # 2. Glassmorphism Frame + Dark Container + Bottom Pill
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # Title: ALL-TIME HIGH PRICE
    title_text = "ALL-TIME HIGH PRICE"
    font_title = get_font(22, weight="extrabold")
    tb = font_title.getbbox(title_text)
    tw = tb[2] - tb[0]
    draw.text((cx0 + (cx1 - cx0 - tw) // 2, cy0 + 36), title_text, fill=(255, 255, 255), font=font_title)

    # Coin Pill Centered: Porcelain capsule
    pill_w = 260
    pill_h = 64
    px0 = cx0 + (cx1 - cx0 - pill_w) // 2
    py0 = cy0 + 86
    pill_bbox = (px0, py0, px0 + pill_w, py0 + pill_h)

    p_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(p_layer)
    p_draw.rounded_rectangle(
        pill_bbox,
        radius=pill_h // 2,
        fill=COLORS["pill_bg"],
        outline=COLORS["pill_border"],
        width=1
    )
    img.alpha_composite(p_layer)

    icon_w = 42
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA").resize((icon_w, icon_w), Image.Resampling.LANCZOS)
            img.alpha_composite(icon, (px0 + 16, py0 + 11))
        except Exception:
            icon_w = 0
    else:
        icon_w = 0

    font_coin = get_font(28, weight="bold")
    draw = ImageDraw.Draw(img)
    name_x = px0 + (68 if icon_w > 0 else 24)
    draw.text((name_x, py0 + 16), meta["name"], fill=COLORS["navy_text"], font=font_coin)

    # Row 1: Price Card
    row1_bbox = (cx0 + 44, cy0 + 185, cx1 - 44, cy0 + 265)
    r1_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    r1_draw = ImageDraw.Draw(r1_layer)
    r1_draw.rounded_rectangle(row1_bbox, radius=24, fill=(22, 24, 32, 230), outline=(255, 255, 255, 30), width=1)
    r1_draw.rounded_rectangle((row1_bbox[0], row1_bbox[1], row1_bbox[0] + 180, row1_bbox[3]), radius=24, fill=(35, 38, 50, 240))
    img.alpha_composite(r1_layer)

    draw = ImageDraw.Draw(img)
    f_lbl = get_font(24, weight="bold")
    draw.text((row1_bbox[0] + 55, row1_bbox[1] + 25), "Price", fill=(255, 255, 255), font=f_lbl)

    f_val = get_font(36, weight="extrabold")
    p_str = format_price(ath_price, decimals=meta.get("decimals", 2))
    sb = f_val.getbbox("$")
    sw = sb[2] - sb[0]
    pb = f_val.getbbox(p_str)
    pw = pb[2] - pb[0]
    total_pw = sw + 6 + pw
    vx = row1_bbox[0] + 180 + ((row1_bbox[2] - (row1_bbox[0] + 180)) - total_pw) // 2
    draw.text((vx, row1_bbox[1] + 18), "$", fill=hex_to_rgb(accent_hex), font=f_val)
    draw.text((vx + sw + 6, row1_bbox[1] + 18), p_str, fill=(255, 255, 255), font=f_val)

    # Row 2: Date Card
    row2_bbox = (cx0 + 44, cy0 + 295, cx1 - 44, cy0 + 375)
    r2_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    r2_draw = ImageDraw.Draw(r2_layer)
    r2_draw.rounded_rectangle(row2_bbox, radius=24, fill=(22, 24, 32, 230), outline=(255, 255, 255, 30), width=1)
    r2_draw.rounded_rectangle((row2_bbox[0], row2_bbox[1], row2_bbox[0] + 180, row2_bbox[3]), radius=24, fill=(35, 38, 50, 240))
    img.alpha_composite(r2_layer)

    draw = ImageDraw.Draw(img)
    draw.text((row2_bbox[0] + 55, row2_bbox[1] + 25), "Date", fill=(255, 255, 255), font=f_lbl)

    date_display = ath_date
    try:
        dt = datetime.fromisoformat(ath_date.replace("Z", "+00:00"))
        date_display = dt.strftime("%B %d, %Y")
    except Exception:
        pass

    f_date = get_font(30, weight="bold")
    dt_b = f_date.getbbox(date_display)
    dt_w = dt_b[2] - dt_b[0]
    dx = row2_bbox[0] + 180 + ((row2_bbox[2] - (row2_bbox[0] + 180)) - dt_w) // 2
    draw.text((dx, row2_bbox[1] + 22), date_display, fill=(255, 255, 255), font=f_date)

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
    """Template 4: Cryptocurrency conversion card with glassmorphism."""
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
    accent_hex = meta.get("color", "#345d9d")
    icon_path = meta.get("icon")

    # 1. Themed Background + Watermark Pattern
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)

    # 2. Glassmorphism Frame + Dark Container + Bottom Pill
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # Row 1: Selected Asset & Quantity
    row1_bbox = (cx0 + 44, cy0 + 60, cx1 - 44, cy0 + 164)
    r1_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    r1_draw = ImageDraw.Draw(r1_layer)
    r1_draw.rounded_rectangle(row1_bbox, radius=28, fill=(22, 24, 32, 230), outline=(255, 255, 255, 30), width=1)
    # Left pill for asset
    r1_draw.rounded_rectangle((row1_bbox[0], row1_bbox[1], row1_bbox[0] + 300, row1_bbox[3]), radius=28, fill=COLORS["pill_bg"])
    img.alpha_composite(r1_layer)

    # Icon inside left pill
    icon_w = 44
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA").resize((icon_w, icon_w), Image.Resampling.LANCZOS)
            img.alpha_composite(icon, (row1_bbox[0] + 20, row1_bbox[1] + 30))
        except Exception:
            icon_w = 0
    else:
        icon_w = 0

    font_crypto = get_font(30, weight="bold")
    draw = ImageDraw.Draw(img)
    draw.text((row1_bbox[0] + 20 + icon_w + 14, row1_bbox[1] + 33), meta["name"], fill=COLORS["navy_text"], font=font_crypto)

    # Right Amount
    font_amt = get_font(38, weight="extrabold")
    if crypto_amount < 1:
        amt_str = f"{crypto_amount:.4f}"
    elif crypto_amount == int(crypto_amount):
        amt_str = f"{crypto_amount:,.2f}"
    else:
        amt_str = f"{crypto_amount:,.4f}".rstrip("0").rstrip(".")

    ab = font_amt.getbbox(amt_str)
    aw = ab[2] - ab[0]
    draw.text((row1_bbox[2] - aw - 30, row1_bbox[1] + 30), amt_str, fill=(255, 255, 255), font=font_amt)

    # Middle Indicator: ⇅ Value
    mid_w = 176
    mid_h = 54
    mx0 = cx0 + (cx1 - cx0 - mid_w) // 2
    my0 = cy0 + 194
    mid_bbox = (mx0, my0, mx0 + mid_w, my0 + mid_h)

    m_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    m_draw = ImageDraw.Draw(m_layer)
    m_draw.rounded_rectangle(mid_bbox, radius=mid_h // 2, fill=(35, 38, 50, 240), outline=(255, 255, 255, 60), width=1)
    img.alpha_composite(m_layer)

    draw = ImageDraw.Draw(img)
    font_mid = get_font(20, weight="bold")
    mid_text = "⇅  Value"
    mb = font_mid.getbbox(mid_text)
    mw = mb[2] - mb[0]
    draw.text((mx0 + (mid_w - mw) // 2, my0 + 15), mid_text, fill=(255, 255, 255), font=font_mid)

    # Row 2: Converted Value & Fiat
    row2_bbox = (cx0 + 44, cy0 + 278, cx1 - 44, cy0 + 382)
    r2_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    r2_draw = ImageDraw.Draw(r2_layer)
    r2_draw.rounded_rectangle(row2_bbox, radius=28, fill=(22, 24, 32, 230), outline=(255, 255, 255, 30), width=1)
    # Right pill for fiat
    r2_draw.rounded_rectangle((row2_bbox[2] - 300, row2_bbox[1], row2_bbox[2], row2_bbox[3]), radius=28, fill=COLORS["pill_bg"])
    img.alpha_composite(r2_layer)

    # Left Converted Value: e.g. $15.44
    draw = ImageDraw.Draw(img)
    fiat_sign = fiat_meta.get("symbol", "$")
    fiat_dec = fiat_meta.get("decimals", 2)
    val_str = f"{fiat_sign}{format_price(fiat_value, decimals=fiat_dec)}"
    font_val = get_font(38, weight="extrabold")
    draw.text((row2_bbox[0] + 30, row2_bbox[1] + 30), val_str, fill=(255, 255, 255), font=font_val)

    # Fiat Name + Badge in Right Pill
    font_fiat = get_font(30, weight="bold")
    fb = font_fiat.getbbox(fiat_symbol)
    fw = fb[2] - fb[0]

    badge_size = 44
    total_fiat_w = fw + 16 + badge_size
    fiat_start_x = (row2_bbox[2] - 300) + (300 - total_fiat_w) // 2

    draw.text((fiat_start_x, row2_bbox[1] + 32), fiat_symbol, fill=COLORS["navy_text"], font=font_fiat)
    badge = get_fiat_badge(fiat_sign, size=badge_size)
    img.alpha_composite(badge, (fiat_start_x + fw + 16, row2_bbox[1] + 30))

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

# ==========================================
# 👻 Fun & Meme Visual Cards
# ==========================================

def render_satoshi_quote(quote: str, date_str: str = "Bitcoin Archives · 2009-2010") -> io.BytesIO:
    """Render dynamic Satoshi Nakamoto quote card in luminous Bitcoin Gold with coin watermark backdrop."""
    accent_hex = "#f7931a"
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox
    draw = ImageDraw.Draw(img)

    # Header badge
    pill_w = 340
    pill_h = 56
    pill_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pill_layer)
    p_draw.rounded_rectangle((cx0 + 40, cy0 + 36, cx0 + 40 + pill_w, cy0 + 36 + pill_h), radius=28, fill=COLORS["pill_bg"], outline=COLORS["pill_border"], width=1)
    img.alpha_composite(pill_layer)

    draw = ImageDraw.Draw(img)
    f_badge = get_font(21, weight="bold")
    draw.text((cx0 + 64, cy0 + 51), "SATOSHI ARCHIVES", fill=COLORS["navy_text"], font=f_badge)

    # Date / Source on right
    f_meta = get_font(15, weight="medium")
    mb = f_meta.getbbox(date_str)
    draw.text((cx1 - 40 - (mb[2] - mb[0]), cy0 + 53), date_str, fill=COLORS["gray_text"], font=f_meta)

    # Quote block in glass container
    q_bbox = (cx0 + 40, cy0 + 120, cx1 - 40, cy1 - 40)
    q_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    qd = ImageDraw.Draw(q_layer)
    qd.rounded_rectangle(q_bbox, radius=24, fill=(18, 20, 26, 230), outline=(247, 147, 26, 60), width=1)
    img.alpha_composite(q_layer)

    draw = ImageDraw.Draw(img)
    # Wrap text cleanly
    f_quote = get_font(26, weight="semibold")
    words = quote.split()
    lines = []
    curr = []
    max_w = (q_bbox[2] - q_bbox[0]) - 80
    for w in words:
        test_line = " ".join(curr + [w])
        tb = f_quote.getbbox(test_line)
        if (tb[2] - tb[0]) > max_w and curr:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    qy = q_bbox[1] + 46
    for line in lines[:7]:
        draw.text((q_bbox[0] + 40, qy), line, fill=(245, 245, 245), font=f_quote)
        qy += 44

    f_sub = get_font(17, weight="bold")
    draw.text((q_bbox[0] + 40, q_bbox[3] - 50), "— Satoshi Nakamoto, Creator of Bitcoin", fill=(247, 147, 26), font=f_sub)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_cope_card(symbol: str, price: float, atl_price: float, atl_date: str) -> io.BytesIO:
    """Render /cope card: calculates massive gain vs All-Time Low with coin watermark backdrop."""
    accent_hex = "#10b981"
    icon_path = COINS.get(symbol.upper(), {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), f"COPE METER · {symbol.upper()}", fill=(16, 185, 129), font=f_title)

    # Subtitle
    f_sub = get_font(16, weight="medium")
    draw.text((cx0 + 40, cy0 + 78), "When in doubt, zoom out! You survived the darkest capitulation.", fill=COLORS["gray_text"], font=f_sub)

    # Main Cope Stat Container
    m_bbox = (cx0 + 40, cy0 + 124, cx1 - 40, cy1 - 40)
    m_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(m_layer)
    md.rounded_rectangle(m_bbox, radius=24, fill=(16, 26, 22, 235), outline=(16, 185, 129, 70), width=1)
    img.alpha_composite(m_layer)

    draw = ImageDraw.Draw(img)
    # Gain vs ATL calculation
    gain_pct = ((price - atl_price) / max(0.000001, atl_price)) * 100.0
    f_gain_lbl = get_font(18, weight="bold")
    draw.text((m_bbox[0] + 40, m_bbox[1] + 36), "GAIN SINCE ALL-TIME LOW (ATL):", fill=COLORS["gray_text"], font=f_gain_lbl)

    f_gain_val = get_font(60, weight="extrabold")
    gain_str = f"+{gain_pct:,.1f}%" if gain_pct < 1000000 else f"+{gain_pct:,.0f}%"
    draw.text((m_bbox[0] + 40, m_bbox[1] + 74), gain_str, fill=(0, 230, 118), font=f_gain_val)

    # Stats Comparison Row
    f_stat_lbl = get_font(17, weight="semibold")
    f_stat_val = get_font(24, weight="bold")

    draw.text((m_bbox[0] + 40, m_bbox[1] + 180), "Live Current Price", fill=COLORS["gray_text"], font=f_stat_lbl)
    draw.text((m_bbox[0] + 40, m_bbox[1] + 210), f"${format_price(price)}", fill=(255, 255, 255), font=f_stat_val)

    draw.text((m_bbox[0] + 340, m_bbox[1] + 180), "All-Time Low (ATL)", fill=COLORS["gray_text"], font=f_stat_lbl)
    draw.text((m_bbox[0] + 340, m_bbox[1] + 210), f"${format_price(atl_price)}", fill=(255, 180, 50), font=f_stat_val)

    draw.text((m_bbox[0] + 620, m_bbox[1] + 180), "ATL Date Recorded", fill=COLORS["gray_text"], font=f_stat_lbl)
    draw.text((m_bbox[0] + 620, m_bbox[1] + 210), atl_date, fill=(200, 200, 200), font=f_stat_val)

    f_badge = get_font(16, weight="bold")
    draw.text((m_bbox[0] + 40, m_bbox[3] - 46), "DIAMOND HANDS VERDICT: You are vastly in profit compared to the true bottom.", fill=(16, 185, 129), font=f_badge)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_panic_card(symbol: str, price: float, change_24h: float) -> io.BytesIO:
    """Render /panic card: emergency panic meter & calming protocol with coin watermark backdrop."""
    accent_hex = "#ef4444"
    icon_path = COINS.get(symbol.upper(), {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), f"EMERGENCY PANIC CONSOLE · {symbol.upper()}", fill=(255, 75, 75), font=f_title)

    p_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    p_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(p_layer)
    pd.rounded_rectangle(p_bbox, radius=24, fill=(32, 16, 18, 235), outline=(255, 70, 70, 70), width=1)
    img.alpha_composite(p_layer)

    draw = ImageDraw.Draw(img)
    panic_score = min(99, max(45, int(abs(change_24h) * 7.5 + 40))) if change_24h < 0 else 25
    meter_text = f"PANIC INDEX: {panic_score} / 100 — {'EXTREME HYPERVENTILATION' if panic_score > 70 else 'ELEVATED ANXIETY'}"
    f_meter = get_font(24, weight="extrabold")
    draw.text((p_bbox[0] + 40, p_bbox[1] + 30), meter_text, fill=(255, 90, 90), font=f_meter)

    checklist = [
        "1. Put down the phone and take a deep breath.",
        "2. Close the 1-minute chart immediately.",
        "3. Remember: 1 BTC = 1 BTC. Volatility is the price of admission.",
        "4. Selling at the bottom transfers your coins to blackrock.",
        "5. Go outside, touch grass, and drink a glass of water."
    ]
    f_item = get_font(19, weight="semibold")
    iy = p_bbox[1] + 86
    for item in checklist:
        draw.text((p_bbox[0] + 40, iy), item, fill=(240, 240, 240), font=f_item)
        iy += 38

    f_alert = get_font(16, weight="bold")
    draw.text((p_bbox[0] + 40, p_bbox[3] - 44), "STATUS: DO NOT PANIC SELL. ALL MARKET DUMPS ARE TEMPORARY.", fill=(255, 180, 50), font=f_alert)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_wagmi_card(gainers: List[Dict[str, Any]]) -> io.BytesIO:
    """Render /wagmi card: top rocket market gainers with coin watermark backdrop."""
    accent_hex = "#8b5cf6"
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(30, weight="extrabold")
    draw.text((cx0 + 40, cy0 + 36), "WAGMI LEADERBOARD", fill=(167, 139, 250), font=f_title)

    f_sub = get_font(16, weight="medium")
    draw.text((cx0 + 40, cy0 + 78), "Today's Top Market Rockets · We're All Gonna Make It Anon", fill=COLORS["gray_text"], font=f_sub)

    w_bbox = (cx0 + 40, cy0 + 118, cx1 - 40, cy1 - 40)
    w_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(w_layer)
    wd.rounded_rectangle(w_bbox, radius=24, fill=(24, 20, 36, 235), outline=(139, 92, 246, 70), width=1)
    img.alpha_composite(w_layer)

    draw = ImageDraw.Draw(img)
    f_sym = get_font(22, weight="bold")
    f_p = get_font(21, weight="bold")
    f_g = get_font(22, weight="extrabold")

    ry = w_bbox[1] + 30
    for idx, g in enumerate(gainers[:5]):
        rank_str = f"#{idx + 1}"
        sym_str = f"{g.get('symbol', 'COIN')} — {g.get('name', 'Crypto')}"
        price_str = f"${format_price(g.get('current_price', 0.0))}"
        chg_val = g.get('change_24h', 0.0)
        chg_str = f"+{chg_val:.2f}%" if chg_val >= 0 else f"{chg_val:.2f}%"

        draw.text((w_bbox[0] + 30, ry), rank_str, fill=(167, 139, 250), font=f_sym)
        draw.text((w_bbox[0] + 90, ry), sym_str, fill=(255, 255, 255), font=f_sym)
        draw.text((w_bbox[0] + 460, ry), price_str, fill=(220, 220, 220), font=f_p)
        draw.text((w_bbox[0] + 640, ry), chg_str, fill=(0, 230, 118) if chg_val >= 0 else (255, 75, 75), font=f_g)
        ry += 52

    f_bottom = get_font(15, weight="bold")
    draw.text((w_bbox[0] + 30, w_bbox[3] - 40), "HOLD FAST · CYCLES REWARD THE PATIENT · GENERATIONAL WEALTH AHEAD", fill=(167, 139, 250), font=f_bottom)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_predict_card(symbol: str, price: float, prediction_target: float, predicted_gain: float, timeframe: str = "Next Cycle") -> io.BytesIO:
    """Render /predict card: 100% technical price prediction with coin watermark backdrop."""
    accent_hex = "#06b6d4"
    icon_path = COINS.get(symbol.upper(), {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), f"PRICE TARGET · {symbol.upper()}", fill=(6, 182, 212), font=f_title)

    pr_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    pr_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    prd = ImageDraw.Draw(pr_layer)
    prd.rounded_rectangle(pr_bbox, radius=24, fill=(16, 26, 32, 235), outline=(6, 182, 212, 70), width=1)
    img.alpha_composite(pr_layer)

    draw = ImageDraw.Draw(img)
    f_lbl = get_font(17, weight="bold")
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 30), f"PROJECTED TARGET ({timeframe.upper()}):", fill=COLORS["gray_text"], font=f_lbl)

    f_target = get_font(56, weight="extrabold")
    target_str = f"${format_price(prediction_target)} (+{predicted_gain:.1f}%)"
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 68), target_str, fill=(6, 182, 212), font=f_target)

    f_item = get_font(18, weight="semibold")
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 160), f"• Current Price: ${format_price(price)}", fill=(255, 255, 255), font=f_item)
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 196), "• Model Confidence: 99.9% (Calculated by Lunar Fib Wave Engine)", fill=(240, 240, 240), font=f_item)
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 232), "• Technical Verdict: GOD CANDLE IMMINENT · BEARS IN SHAMBLES", fill=(0, 230, 118), font=f_item)
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 268), "• Strategy: Accumulate dips, ignore noise, retire early.", fill=(240, 240, 240), font=f_item)

    f_disc = get_font(14, weight="medium")
    draw.text((pr_bbox[0] + 40, pr_bbox[3] - 40), "Disclaimer: Not financial advice. For entertainment and degen conviction only.", fill=COLORS["gray_text"], font=f_disc)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_didyouknow_card(symbol: str, fact_title: str, fact_body: str) -> io.BytesIO:
    """Render /didyouknow card: crypto trivia & historical lore with coin watermark backdrop."""
    accent_hex = "#3b82f6"
    icon_path = COINS.get(symbol.upper(), {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), f"DID YOU KNOW? · {symbol.upper()}", fill=(59, 130, 246), font=f_title)

    dy_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    dy_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dyd = ImageDraw.Draw(dy_layer)
    dyd.rounded_rectangle(dy_bbox, radius=24, fill=(16, 22, 34, 235), outline=(59, 130, 246, 70), width=1)
    img.alpha_composite(dy_layer)

    draw = ImageDraw.Draw(img)
    f_ht = get_font(24, weight="bold")
    draw.text((dy_bbox[0] + 40, dy_bbox[1] + 34), fact_title, fill=(255, 255, 255), font=f_ht)

    f_body = get_font(21, weight="medium")
    words = fact_body.split()
    lines = []
    curr = []
    max_w = (dy_bbox[2] - dy_bbox[0]) - 80
    for w in words:
        test_line = " ".join(curr + [w])
        tb = f_body.getbbox(test_line)
        if (tb[2] - tb[0]) > max_w and curr:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    by = dy_bbox[1] + 90
    for l in lines[:6]:
        draw.text((dy_bbox[0] + 40, by), l, fill=(230, 230, 230), font=f_body)
        by += 38

    f_tag = get_font(15, weight="bold")
    draw.text((dy_bbox[0] + 40, dy_bbox[3] - 44), "CURRENCING CRYPTO ENCYCLOPEDIA · VERIFIED BLOCKCHAIN TRIVIA", fill=(59, 130, 246), font=f_tag)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_me_profile_card(user_id: int, username: Optional[str], first_name: str, joined_at: Optional[str], total_lookups: int, favorite_coin: str) -> io.BytesIO:
    """Render /me user profile & intelligence recap card with luxury watermark backdrop."""
    accent_hex = "#6366f1"
    icon_path = COINS.get(favorite_coin.upper(), {}).get("icon") or COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), "USER INTELLIGENCE PROFILE", fill=(99, 102, 241), font=f_title)

    pr_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    pr_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    prd = ImageDraw.Draw(pr_layer)
    prd.rounded_rectangle(pr_bbox, radius=24, fill=(20, 20, 34, 235), outline=(99, 102, 241, 70), width=1)
    img.alpha_composite(pr_layer)

    draw = ImageDraw.Draw(img)
    f_name = get_font(36, weight="extrabold")
    user_tag = f"@{username}" if username else first_name
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 30), f"{first_name} ({user_tag})", fill=(255, 255, 255), font=f_name)

    f_lbl = get_font(17, weight="semibold")
    f_val = get_font(24, weight="bold")

    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 110), "Telegram ID", fill=COLORS["gray_text"], font=f_lbl)
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 140), str(user_id), fill=(220, 220, 220), font=f_val)

    draw.text((pr_bbox[0] + 340, pr_bbox[1] + 110), "Total Lookups", fill=COLORS["gray_text"], font=f_lbl)
    draw.text((pr_bbox[0] + 340, pr_bbox[1] + 140), f"{total_lookups} searches", fill=(0, 230, 118), font=f_val)

    draw.text((pr_bbox[0] + 620, pr_bbox[1] + 110), "Favorite Asset", fill=COLORS["gray_text"], font=f_lbl)
    draw.text((pr_bbox[0] + 620, pr_bbox[1] + 140), favorite_coin.upper(), fill=(247, 147, 26), font=f_val)

    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 200), "Member Joined", fill=COLORS["gray_text"], font=f_lbl)
    join_str = joined_at[:10] if joined_at else "Active Trader"
    draw.text((pr_bbox[0] + 40, pr_bbox[1] + 230), join_str, fill=(200, 200, 200), font=f_val)

    draw.text((pr_bbox[0] + 340, pr_bbox[1] + 200), "Trader Rank", fill=COLORS["gray_text"], font=f_lbl)
    rank_tier = "Whale" if total_lookups > 50 else ("Degen Master" if total_lookups > 15 else "Market Explorer")
    draw.text((pr_bbox[0] + 340, pr_bbox[1] + 230), rank_tier, fill=(99, 102, 241), font=f_val)

    draw.text((pr_bbox[0] + 620, pr_bbox[1] + 200), "Network Status", fill=COLORS["gray_text"], font=f_lbl)
    draw.text((pr_bbox[0] + 620, pr_bbox[1] + 230), "Verified Active", fill=(0, 230, 118), font=f_val)

    f_sub = get_font(15, weight="bold")
    draw.text((pr_bbox[0] + 40, pr_bbox[3] - 40), "PRO LEVEL METRICS · REAL-TIME TELEGRAM CRYPTO TRACKER", fill=(99, 102, 241), font=f_sub)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_firstseen_card(symbol: str, first_price: float, current_price: float, first_seen_time: str) -> io.BytesIO:
    """Render /firstseen card: tracking price change since first check with coin watermark backdrop."""
    accent_hex = "#ec4899"
    icon_path = COINS.get(symbol.upper(), {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), f"TIME CAPSULE · {symbol.upper()}", fill=(236, 72, 153), font=f_title)

    fs_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    fs_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fsd = ImageDraw.Draw(fs_layer)
    fsd.rounded_rectangle(fs_bbox, radius=24, fill=(30, 16, 26, 235), outline=(236, 72, 153, 70), width=1)
    img.alpha_composite(fs_layer)

    draw = ImageDraw.Draw(img)
    f_lbl = get_font(17, weight="bold")
    draw.text((fs_bbox[0] + 40, fs_bbox[1] + 30), "PRICE CHANGE SINCE YOUR FIRST LOOKUP:", fill=COLORS["gray_text"], font=f_lbl)

    diff_pct = ((current_price - first_price) / max(0.000001, first_price)) * 100.0
    f_chg = get_font(56, weight="extrabold")
    sign = "+" if diff_pct >= 0 else ""
    draw.text((fs_bbox[0] + 40, fs_bbox[1] + 68), f"{sign}{diff_pct:.2f}%", fill=(0, 230, 118) if diff_pct >= 0 else (255, 75, 75), font=f_chg)

    f_slbl = get_font(17, weight="semibold")
    f_sval = get_font(24, weight="bold")

    draw.text((fs_bbox[0] + 40, fs_bbox[1] + 160), "First Checked At", fill=COLORS["gray_text"], font=f_slbl)
    draw.text((fs_bbox[0] + 40, fs_bbox[1] + 190), f"${format_price(first_price)}", fill=(255, 255, 255), font=f_sval)

    draw.text((fs_bbox[0] + 340, fs_bbox[1] + 160), "Current Price Now", fill=COLORS["gray_text"], font=f_slbl)
    draw.text((fs_bbox[0] + 340, fs_bbox[1] + 190), f"${format_price(current_price)}", fill=(0, 230, 118), font=f_sval)

    draw.text((fs_bbox[0] + 620, fs_bbox[1] + 160), "First Seen Date", fill=COLORS["gray_text"], font=f_slbl)
    draw.text((fs_bbox[0] + 620, fs_bbox[1] + 190), first_seen_time, fill=(200, 200, 200), font=f_sval)

    f_sub = get_font(15, weight="bold")
    draw.text((fs_bbox[0] + 40, fs_bbox[3] - 40), "TIME CAPSULE ARCHIVE · PERSONALIZED CRYPTO MEMORY", fill=(236, 72, 153), font=f_sub)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_lookup_card(symbol: str, last_price: float, current_price: float, last_seen_time: str) -> io.BytesIO:
    """Render /lookup card: last check vs right now with coin watermark backdrop."""
    diff_val = current_price - last_price
    diff_pct = (diff_val / max(0.000001, last_price)) * 100.0
    accent_hex = "#10b981" if diff_pct >= 0 else "#ef4444"
    icon_path = COINS.get(symbol.upper(), {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), f"PRICE RECAP · {symbol.upper()}", fill=(20, 184, 166), font=f_title)

    lk_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    lk_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lkd = ImageDraw.Draw(lk_layer)
    lkd.rounded_rectangle(lk_bbox, radius=24, fill=(16, 28, 28, 235), outline=(20, 184, 166, 70), width=1)
    img.alpha_composite(lk_layer)

    draw = ImageDraw.Draw(img)
    diff_val = current_price - last_price
    diff_pct = (diff_val / max(0.000001, last_price)) * 100.0

    f_lbl = get_font(17, weight="bold")
    draw.text((lk_bbox[0] + 40, lk_bbox[1] + 30), "DELTA SINCE LAST CHECK:", fill=COLORS["gray_text"], font=f_lbl)

    f_chg = get_font(56, weight="extrabold")
    sign = "+" if diff_pct >= 0 else ""
    draw.text((lk_bbox[0] + 40, lk_bbox[1] + 68), f"{sign}{diff_pct:.2f}% (${sign}{format_price(abs(diff_val))})", fill=(0, 230, 118) if diff_pct >= 0 else (255, 75, 75), font=f_chg)

    f_slbl = get_font(17, weight="semibold")
    f_sval = get_font(24, weight="bold")

    draw.text((lk_bbox[0] + 40, lk_bbox[1] + 160), "Last Seen Price", fill=COLORS["gray_text"], font=f_slbl)
    draw.text((lk_bbox[0] + 40, lk_bbox[1] + 190), f"${format_price(last_price)}", fill=(255, 255, 255), font=f_sval)

    draw.text((lk_bbox[0] + 340, lk_bbox[1] + 160), "Current Price Now", fill=COLORS["gray_text"], font=f_slbl)
    draw.text((lk_bbox[0] + 340, lk_bbox[1] + 190), f"${format_price(current_price)}", fill=(0, 230, 118), font=f_sval)

    draw.text((lk_bbox[0] + 620, lk_bbox[1] + 160), "Timestamp of Last Check", fill=COLORS["gray_text"], font=f_slbl)
    draw.text((lk_bbox[0] + 620, lk_bbox[1] + 190), last_seen_time, fill=(200, 200, 200), font=f_sval)

    f_sub = get_font(15, weight="bold")
    draw.text((lk_bbox[0] + 40, lk_bbox[3] - 40), "PRICE COMPARISON DELTA · TRACKING EVERY MOMENTUM SHIFT", fill=(20, 184, 166), font=f_sub)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_chatvibe_card(chat_title: str, top_coins: List[Dict[str, Any]]) -> io.BytesIO:
    """Render /chatvibe card: group chat's top checked coins & vibe summary with coin watermark backdrop."""
    accent_hex = "#f59e0b"
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), "GROUP CHAT VIBE & MARKET PULSE", fill=(245, 158, 11), font=f_title)

    cv_bbox = (cx0 + 40, cy0 + 96, cx1 - 40, cy1 - 40)
    cv_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cvd = ImageDraw.Draw(cv_layer)
    cvd.rounded_rectangle(cv_bbox, radius=24, fill=(30, 24, 16, 235), outline=(245, 158, 11, 70), width=1)
    img.alpha_composite(cv_layer)

    draw = ImageDraw.Draw(img)
    f_ct = get_font(24, weight="bold")
    draw.text((cv_bbox[0] + 40, cv_bbox[1] + 28), f"Chat: {chat_title}", fill=(255, 255, 255), font=f_ct)

    f_sub = get_font(16, weight="semibold")
    draw.text((cv_bbox[0] + 40, cv_bbox[1] + 66), "MOST CHECKED CRYPTOCURRENCIES IN THIS CHAT:", fill=COLORS["gray_text"], font=f_sub)

    f_item = get_font(22, weight="bold")
    cy = cv_bbox[1] + 104
    if top_coins:
        for idx, item in enumerate(top_coins[:5]):
            rank_str = f"#{idx + 1}"
            sym = item.get("symbol", "BTC")
            cnt = item.get("count", 1)
            draw.text((cv_bbox[0] + 40, cy), rank_str, fill=(245, 158, 11), font=f_item)
            draw.text((cv_bbox[0] + 100, cy), sym, fill=(255, 255, 255), font=f_item)
            draw.text((cv_bbox[0] + 300, cy), f"{cnt} lookups", fill=(0, 230, 118), font=f_item)
            cy += 42
    else:
        draw.text((cv_bbox[0] + 40, cy + 20), "No coin checks recorded yet in this group! Use /btc, /sol, /eth to build the vibe.", fill=(200, 200, 200), font=f_item)

    f_foot = get_font(15, weight="bold")
    draw.text((cv_bbox[0] + 40, cv_bbox[3] - 40), "COMMUNITY SENTIMENT ENGINE · POWERED BY CURRENCING BOT", fill=(245, 158, 11), font=f_foot)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_daily_quote(quote: str, author: str, source: str = "Daily Crypto Intelligence") -> io.BytesIO:
    """Render /daily card: inspiring crypto thought in luminous royal violet with luxury watermark."""
    accent_hex = "#8b5cf6"
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox
    draw = ImageDraw.Draw(img)

    # Header badge
    pill_w = 360
    pill_h = 56
    pill_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pill_layer)
    p_draw.rounded_rectangle((cx0 + 40, cy0 + 36, cx0 + 40 + pill_w, cy0 + 36 + pill_h), radius=28, fill=COLORS["pill_bg"], outline=COLORS["pill_border"], width=1)
    img.alpha_composite(pill_layer)

    draw = ImageDraw.Draw(img)
    f_badge = get_font(21, weight="bold")
    draw.text((cx0 + 64, cy0 + 51), "DAILY CRYPTO THOUGHT", fill=COLORS["navy_text"], font=f_badge)

    # Date / Source on right
    f_meta = get_font(15, weight="medium")
    mb = f_meta.getbbox(source)
    draw.text((cx1 - 40 - (mb[2] - mb[0]), cy0 + 53), source, fill=COLORS["gray_text"], font=f_meta)

    # Quote block in glass container
    q_bbox = (cx0 + 40, cy0 + 120, cx1 - 40, cy1 - 40)
    q_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    qd = ImageDraw.Draw(q_layer)
    qd.rounded_rectangle(q_bbox, radius=24, fill=(22, 18, 34, 235), outline=(139, 92, 246, 70), width=1)
    img.alpha_composite(q_layer)

    draw = ImageDraw.Draw(img)
    f_quote = get_font(25, weight="semibold")
    words = quote.split()
    lines = []
    curr = []
    max_w = (q_bbox[2] - q_bbox[0]) - 80
    for w in words:
        test_line = " ".join(curr + [w])
        tb = f_quote.getbbox(test_line)
        if (tb[2] - tb[0]) > max_w and curr:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    qy = q_bbox[1] + 44
    for line in lines[:7]:
        draw.text((q_bbox[0] + 40, qy), line, fill=(245, 245, 245), font=f_quote)
        qy += 42

    f_sub = get_font(18, weight="bold")
    draw.text((q_bbox[0] + 40, q_bbox[3] - 50), f"— {author}", fill=(167, 139, 250), font=f_sub)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_meme_card(title: str, text: str, punchline: str = "") -> io.BytesIO:
    """Render /meme card: relatable degen meme & trading truth in emerald green with watermark."""
    accent_hex = "#10b981"
    icon_path = COINS.get("DOGE", {}).get("icon") or COINS.get("PEPE", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_glass_frame(img, accent_hex=accent_hex)
    cx0, cy0, cx1, cy1 = card_bbox
    draw = ImageDraw.Draw(img)

    # Title Banner
    f_title = get_font(28, weight="bold")
    draw.text((cx0 + 40, cy0 + 36), "CRYPTO MEME & DEGEN LORE", fill=(16, 185, 129), font=f_title)

    f_sub = get_font(16, weight="medium")
    draw.text((cx0 + 40, cy0 + 78), title, fill=(255, 255, 255), font=f_sub)

    # Content Container
    m_bbox = (cx0 + 40, cy0 + 116, cx1 - 40, cy1 - 40)
    m_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(m_layer)
    md.rounded_rectangle(m_bbox, radius=24, fill=(16, 28, 22, 235), outline=(16, 185, 129, 70), width=1)
    img.alpha_composite(m_layer)

    draw = ImageDraw.Draw(img)
    f_text = get_font(26, weight="semibold")
    words = text.split()
    lines = []
    curr = []
    max_w = (m_bbox[2] - m_bbox[0]) - 80
    for w in words:
        test_line = " ".join(curr + [w])
        tb = f_text.getbbox(test_line)
        if (tb[2] - tb[0]) > max_w and curr:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    my = m_bbox[1] + 46
    for line in lines[:5]:
        draw.text((m_bbox[0] + 40, my), line, fill=(240, 240, 240), font=f_text)
        my += 44

    if punchline:
        f_punch = get_font(20, weight="extrabold")
        draw.text((m_bbox[0] + 40, m_bbox[3] - 56), punchline, fill=(0, 230, 118), font=f_punch)
    else:
        f_foot = get_font(15, weight="bold")
        draw.text((m_bbox[0] + 40, m_bbox[3] - 44), "DEGEN ARCHIVE · ACCURACY RATING: 100% PAINFULLY TRUE", fill=(16, 185, 129), font=f_foot)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf
