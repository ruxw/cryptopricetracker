import os
from typing import Dict, Any, Optional
from PIL import Image, ImageFont, ImageDraw

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

FONT_PATH = os.path.join(FONTS_DIR, "Inter.ttf")
# Fallbacks for Windows if needed
FALLBACK_FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FALLBACK_FONT_REGULAR = r"C:\Windows\Fonts\segoeui.ttf"

# Supported Cryptocurrencies (Top 20 + Top 3 Memes = 23 coins)
COINS: Dict[str, Dict[str, Any]] = {
    # Top 20 Cryptocurrencies
    "BTC": {
        "id": "bitcoin",
        "name": "Bitcoin",
        "symbol": "BTC",
        "color": "#f7931a",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "btc.png")
    },
    "ETH": {
        "id": "ethereum",
        "name": "Ethereum",
        "symbol": "ETH",
        "color": "#456ee8",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "eth.png")
    },
    "SOL": {
        "id": "solana",
        "name": "Solana",
        "symbol": "SOL",
        "color": "#9945ff",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "sol.png")
    },
    "BNB": {
        "id": "binancecoin",
        "name": "BNB",
        "symbol": "BNB",
        "color": "#f3ba2f",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "bnb.png")
    },
    "XRP": {
        "id": "ripple",
        "name": "XRP",
        "symbol": "XRP",
        "color": "#23292f",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "xrp.png")
    },
    "DOGE": {
        "id": "dogecoin",
        "name": "Dogecoin",
        "symbol": "DOGE",
        "color": "#c2a633",
        "decimals": 4,
        "icon": os.path.join(ICONS_DIR, "doge.png")
    },
    "ADA": {
        "id": "cardano",
        "name": "Cardano",
        "symbol": "ADA",
        "color": "#0033ad",
        "decimals": 4,
        "icon": os.path.join(ICONS_DIR, "ada.png")
    },
    "AVAX": {
        "id": "avalanche-2",
        "name": "Avalanche",
        "symbol": "AVAX",
        "color": "#e84142",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "avax.png")
    },
    "GRAM": {
        "id": "the-open-network",
        "name": "Gram",
        "symbol": "GRAM",
        "color": "#0098ea",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "gram.png")
    },
    "TRX": {
        "id": "tron",
        "name": "Tron",
        "symbol": "TRX",
        "color": "#eb0029",
        "decimals": 4,
        "icon": os.path.join(ICONS_DIR, "trx.png")
    },
    "LTC": {
        "id": "litecoin",
        "name": "Litecoin",
        "symbol": "LTC",
        "color": "#345d9d",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "ltc.png")
    },
    "XMR": {
        "id": "monero",
        "name": "Monero",
        "symbol": "XMR",
        "color": "#ff6600",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "xmr.png")
    },
    "SHIB": {
        "id": "shiba-inu",
        "name": "Shiba Inu",
        "symbol": "SHIB",
        "color": "#ff8c00",
        "decimals": 6,
        "icon": os.path.join(ICONS_DIR, "shib.png")
    },
    "PEPE": {
        "id": "pepe",
        "name": "Pepe",
        "symbol": "PEPE",
        "color": "#469f41",
        "decimals": 8,
        "icon": os.path.join(ICONS_DIR, "pepe.png")
    }
}

# Fiat Currencies Supported for Conversion
FIAT_CURRENCIES: Dict[str, Dict[str, Any]] = {
    "USD": {"symbol": "$", "name": "US Dollar", "decimals": 2},
    "EUR": {"symbol": "€", "name": "Euro", "decimals": 2},
    "GBP": {"symbol": "£", "name": "British Pound", "decimals": 2},
    "JPY": {"symbol": "¥", "name": "Japanese Yen", "decimals": 0},
    "CAD": {"symbol": "$", "name": "Canadian Dollar", "decimals": 2},
    "AUD": {"symbol": "$", "name": "Australian Dollar", "decimals": 2},
    "CHF": {"symbol": "CHF", "name": "Swiss Franc", "decimals": 2},
    "CNY": {"symbol": "¥", "name": "Chinese Yuan", "decimals": 2},
    "INR": {"symbol": "₹", "name": "Indian Rupee", "decimals": 2},
    "RUB": {"symbol": "₽", "name": "Russian Ruble", "decimals": 2},
}

# Color Palette
COLORS = {
    "navy_text": (30, 30, 45),        # #1e1e2d
    "white": (255, 255, 255),
    "card_bg": (245, 247, 255, 195),
    "pill_bg": (255, 255, 255, 245),
    "pill_border": (255, 255, 255, 180),
    "green": (16, 185, 129),          # #10b981
    "red": (225, 59, 59),             # #e13b3b
    "gray_text": (90, 88, 110),
    "chart_stroke": (255, 255, 255, 255),
    "chart_fill_top": (255, 255, 255, 60),
    "chart_fill_bot": (255, 255, 255, 10),
}

_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}

def get_font(size: int, bold: bool = True, weight: str = "bold") -> ImageFont.FreeTypeFont:
    """
    Load Inter with proper weight.
    weight: "regular" | "semibold" | "bold"
    If the Inter variable font doesn't support named weights, falls back to
    system Segoe UI bold/regular.
    """
    weight_map = {"regular": 0, "semibold": 1, "bold": 2}
    cache_key = size * 10 + weight_map.get(weight, 2 if bold else 0)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    # Try Inter font (variable font — PIL uses it without axis tuning,
    # but we can pick bold/regular via the face index or separate files)
    if os.path.exists(FONT_PATH):
        try:
            font = ImageFont.truetype(FONT_PATH, size)
            _font_cache[cache_key] = font
            return font
        except Exception:
            pass

    # Fallback to Windows system fonts by weight
    if weight == "regular":
        fallback = FALLBACK_FONT_REGULAR
    else:
        fallback = FALLBACK_FONT_BOLD

    if os.path.exists(fallback):
        font = ImageFont.truetype(fallback, size)
        _font_cache[cache_key] = font
        return font

    font = ImageFont.load_default()
    _font_cache[cache_key] = font
    return font

def hex_to_rgb(hex_code: str) -> tuple:
    hex_code = hex_code.lstrip("#")
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def format_price(value: float, decimals: Optional[int] = None) -> str:
    """Format price with appropriate commas and decimals."""
    if value is None:
        return "0.00"
    if decimals is not None:
        return f"{value:,.{decimals}f}"
    if value >= 1000:
        return f"{value:,.2f}"
    elif value >= 1:
        return f"{value:,.2f}"
    elif value >= 0.01:
        return f"{value:,.4f}"
    else:
        return f"{value:,.6f}"

def format_change(value: Optional[float]) -> str:
    """Format percentage change string like '-1.36%' or '+2.45%'."""
    if value is None:
        return "0.00%"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"

def get_fiat_badge(symbol: str, size: int = 40) -> Image.Image:
    """Generate a clean circular fiat symbol badge."""
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    # White circle with dark outline
    draw.ellipse([1, 1, size - 2, size - 2], fill=(245, 247, 252, 255), outline=(50, 50, 70, 200), width=2)
    font_size = int(size * 0.55)
    font = get_font(font_size, bold=True)
    bbox = font.getbbox(symbol)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), symbol, fill=(30, 30, 45), font=font)
    return badge
