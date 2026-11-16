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
    draw_rounded_rect, draw_footer, draw_card_frame
)

# ── Shared timestamp helper ────────────────────────────────────────────────────
def _stamp_timestamp(draw: ImageDraw.ImageDraw, card_bbox: tuple, now_utc: Optional[datetime] = None) -> None:
    """
    Stamp a compact live-rate timestamp at the bottom-right corner of a card.
    Format: 'Live · 16 Nov 2026 · 12:34 UTC'
    """
    if now_utc is None:
        now_utc = datetime.utcnow()
    ts_str = now_utc.strftime("Live · %d %b %Y · %H:%M UTC")
    cx0, cy0, cx1, cy1 = card_bbox
    f_ts = get_font(13, weight="medium")
    tb = f_ts.getbbox(ts_str)
    tw = tb[2] - tb[0]
    draw.text((cx1 - tw - 2, cy1 - 22), ts_str, fill=(90, 100, 125), font=f_ts)

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

    # 8. Live rate timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_market_overview(coins_data: List[Dict[str, Any]]) -> io.BytesIO:
    """Template 2: 3x3 Multi-Coin Market Overview — glassmorphism tiles, gradient backdrop, timestamp."""
    import numpy as np
    width, height = 1080, 660

    # ── Rich radial multi-stop gradient backdrop ───────────────────────────────
    # Deep space: dark navy at edges → vibrant electric blue-purple at center-top
    Y, X = np.ogrid[:height, :width]
    # Primary glow: electric indigo from top-left
    d1 = np.sqrt(((X - width * 0.25) / width) ** 2 + ((Y - height * 0.1) / height) ** 2)
    d1 = np.clip(d1 / 0.9, 0, 1)
    c_light1 = np.array([26, 20, 68], dtype=float)   # deep indigo
    c_dark1  = np.array([6, 7, 12],   dtype=float)   # near black
    grad1 = (c_light1 * (1 - d1[:, :, None]) + c_dark1 * d1[:, :, None]).astype(np.uint8)

    # Secondary glow: teal accent from bottom-right corner
    d2 = np.sqrt(((X - width * 0.82) / width) ** 2 + ((Y - height * 0.88) / height) ** 2)
    d2 = np.clip(d2 / 0.75, 0, 1)
    c_light2 = np.array([10, 48, 60], dtype=float)   # dark teal
    c_dark2  = np.array([4, 5, 10],   dtype=float)
    grad2 = (c_light2 * (1 - d2[:, :, None]) + c_dark2 * d2[:, :, None]).astype(np.uint8)

    # Blend the two gradients with screen-like additive mix capped at 255
    blended = np.clip(grad1.astype(int) + grad2.astype(int), 0, 255).astype(np.uint8)
    bg = Image.fromarray(blended, "RGB").convert("RGBA")

    # ── Subtle diagonal scanline texture overlay ───────────────────────────────
    scan_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sc_draw = ImageDraw.Draw(scan_layer)
    for y in range(0, height, 4):
        sc_draw.line([(0, y), (width, y)], fill=(255, 255, 255, 5), width=1)
    bg = Image.alpha_composite(bg, scan_layer)

    # ── Grid specs: 3×3, tiles a bit taller for timestamp ─────────────────────
    tile_w, tile_h = 316, 162
    gap_x, gap_y = 20, 18
    start_x = (width - 3 * tile_w - 2 * gap_x) // 2
    start_y = 44

    font_name  = get_font(20, weight="bold")
    font_price = get_font(31, weight="extrabold")
    font_chg   = get_font(19, weight="bold")
    font_ts    = get_font(11, weight="medium")

    display_coins = coins_data[:9]
    now_utc = datetime.utcnow()

    for idx, item in enumerate(display_coins):
        row = idx // 3
        col = idx % 3
        tx0 = start_x + col * (tile_w + gap_x)
        ty0 = start_y + row * (tile_h + gap_y)
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
        icon_path = meta.get("icon")

        # ── 1. Per-coin ambient bloom ──────────────────────────────────────────
        bloom = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bl_draw = ImageDraw.Draw(bloom)
        bl_draw.rounded_rectangle(
            (tx0 - 6, ty0 - 6, tx1 + 6, ty1 + 6),
            radius=28, fill=acc_rgb + (45,)
        )
        bloom = bloom.filter(ImageFilter.GaussianBlur(14))
        bg = Image.alpha_composite(bg, bloom)

        # ── 2. Glassmorphism card body ─────────────────────────────────────────
        # Frosted blur under card
        card_blur = bg.filter(ImageFilter.GaussianBlur(18))
        blur_mask = Image.new("L", (width, height), 0)
        bm_draw = ImageDraw.Draw(blur_mask)
        bm_draw.rounded_rectangle((tx0, ty0, tx1, ty1), radius=22, fill=255)
        bg = Image.composite(card_blur, bg, blur_mask)

        # Dark translucent card surface
        card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cd_draw = ImageDraw.Draw(card_layer)
        cd_draw.rounded_rectangle(
            (tx0, ty0, tx1, ty1),
            radius=22,
            fill=(14, 16, 22, 210),
            outline=acc_rgb + (170,),
            width=1
        )
        bg = Image.alpha_composite(bg, card_layer)

        # Specular highlight (top edge sheen)
        sheen_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(sheen_layer)
        sh_draw.rounded_rectangle(
            (tx0 + 1, ty0 + 1, tx1 - 1, ty0 + 28),
            radius=22,
            fill=(255, 255, 255, 18)
        )
        bg = Image.alpha_composite(bg, sheen_layer)

        # ── 3. Coin icon watermark (large, centered, low opacity) ──────────────
        if icon_path and os.path.exists(icon_path):
            try:
                wm_img = Image.open(icon_path).convert("RGBA").resize((86, 86), Image.Resampling.LANCZOS)
                _, _, _, a = wm_img.split()
                a_mask = a.point(lambda p: int(p * 0.08))
                wm_ghost = Image.composite(wm_img, Image.new("RGBA", (86, 86), (0, 0, 0, 0)), a_mask)
                bg.alpha_composite(wm_ghost, (tx0 + (tile_w - 86) // 2, ty0 + (tile_h - 86) // 2))
            except Exception:
                pass

        # ── 4. Top row: coin icon (32px) + name ───────────────────────────────
        icon_size = 32
        coin_name = meta["name"]
        nb = font_name.getbbox(coin_name)
        nw = nb[2] - nb[0]
        has_icon = bool(icon_path and os.path.exists(icon_path))
        total_top_w = (icon_size + 8 + nw) if has_icon else nw
        top_start_x = tx0 + (tile_w - total_top_w) // 2

        if has_icon:
            try:
                c_icon = Image.open(icon_path).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                bg.alpha_composite(c_icon, (top_start_x, ty0 + 14))
            except Exception:
                pass
            text_x = top_start_x + icon_size + 8
        else:
            text_x = top_start_x

        draw = ImageDraw.Draw(bg)
        draw.text((text_x, ty0 + 16), coin_name, fill=(255, 255, 255), font=font_name)

        # ── 5. Price row: accent '$' + white price ─────────────────────────────
        p_val = item.get("price", 0.0)
        p_str = format_price(p_val, decimals=meta.get("decimals", 2))
        sb = font_price.getbbox("$")
        sw = sb[2] - sb[0]
        pb = font_price.getbbox(p_str)
        pw = pb[2] - pb[0]
        total_p_w = sw + 4 + pw
        px = tx0 + (tile_w - total_p_w) // 2
        py = ty0 + 56
        draw.text((px, py), "$", fill=acc_rgb, font=font_price)
        draw.text((px + sw + 4, py), p_str, fill=(255, 255, 255), font=font_price)

        # ── 6. 24h change ─────────────────────────────────────────────────────
        chg = item.get("change_24h", 0.0)
        chg_col = COLORS["green"] if chg >= 0 else COLORS["red"]
        chg_str = format_change(chg)
        cb = font_chg.getbbox(chg_str)
        cw = cb[2] - cb[0]
        draw.text((tx0 + (tile_w - cw) // 2, ty0 + 104), chg_str, fill=chg_col, font=font_chg)

        # ── 7. Timestamp bottom-right of each tile ─────────────────────────────
        ts_str = now_utc.strftime("%d %b · %H:%M UTC")
        tsb = font_ts.getbbox(ts_str)
        tsw = tsb[2] - tsb[0]
        draw.text((tx1 - tsw - 10, ty1 - 17), ts_str, fill=(90, 100, 125), font=font_ts)

    # ── Bottom branded footer pill ─────────────────────────────────────────────
    draw_footer(bg, y_pos=636)

    buf = io.BytesIO()
    bg.convert("RGB").save(buf, format="PNG", quality=96)
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

    _stamp_timestamp(draw, card_bbox)

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

    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

# ==========================================
# 👻 Fun & Meme Visual Cards
# ==========================================

def render_satoshi_quote(quote: str, date_str: str = "Bitcoin Archives · 2009-2010") -> io.BytesIO:
    """Render dynamic Satoshi Nakamoto quote card matching reference layout."""
    accent_hex = "#f7931a"
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol="BTC")
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "SATOSHI ARCHIVES", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 112), date_str, fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # 2. Quote text
    f_quote = get_font(26, weight="bold")
    words = quote.split()
    lines = []
    curr = []
    max_w = (cx1 - cx0) - 88
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

    line_h = 42
    total_h = len(lines) * line_h
    start_y = cy0 + 175 + ((cy1 - cy0 - 240) - total_h) // 2
    for idx, line in enumerate(lines):
        draw.text((cx0 + 44, start_y + idx * line_h), line, fill=(255, 255, 255), font=f_quote)

    # 3. Signature
    draw.text((cx0 + 44, cy1 - 50), "— Satoshi Nakamoto, Creator of Bitcoin", fill=(247, 147, 26), font=get_font(20, weight="bold"))

    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_cope_card(symbol: str, price: float, atl_price: float, atl_date: str) -> io.BytesIO:
    """Render /cope card matching user reference layout."""
    sym = symbol.upper()
    meta = COINS.get(sym, {"name": sym, "color": "#10b981", "icon": None, "decimals": 2})
    accent_hex = meta.get("color", "#10b981")
    icon_path = meta.get("icon")

    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol=sym)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # Header
    draw.text((cx0 + 44, cy0 + 44), "COPE METER", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 112), "When in doubt, zoom out — you survived the capitulation", fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # Section Label
    draw.text((cx0 + 44, cy0 + 184), "GAIN SINCE ALL-TIME LOW (ATL)", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    gain_pct = ((price - atl_price) / max(0.000001, atl_price)) * 100.0
    gain_str = f"+{gain_pct:,.1f}%" if gain_pct < 1000000 else f"+{gain_pct:,.0f}%"
    draw.text((cx0 + 44, cy0 + 212), gain_str, fill=(0, 230, 118), font=get_font(56, weight="extrabold"))

    # Stats row
    f_lbl = get_font(14, weight="bold")
    f_val = get_font(32, weight="extrabold")

    draw.text((cx0 + 44, cy0 + 310), "CURRENT PRICE", fill=(56, 189, 248), font=f_lbl)
    draw.text((cx0 + 44, cy0 + 338), f"${format_price(price, decimals=meta.get('decimals', 2))}", fill=(255, 255, 255), font=f_val)

    draw.text((cx0 + 360, cy0 + 310), "ALL-TIME LOW", fill=(56, 189, 248), font=f_lbl)
    draw.text((cx0 + 360, cy0 + 338), f"${format_price(atl_price, decimals=meta.get('decimals', 2))}", fill=(255, 180, 50), font=f_val)

    draw.text((cx0 + 640, cy0 + 310), "ATL DATE", fill=(56, 189, 248), font=f_lbl)
    draw.text((cx0 + 640, cy0 + 338), str(atl_date)[:10], fill=(200, 210, 225), font=f_val)

    # Conviction verdict
    draw.text((cx0 + 44, cy1 - 42), "this is what diamond hands feel like.", fill=(125, 133, 150), font=get_font(16, weight="medium"))

    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_panic_card(symbol: str, price: float, change_24h: float) -> io.BytesIO:
    """Render /panic card matching exact user reference image."""
    sym = symbol.upper()
    meta = COINS.get(sym, {"name": sym, "color": "#f7931a", "icon": None, "decimals": 2})
    accent_hex = meta.get("color", "#f7931a")
    icon_path = meta.get("icon")

    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol=sym)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header: DON'T PANIC.
    draw.text((cx0 + 44, cy0 + 44), "DON'T", fill=(255, 255, 255), font=get_font(56, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 106), "PANIC.", fill=(56, 189, 248), font=get_font(56, weight="extrabold"))

    # 2. Section Label: RIGHT NOW
    draw.text((cx0 + 44, cy0 + 196), "RIGHT NOW", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    # 3. Price
    p_str = f"${format_price(price, decimals=meta.get('decimals', 2))}"
    draw.text((cx0 + 44, cy0 + 224), p_str, fill=(255, 255, 255), font=get_font(54, weight="extrabold"))

    # 4. 24H Change
    chg_sign = "+" if change_24h >= 0 else ""
    chg_str = f"{chg_sign}{change_24h:.2f}% (24H)"
    chg_col = (0, 230, 118) if change_24h >= 0 else (255, 65, 65)
    draw.text((cx0 + 44, cy0 + 300), chg_str, fill=chg_col, font=get_font(26, weight="bold"))

    # 5. Conviction subtext
    draw.text((cx0 + 44, cy0 + 388), "this is what conviction feels like", fill=(240, 240, 240), font=get_font(22, weight="semibold"))
    draw.text((cx0 + 44, cy0 + 434), "you've got this.", fill=(125, 133, 150), font=get_font(15, weight="medium"))

    # 6. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_wagmi_card(gainers: List[Dict[str, Any]]) -> io.BytesIO:
    """Render /wagmi rocket leaderboard card matching user reference image."""
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex="#258bd2", icon_path=icon_path)
    img, card_bbox = draw_card_frame(img)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "WAGMI", fill=(0, 230, 118), font=get_font(56, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 116), "good vibes, green candles", fill=(255, 255, 255), font=get_font(22, weight="medium"))

    # 2. Section Label
    draw.text((cx0 + 44, cy0 + 172), "TOP GAINERS — LAST 24H", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    # 3. Top Gainers List
    f_sym = get_font(28, weight="bold")
    f_chg = get_font(30, weight="extrabold")
    y = cy0 + 224

    if not gainers:
        gainers = [{"symbol": "BTC", "name": "Bitcoin", "change_24h": 5.2}]

    for idx, g in enumerate(gainers[:3]):
        sym = g.get("symbol", "").upper()
        name = g.get("name", sym)
        chg = g.get("change_24h", 0.0)
        rank_name = f"{idx + 1}.   {name} ({sym})"
        chg_sign = "+" if chg >= 0 else ""
        chg_str = f"{chg_sign}{chg:.2f}%"
        draw.text((cx0 + 44, y), rank_name, fill=(255, 255, 255), font=f_sym)

        tb = f_chg.getbbox(chg_str)
        tw = tb[2] - tb[0]
        draw.text((cx1 - 60 - tw, y), chg_str, fill=(0, 230, 118), font=f_chg)
        y += 62

    # 4. Footer
    draw.text((cx0 + 44, cy1 - 42), "we're so back.", fill=(125, 133, 150), font=get_font(16, weight="medium"))

    # 5. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_predict_card(
    symbol: str,
    price: float,
    prediction_target: float,
    predicted_gain: float,
    timeframe: str = "Dinner Time"
) -> io.BytesIO:
    """Render /predict price prediction card matching user reference image."""
    sym = symbol.upper()
    meta = COINS.get(sym, {"name": sym, "color": "#f7931a", "icon": None, "decimals": 2})
    accent_hex = meta.get("color", "#f7931a")
    icon_path = meta.get("icon")

    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol=sym)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "PRICE PREDICTION", fill=(255, 255, 255), font=get_font(48, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 104), f"current: ${format_price(price, decimals=meta.get('decimals', 2))}", fill=(140, 148, 165), font=get_font(18, weight="medium"))

    # 2. Target Section
    draw.text((cx0 + 44, cy0 + 164), "TARGET PRICE", fill=(56, 189, 248), font=get_font(14, weight="bold"))
    t_str = f"${format_price(prediction_target, decimals=meta.get('decimals', 2))}"
    draw.text((cx0 + 44, cy0 + 192), t_str, fill=(0, 230, 118), font=get_font(54, weight="extrabold"))

    gain_sign = "+" if predicted_gain >= 0 else ""
    draw.text((cx0 + 44, cy0 + 264), f"{gain_sign}{predicted_gain:.2f}%", fill=(0, 230, 118), font=get_font(26, weight="bold"))

    # 3. Confidence & Timeframe
    draw.text((cx0 + 44, cy0 + 322), f"BY {timeframe.upper()}", fill=(56, 189, 248), font=get_font(14, weight="bold"))
    conf = min(99.9, max(85.0, 90.0 + (price % 9.9)))
    draw.text((cx0 + 44, cy0 + 348), f"{conf:.1f}% confident", fill=(255, 255, 255), font=get_font(28, weight="bold"))
    draw.text((cx0 + 44, cy0 + 396), "Confirmed by my dog", fill=(200, 210, 225), font=get_font(20, weight="medium"))

    # 4. Disclaimer
    draw.text((cx0 + 44, cy1 - 36), "100% NOT financial advice. For entertainment only.", fill=(110, 120, 135), font=get_font(14, weight="medium"))

    # 5. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_didyouknow_card(symbol: str, fact_title: str, fact_body: str) -> io.BytesIO:
    """Render /didyouknow & /dyk card matching user reference image."""
    sym = symbol.upper()
    meta = COINS.get(sym, {"name": sym, "color": "#f7931a", "icon": None})
    accent_hex = meta.get("color", "#f7931a")
    icon_path = meta.get("icon")

    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol=sym)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "DID YOU KNOW?", fill=(255, 255, 255), font=get_font(50, weight="extrabold"))

    # 2. Fact Body Centered Vertically
    f_body = get_font(26, weight="bold")
    words = fact_body.split()
    lines = []
    curr = []
    max_w = (cx1 - cx0) - 88
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

    line_h = 44
    total_text_h = len(lines) * line_h
    start_y = cy0 + 180 + ((cy1 - cy0 - 200) - total_text_h) // 2
    for idx, line in enumerate(lines):
        draw.text((cx0 + 44, start_y + idx * line_h), line, fill=(255, 255, 255), font=f_body)

    # 3. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_me_profile_card(
    user_id: int,
    username: Optional[str],
    first_name: str,
    joined_at: Optional[str],
    total_lookups: int,
    favorite_coin: str
) -> io.BytesIO:
    """Render /me user profile & intelligence recap card matching user reference image."""
    icon_path = COINS.get(favorite_coin.upper(), {}).get("icon") or COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex="#258bd2", icon_path=icon_path)
    img, card_bbox = draw_card_frame(img)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "YOUR CRYPTO RECAP", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    sub_title = f"@{username} — all-time stats" if username else f"{first_name} — all-time stats"
    draw.text((cx0 + 44, cy0 + 112), sub_title, fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # 2. Left Column: Lookups & Vibe
    draw.text((cx0 + 44, cy0 + 176), "YOU LOOKED UP", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    num_str = str(total_lookups)
    f_num = get_font(58, weight="extrabold")
    draw.text((cx0 + 44, cy0 + 204), num_str, fill=(255, 255, 255), font=f_num)
    nb = f_num.getbbox(num_str)
    nw = nb[2] - nb[0]
    draw.text((cx0 + 44 + nw + 12, cy0 + 228), "TIMES", fill=(120, 128, 145), font=get_font(26, weight="bold"))

    draw.text((cx0 + 44, cy0 + 348), "YOUR VIBE", fill=(56, 189, 248), font=get_font(14, weight="bold"))
    vibe = "Crypto Curious" if total_lookups < 10 else ("Alpha Degen" if total_lookups < 50 else "Diamond Hand Legend")
    draw.text((cx0 + 44, cy0 + 380), f'"{vibe}"', fill=(255, 255, 255), font=get_font(28, weight="bold"))

    # 3. Right Column: Top 5
    draw.text((cx0 + 460, cy0 + 176), "YOUR TOP 5", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    fav = favorite_coin.lower() if favorite_coin else "btc"
    top_cmds = [
        (f"/{fav}", max(1, total_lookups // 2)),
        ("/satoshi", max(1, total_lookups // 3)),
        ("/wagmi", max(1, total_lookups // 4)),
        ("/top", max(1, total_lookups // 5)),
        ("/panic", max(1, total_lookups // 6)),
    ]
    f_cmd = get_font(26, weight="bold")
    y = cy0 + 214
    for idx, (cmd, cnt) in enumerate(top_cmds):
        draw.text((cx0 + 460, y), f"{idx + 1}.   {cmd}", fill=(255, 255, 255), font=f_cmd)
        cnt_str = str(cnt)
        cb = f_cmd.getbbox(cnt_str)
        draw.text((cx1 - 60 - (cb[2] - cb[0]), y), cnt_str, fill=(0, 230, 118), font=f_cmd)
        y += 44

    # 4. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_firstseen_card(symbol: str, first_price: float, current_price: float, first_seen_time: str) -> io.BytesIO:
    """Render /firstseen card matching user reference image layout."""
    sym = symbol.upper()
    meta = COINS.get(sym, {"name": sym, "color": "#ec4899", "icon": None, "decimals": 2})
    accent_hex = meta.get("color", "#ec4899")
    icon_path = meta.get("icon")

    img = get_themed_background(1024, 640, accent_hex=accent_hex, icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol=sym)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # Header
    draw.text((cx0 + 44, cy0 + 44), "FIRST SEEN", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 112), f"Time capsule tracking since your initial check on {first_seen_time}", fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # Section Label
    draw.text((cx0 + 44, cy0 + 184), "PRICE DELTA SINCE FIRST SEEN", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    diff_pct = ((current_price - first_price) / max(0.000001, first_price)) * 100.0
    sign = "+" if diff_pct >= 0 else ""
    draw.text((cx0 + 44, cy0 + 212), f"{sign}{diff_pct:.2f}%", fill=(0, 230, 118) if diff_pct >= 0 else (255, 65, 65), font=get_font(56, weight="extrabold"))

    f_lbl = get_font(14, weight="bold")
    f_val = get_font(32, weight="extrabold")

    draw.text((cx0 + 44, cy0 + 310), "FIRST CHECKED", fill=(56, 189, 248), font=f_lbl)
    draw.text((cx0 + 44, cy0 + 338), f"${format_price(first_price, decimals=meta.get('decimals', 2))}", fill=(255, 255, 255), font=f_val)

    draw.text((cx0 + 460, cy0 + 310), "CURRENT PRICE", fill=(56, 189, 248), font=f_lbl)
    draw.text((cx0 + 460, cy0 + 338), f"${format_price(current_price, decimals=meta.get('decimals', 2))}", fill=(0, 230, 118), font=f_val)

    draw.text((cx0 + 44, cy1 - 42), "every great portfolio starts with a single lookup.", fill=(125, 133, 150), font=get_font(16, weight="medium"))

    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_lookup_card(symbol: str, last_price: float, current_price: float, last_seen_time: str) -> io.BytesIO:
    """Render /lookup price comparison card matching user reference image."""
    sym = symbol.upper()
    diff_val = current_price - last_price
    diff_pct = (diff_val / max(0.000001, last_price)) * 100.0

    icon_path = COINS.get(sym, {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex="#258bd2", icon_path=icon_path)
    img, card_bbox = draw_card_frame(img)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "LAST LOOKUP", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    sub_text = f"{sym} — {last_seen_time}"
    draw.text((cx0 + 44, cy0 + 112), sub_text, fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # 2. Left Column: Price Then & Price Now
    draw.text((cx0 + 44, cy0 + 184), "PRICE THEN", fill=(56, 189, 248), font=get_font(14, weight="bold"))
    draw.text((cx0 + 44, cy0 + 212), f"${format_price(last_price)}", fill=(160, 168, 185), font=get_font(42, weight="bold"))

    draw.text((cx0 + 44, cy0 + 292), "PRICE NOW", fill=(56, 189, 248), font=get_font(14, weight="bold"))
    draw.text((cx0 + 44, cy0 + 320), f"${format_price(current_price)}", fill=(255, 255, 255), font=get_font(42, weight="extrabold"))

    # 3. Right Column: Change % and Change $
    chg_col = (0, 230, 118) if diff_pct >= 0 else (255, 65, 65)
    draw.text((cx0 + 480, cy0 + 184), "CHANGE", fill=chg_col, font=get_font(14, weight="bold"))

    sign_str = "+" if diff_pct >= 0 else ""
    pct_str = f"{sign_str}{diff_pct:.2f}%"
    draw.text((cx0 + 480, cy0 + 212), pct_str, fill=chg_col, font=get_font(52, weight="extrabold"))

    dollar_sign = "+$" if diff_val >= 0 else "-$"
    dollar_str = f"{dollar_sign}{format_price(abs(diff_val))}"
    draw.text((cx0 + 480, cy0 + 292), dollar_str, fill=chg_col, font=get_font(42, weight="extrabold"))

    # 4. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_chatvibe_card(chat_title: str, top_coins: List[Dict[str, Any]]) -> io.BytesIO:
    """Render /chatvibe group market pulse card matching user reference image."""
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex="#258bd2", icon_path=icon_path)
    img, card_bbox = draw_card_frame(img)
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "CHAT'S VIBE", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 112), "what this group's been looking up", fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # 2. Section Label
    draw.text((cx0 + 44, cy0 + 176), "TOP TICKERS", fill=(56, 189, 248), font=get_font(14, weight="bold"))

    # 3. Tickers List
    f_sym = get_font(30, weight="bold")
    f_pct = get_font(30, weight="extrabold")
    y = cy0 + 224

    if not top_coins:
        top_coins = [{"symbol": "BTC", "count": 1}]

    total_count = sum(c.get("count", 1) for c in top_coins) or 1
    for idx, c in enumerate(top_coins[:4]):
        sym = c.get("symbol", "btc").lower()
        ticker = f"/{sym}"
        pct = int(round((c.get("count", 1) / total_count) * 100))
        pct_str = f"{pct}%"

        draw.text((cx0 + 44, y), f"{idx + 1}.   {ticker}", fill=(255, 255, 255), font=f_sym)
        tb = f_pct.getbbox(pct_str)
        tw = tb[2] - tb[0]
        draw.text((cx1 - 60 - tw, y), pct_str, fill=(0, 230, 118), font=f_pct)
        y += 62

    # 4. Live Timestamp
    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_daily_quote(quote: str, author: str, source: str = "Daily Crypto Intelligence") -> io.BytesIO:
    """Render /daily card matching reference floating card layout."""
    icon_path = COINS.get("BTC", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex="#8b5cf6", icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol="BTC")
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "DAILY THOUGHT", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 112), source, fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # 2. Quote text centered
    f_quote = get_font(26, weight="bold")
    words = quote.split()
    lines = []
    curr = []
    max_w = (cx1 - cx0) - 88
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

    line_h = 42
    total_h = len(lines) * line_h
    start_y = cy0 + 175 + ((cy1 - cy0 - 240) - total_h) // 2
    for idx, line in enumerate(lines):
        draw.text((cx0 + 44, start_y + idx * line_h), line, fill=(255, 255, 255), font=f_quote)

    # 3. Attribution
    draw.text((cx0 + 44, cy1 - 50), f"— {author}", fill=(167, 139, 250), font=get_font(20, weight="bold"))

    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf

def render_meme_card(title: str, text: str, punchline: str = "") -> io.BytesIO:
    """Render /meme card matching reference floating card layout."""
    icon_path = COINS.get("DOGE", {}).get("icon") or COINS.get("PEPE", {}).get("icon")
    img = get_themed_background(1024, 640, accent_hex="#10b981", icon_path=icon_path)
    img, card_bbox = draw_card_frame(img, coin_symbol="DOGE")
    cx0, cy0, cx1, cy1 = card_bbox

    draw = ImageDraw.Draw(img)

    # 1. Header
    draw.text((cx0 + 44, cy0 + 44), "CRYPTO MEME", fill=(255, 255, 255), font=get_font(52, weight="extrabold"))
    draw.text((cx0 + 44, cy0 + 112), title, fill=(140, 148, 165), font=get_font(20, weight="medium"))

    # 2. Meme text
    f_text = get_font(26, weight="bold")
    words = text.split()
    lines = []
    curr = []
    max_w = (cx1 - cx0) - 88
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

    line_h = 42
    total_h = len(lines) * line_h
    start_y = cy0 + 175 + ((cy1 - cy0 - 240) - total_h) // 2
    for idx, line in enumerate(lines):
        draw.text((cx0 + 44, start_y + idx * line_h), line, fill=(255, 255, 255), font=f_text)

    # 3. Punchline
    if punchline:
        draw.text((cx0 + 44, cy1 - 50), punchline, fill=(0, 230, 118), font=get_font(22, weight="extrabold"))
    else:
        draw.text((cx0 + 44, cy1 - 42), "we live in a simulation.", fill=(125, 133, 150), font=get_font(16, weight="medium"))

    _stamp_timestamp(draw, card_bbox)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf
