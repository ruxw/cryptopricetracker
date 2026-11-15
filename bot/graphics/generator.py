import os
import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from bot.config import BOT_USERNAME
from bot.graphics.assets import (
    ASSETS_DIR, COLORS, get_font, hex_to_rgb
)

BG_TEMPLATE_PATH = os.path.join(ASSETS_DIR, "background.png")
FOOTER_PATH = os.path.join(ASSETS_DIR, "currencing_footer.png")
CURRENCING_LOGO_PATH = os.path.join(ASSETS_DIR, "currencing_logo.png")

_icon_cache: dict[int, Image.Image] = {}

def get_currencing_icon(size: int = 24) -> Optional[Image.Image]:
    """Load and cache the Currencing logo icon for bottom pills."""
    if size in _icon_cache:
        return _icon_cache[size]
    if os.path.exists(CURRENCING_LOGO_PATH):
        try:
            im = Image.open(CURRENCING_LOGO_PATH).convert("RGBA")
            im = im.resize((size, size), Image.Resampling.LANCZOS)
            _icon_cache[size] = im
            return im
        except Exception:
            pass
    return None

def get_themed_background(
    width: int = 1024,
    height: int = 640,
    accent_hex: str = "#f7931a",
    icon_path: Optional[str] = None
) -> Image.Image:
    """Generate radiant ambient gradient background with repeating watermark pattern."""
    acc_rgb = hex_to_rgb(accent_hex)
    
    # Generate rich harmonic gradient
    # Top-center/left is luminous accent glow, edges/corners are deep shade
    r, g, b = acc_rgb
    c1 = np.array([min(255, int(r * 0.95 + 15)), min(255, int(g * 0.95 + 10)), min(255, int(b * 0.95 + 10))], dtype=float)
    c2 = np.array([max(6, int(r * 0.22)), max(6, int(g * 0.22)), max(6, int(b * 0.22))], dtype=float)

    Y, X = np.ogrid[:height, :width]
    # Radial falloff
    dist = np.sqrt(((X - width * 0.38) / width)**2 + ((Y - height * 0.22) / height)**2)
    dist = np.clip(dist / 1.12, 0, 1)

    grad = (c1[None, None, :] * (1 - dist[:, :, None]) + c2[None, None, :] * dist[:, :, None]).astype(np.uint8)
    base = Image.fromarray(grad, "RGB").convert("RGBA")

    # Watermark tiling
    if icon_path and os.path.exists(icon_path):
        try:
            icon = Image.open(icon_path).convert("RGBA")
            wm_size = 52
            icon = icon.resize((wm_size, wm_size), Image.Resampling.LANCZOS)
            _, _, _, a = icon.split()
            # 13% opacity white watermark
            alpha_mask = a.point(lambda p: int(p * 0.13))
            white_img = Image.new("RGBA", (wm_size, wm_size), (255, 255, 255, 255))
            watermark = Image.composite(white_img, Image.new("RGBA", (wm_size, wm_size), (0, 0, 0, 0)), alpha_mask)

            step_x, step_y = 110, 95
            for row, y in enumerate(range(-30, height + 60, step_y)):
                offset = (step_x // 2) if (row % 2 == 1) else 0
                for x in range(-30 + offset, width + 60, step_x):
                    base.alpha_composite(watermark, (x, y))
        except Exception:
            pass

    return base

def get_base_background(width: int = 1024, height: int = 640) -> Image.Image:
    """Return background (uses themed background or default template)."""
    return get_themed_background(width, height, accent_hex="#f7931a")

def draw_glass_frame(
    img: Image.Image,
    glass_bbox: Tuple[int, int, int, int] = (44, 34, 980, 582),
    glass_rad: int = 44,
    card_margin: int = 34,
    card_rad: int = 28,
    accent_hex: str = "#f7931a",
    bot_pill_text: Optional[str] = None
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Draw realistic frosted glassmorphism outer plate + dark inner card + bottom branded pill.
    Returns (img, card_bbox).
    """
    if bot_pill_text is None:
        bot_pill_text = f"t.me/{BOT_USERNAME}"

    width, height = img.size
    gx0, gy0, gx1, gy1 = glass_bbox

    # 1. Glass Drop Shadow
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rounded_rectangle((gx0, gy0 + 10, gx1, gy1 + 10), radius=glass_rad, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img = Image.alpha_composite(img, shadow)

    # 2. Frosted Blur through glass plate
    bg_blurred = img.filter(ImageFilter.GaussianBlur(24))
    glass_mask = Image.new("L", (width, height), 0)
    m_draw = ImageDraw.Draw(glass_mask)
    m_draw.rounded_rectangle(glass_bbox, radius=glass_rad, fill=255)
    img = Image.composite(bg_blurred, img, glass_mask)

    # 3. Frosted Translucent Glass Overlay + Specular Rim
    glass_sheen = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gs_draw = ImageDraw.Draw(glass_sheen)
    gs_draw.rounded_rectangle(glass_bbox, radius=glass_rad, fill=(255, 255, 255, 28), outline=(255, 255, 255, 95), width=2)
    img = Image.alpha_composite(img, glass_sheen)

    # 4. Inner Dark Container Card
    cx0 = gx0 + card_margin
    cy0 = gy0 + card_margin
    cx1 = gx1 - card_margin
    cy1 = gy1 - card_margin
    card_bbox = (cx0, cy0, cx1, cy1)

    c_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cs_draw = ImageDraw.Draw(c_shadow)
    cs_draw.rounded_rectangle((cx0, cy0 + 4, cx1, cy1 + 4), radius=card_rad, fill=(0, 0, 0, 150))
    c_shadow = c_shadow.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img, c_shadow)

    card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_layer)
    c_draw.rounded_rectangle(card_bbox, radius=card_rad, fill=(12, 13, 17, 246), outline=(255, 255, 255, 22), width=1)
    img = Image.alpha_composite(img, card_layer)

    # 5. Bottom Branded Pill Badge (t.me/CurrencingBot with Currencing brand icon)
    pill_w = 276
    pill_h = 48
    px0 = (width - pill_w) // 2
    py0 = gy1 - (pill_h // 2)
    px1 = px0 + pill_w
    py1 = py0 + pill_h
    b_pill_bbox = (px0, py0, px1, py1)

    bp_shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bps_draw = ImageDraw.Draw(bp_shadow)
    bps_draw.rounded_rectangle((px0, py0 + 3, px1, py1 + 3), radius=pill_h // 2, fill=(0, 0, 0, 100))
    bp_shadow = bp_shadow.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img, bp_shadow)

    bp_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bp_draw = ImageDraw.Draw(bp_layer)
    acc_rgb = hex_to_rgb(accent_hex)
    bp_draw.rounded_rectangle(b_pill_bbox, radius=pill_h // 2, fill=acc_rgb + (255,), outline=(255, 255, 255, 140), width=1)
    img = Image.alpha_composite(img, bp_layer)

    draw = ImageDraw.Draw(img)
    f_bot = get_font(19, weight="bold")
    bt_bbox = f_bot.getbbox(bot_pill_text)
    btw = bt_bbox[2] - bt_bbox[0]
    bth = bt_bbox[3] - bt_bbox[1]

    logo_icon = get_currencing_icon(24)
    if logo_icon:
        spacing = 8
        content_w = 24 + spacing + btw
        start_x = px0 + (pill_w - content_w) // 2
        logo_y = py0 + (pill_h - 24) // 2
        img.alpha_composite(logo_icon, (start_x, logo_y))
        text_x = start_x + 24 + spacing
        text_y = py0 + (pill_h - bth) // 2 - bt_bbox[1]
        draw.text((text_x, text_y), bot_pill_text, fill=(255, 255, 255), font=f_bot)
    else:
        draw.text((px0 + (pill_w - btw) // 2, py0 + (pill_h - bth) // 2 - bt_bbox[1]), bot_pill_text, fill=(255, 255, 255), font=f_bot)

    return img, card_bbox

def draw_rounded_rect(
    img: Image.Image,
    bbox: Tuple[int, int, int, int],
    radius: int,
    fill: Tuple[int, int, int, int],
    outline: Optional[Tuple[int, int, int, int]] = None,
    width: int = 1
) -> Image.Image:
    """Draw an anti-aliased rounded rectangle with transparency."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return img

    scale = 2
    sw, sh = w * scale, h * scale
    s_radius = radius * scale
    s_width = width * scale

    sub = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(sub)
    s_draw.rounded_rectangle(
        (0, 0, sw, sh),
        radius=s_radius,
        fill=fill,
        outline=outline,
        width=s_width if outline else 0
    )

    sub = sub.resize((w, h), Image.Resampling.LANCZOS)
    img.alpha_composite(sub, (x0, y0))
    return img

def draw_footer(img: Image.Image, y_pos: Optional[int] = None) -> None:
    """Stamp the footer pill at bottom center with Currencing brand icon."""
    w, h = img.size
    y = y_pos if y_pos is not None else h - 35
    pill_w = 268
    pill_h = 44
    px0 = (w - pill_w) // 2
    py0 = y - (pill_h // 2)
    px1 = px0 + pill_w
    py1 = py0 + pill_h

    bp_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bp_draw = ImageDraw.Draw(bp_layer)
    bp_draw.rounded_rectangle((px0, py0, px1, py1), radius=pill_h // 2, fill=COLORS["brand_orange"] + (255,), outline=(255, 255, 255, 140), width=1)
    img.alpha_composite(bp_layer)

    draw = ImageDraw.Draw(img)
    f_bot = get_font(18, weight="bold")
    bot_text = f"t.me/{BOT_USERNAME}"
    bb = f_bot.getbbox(bot_text)
    bw = bb[2] - bb[0]
    bh = bb[3] - bb[1]

    logo_icon = get_currencing_icon(22)
    if logo_icon:
        spacing = 8
        content_w = 22 + spacing + bw
        start_x = px0 + (pill_w - content_w) // 2
        logo_y = py0 + (pill_h - 22) // 2
        img.alpha_composite(logo_icon, (start_x, logo_y))
        text_x = start_x + 22 + spacing
        text_y = py0 + (pill_h - bh) // 2 - bb[1]
        draw.text((text_x, text_y), bot_text, fill=(255, 255, 255), font=f_bot)
    else:
        draw.text((px0 + (pill_w - bw) // 2, py0 + (pill_h - bh) // 2 - bb[1]), bot_text, fill=(255, 255, 255), font=f_bot)

def smooth_curve(points: List[Tuple[float, float]], num_samples: int = 300) -> List[Tuple[float, float]]:
    """Catmull-Rom spline interpolation for smooth chart curves."""
    if len(points) < 4:
        return points

    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]

    x_padded = [x_vals[0]] + x_vals + [x_vals[-1]]
    y_padded = [y_vals[0]] + y_vals + [y_vals[-1]]

    smoothed = []
    n_segs = len(points) - 1
    samples_per_seg = max(2, num_samples // n_segs)

    for i in range(1, len(x_padded) - 2):
        p0 = (x_padded[i - 1], y_padded[i - 1])
        p1 = (x_padded[i], y_padded[i])
        p2 = (x_padded[i + 1], y_padded[i + 1])
        p3 = (x_padded[i + 2], y_padded[i + 2])

        for t_step in range(samples_per_seg):
            t = t_step / samples_per_seg
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                (2 * p1[0]) +
                (-p0[0] + p2[0]) * t +
                (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1]) +
                (-p0[1] + p2[1]) * t +
                (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            smoothed.append((x, y))

    smoothed.append(points[-1])
    return smoothed

def draw_historical_chart(
    img: Image.Image,
    prices: List[float],
    bbox: Tuple[int, int, int, int] = (96, 360, 928, 510),
    date_labels: Optional[List[str]] = None,
    is_positive: bool = True
) -> None:
    """Draw gradient-filled area chart with spline line and timeline dates."""
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0
    if not prices or len(prices) < 2 or w <= 0 or h <= 0:
        return

    min_p, max_p = min(prices), max(prices)
    rng = max_p - min_p
    n = len(prices)
    raw_points = []
    if rng <= 0.0001:
        # Prevent flat baseline line pinned to the bottom.
        # Synthesize gentle wave centered in chart bbox.
        baseline = (y0 + y1) / 2.0
        wave_amp = h * 0.15
        for i in range(n):
            px = x0 + (i / max(1, n - 1)) * w
            py = baseline + math.sin(i * 0.18) * wave_amp
            raw_points.append((px, py))
    else:
        for i, p in enumerate(prices):
            px = x0 + (i / (n - 1)) * w
            norm_y = (p - min_p) / rng
            py = (y1 - 16) - norm_y * (h - 32)
            raw_points.append((px, py))

    curve = smooth_curve(raw_points, num_samples=320)

    # Stroke and fill colors
    if is_positive:
        stroke_color = COLORS["chart_stroke_green"]
        top_fill = (0, 230, 118, 75)
        bot_fill = (0, 230, 118, 0)
    else:
        stroke_color = COLORS["chart_stroke_red"]
        top_fill = (255, 65, 65, 75)
        bot_fill = (255, 65, 65, 0)

    # Gradient Fill underneath curve
    chart_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    poly_points = [(curve[0][0], y1)] + curve + [(curve[-1][0], y1)]
    poly_mask = Image.new("L", img.size, 0)
    pm_draw = ImageDraw.Draw(poly_mask)
    pm_draw.polygon(poly_points, fill=255)

    grad_arr = np.zeros((h, w, 4), dtype=np.uint8)
    tf_np = np.array(top_fill, dtype=float)
    bf_np = np.array(bot_fill, dtype=float)
    for yi in range(h):
        f = yi / max(1, h - 1)
        grad_arr[yi, :] = (tf_np * (1 - f) + bf_np * f).astype(np.uint8)
    grad_img = Image.fromarray(grad_arr, "RGBA")

    chart_layer.paste(grad_img, (x0, y0))
    img.paste(chart_layer, (0, 0), poly_mask)

    # Crisp Line Stroke
    stroke_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    st_draw = ImageDraw.Draw(stroke_layer)
    st_draw.line(curve, fill=stroke_color, width=3, joint="curve")
    img.alpha_composite(stroke_layer)

    # Timeline Date Labels
    if not date_labels:
        today = datetime.now()
        date_labels = [(today - timedelta(days=7 - i)).strftime("%b %d") for i in range(8)]

    f_date = get_font(13, weight="semibold")
    draw = ImageDraw.Draw(img)
    num_dates = len(date_labels)
    for i, d_lbl in enumerate(date_labels):
        bbox_d = f_date.getbbox(d_lbl)
        dw = bbox_d[2] - bbox_d[0]
        dx = x0 + int((i / (num_dates - 1)) * (w - dw))
        draw.text((dx, y1 + 10), d_lbl, fill=COLORS["gray_text"], font=f_date)
