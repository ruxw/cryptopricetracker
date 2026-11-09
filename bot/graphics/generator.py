import os
import math
from typing import List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from bot.graphics.assets import (
    ASSETS_DIR, COLORS, get_font, hex_to_rgb
)

BG_TEMPLATE_PATH = os.path.join(ASSETS_DIR, "background.png")
FOOTER_PATH = os.path.join(ASSETS_DIR, "currencing_footer.png")

def get_base_background(width: int = 1024, height: int = 640) -> Image.Image:
    """Return the faceted purple/blue gradient base background."""
    if os.path.exists(BG_TEMPLATE_PATH):
        try:
            bg = Image.open(BG_TEMPLATE_PATH).convert("RGBA")
            if bg.size != (width, height):
                bg = bg.resize((width, height), Image.Resampling.LANCZOS)
            return bg
        except Exception:
            pass

    # Generate procedurally if template not found
    top_col = np.array([170, 125, 252], dtype=float)
    bot_col = np.array([80, 175, 254], dtype=float)
    grad = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        f = y / (height - 1)
        grad[y, :] = (top_col * (1 - f) + bot_col * f).astype(np.uint8)

    base = Image.fromarray(grad, "RGB").convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    facets = [
        ([(0, 0), (380, 0), (280, 220), (0, 140)], (255, 255, 255, 22)),
        ([(280, 220), (380, 0), (680, 0), (520, 260)], (190, 215, 255, 14)),
        ([(520, 260), (680, 0), (1024, 0), (840, 240)], (255, 255, 255, 24)),
        ([(840, 240), (1024, 0), (1024, 280), (760, 360)], (210, 200, 255, 16)),
        ([(0, 140), (280, 220), (180, 440), (0, 380)], (200, 220, 255, 18)),
        ([(180, 440), (280, 220), (520, 260), (420, 480)], (255, 255, 255, 20)),
        ([(420, 480), (520, 260), (760, 360), (640, 520)], (190, 230, 255, 15)),
        ([(640, 520), (760, 360), (840, 240), (1024, 280), (1024, 480)], (255, 255, 255, 22)),
        ([(0, 380), (180, 440), (240, 640), (0, 640)], (210, 240, 255, 16)),
        ([(180, 440), (420, 480), (460, 640), (240, 640)], (255, 255, 255, 18)),
        ([(420, 480), (640, 520), (720, 640), (460, 640)], (180, 225, 255, 14)),
        ([(640, 520), (1024, 480), (1024, 640), (720, 640)], (255, 255, 255, 20)),
    ]
    for poly, col in facets:
        draw.polygon(poly, fill=col)
    overlay = overlay.filter(ImageFilter.GaussianBlur(1.5))
    return Image.alpha_composite(base, overlay)

def draw_rounded_rect(
    img: Image.Image,
    bbox: Tuple[int, int, int, int],
    radius: int,
    fill: Tuple[int, int, int, int],
    outline: Optional[Tuple[int, int, int, int]] = None,
    width: int = 1
) -> Image.Image:
    """Draw a smooth anti-aliased rounded rectangle with transparency."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return img

    # Supersample 2x for crystal-clean curved borders
    scale = 2
    sw, sh = w * scale, h * scale
    s_radius = radius * scale
    s_width = width * scale

    sub = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(sub)
    s_bbox = (0, 0, sw, sh)

    s_draw.rounded_rectangle(
        s_bbox,
        radius=s_radius,
        fill=fill,
        outline=outline,
        width=s_width if outline else 0
    )

    sub = sub.resize((w, h), Image.Resampling.LANCZOS)
    img.alpha_composite(sub, (x0, y0))
    return img

def draw_footer(img: Image.Image, y_pos: Optional[int] = None) -> None:
    """Stamp the official Powered by SWAP.MY footer at bottom center."""
    w, h = img.size
    y = y_pos if y_pos is not None else h - 35

    if os.path.exists(FOOTER_PATH):
        try:
            footer = Image.open(FOOTER_PATH).convert("RGBA")
            fw, fh = footer.size
            fx = (w - fw) // 2
            fy = y - (fh // 2)
            img.alpha_composite(footer, (fx, fy))
            return
        except Exception:
            pass

    # Procedural fallback footer
    draw = ImageDraw.Draw(img)
    font = get_font(18, bold=True)
    text = "Powered by Currencing"
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = y - (th // 2)
    draw.text((tx, ty), text, fill=(255, 255, 255, 240), font=font)

def smooth_curve(points: List[Tuple[float, float]], num_samples: int = 300) -> List[Tuple[float, float]]:
    """Interpolate points using Catmull-Rom spline for a silky smooth chart line."""
    if len(points) < 4:
        return points

    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]
    
    # Pad ends
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
            
            # Catmull-Rom formula
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
    bbox: Tuple[int, int, int, int],
    date_labels: List[str],
    is_positive: bool = True,
) -> None:
    """Render the 7-day historical chart with glowing line and translucent fill.

    Line + fill are GREEN when price change is positive, RED when negative.
    """
    if not prices or len(prices) < 2:
        return

    x0, y0, x1, y1 = bbox
    chart_w = x1 - x0
    chart_h = y1 - y0

    p_arr = np.array(prices, dtype=float)
    p_min, p_max = p_arr.min(), p_arr.max()
    p_range = p_max - p_min if p_max > p_min else 1.0

    # Margin inside chart box
    top_pad = 20
    bot_pad = 10
    active_h = chart_h - top_pad - bot_pad

    raw_points = []
    n = len(prices)
    for i, p in enumerate(prices):
        x = x0 + (i / (n - 1)) * chart_w
        norm_y = (p - p_min) / p_range
        y = (y1 - bot_pad) - norm_y * active_h
        raw_points.append((x, y))

    smooth_pts = smooth_curve(raw_points, num_samples=350)
    baseline_y = y1 + 5

    # Colour scheme: green for positive, red for negative
    if is_positive:
        line_color  = (16, 185, 129, 255)   # #10b981 green
        fill_color  = (16, 185, 129, 55)
    else:
        line_color  = (225, 59,  59,  255)   # #e13b3b red
        fill_color  = (225, 59,  59,  50)

    # 1. Fill polygon with translucent gradient
    chart_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(chart_layer)

    poly = list(smooth_pts) + [(smooth_pts[-1][0], baseline_y), (smooth_pts[0][0], baseline_y)]
    draw.polygon(poly, fill=fill_color)

    # 2. Draw crisp coloured stroke on top of the curve
    draw.line(smooth_pts, fill=line_color, width=4, joint="curve")

    img.alpha_composite(chart_layer)

    # 3. Draw Date Ticks along the bottom
    if date_labels:
        draw_labels = ImageDraw.Draw(img)
        font = get_font(16, bold=True)
        label_color = (60, 60, 85)
        num_labels = len(date_labels)
        
        for i, label in enumerate(date_labels):
            bbox_t = font.getbbox(label)
            tw = bbox_t[2] - bbox_t[0]
            # Calculate x position centered on each tick
            if num_labels == 1:
                lx = x0 + chart_w // 2 - tw // 2
            else:
                lx = x0 + (i / (num_labels - 1)) * chart_w - (tw // 2)
            # Clamp inside boundaries
            lx = max(x0, min(lx, x1 - tw))
            draw_labels.text((lx, baseline_y + 8), label, fill=label_color, font=font)
