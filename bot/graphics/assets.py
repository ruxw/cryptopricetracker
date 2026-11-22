import os
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageFont, ImageDraw

from bot.config import BOT_USERNAME

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

FONT_PATH = os.path.join(FONTS_DIR, "Inter.ttf")
# Fallbacks for Windows if needed
FALLBACK_FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FALLBACK_FONT_REGULAR = r"C:\Windows\Fonts\segoeui.ttf"

# Supported Cryptocurrencies
COINS: Dict[str, Dict[str, Any]] = {
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
        "color": "#627eea",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "eth.png")
    },
    "SOL": {
        "id": "solana",
        "name": "Solana",
        "symbol": "SOL",
        "color": "#14f195",
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
        "color": "#505862",
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
    "TON": {
        "id": "the-open-network",
        "name": "Gram",
        "symbol": "TON",
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
    },
    "LINK": {
        "id": "chainlink",
        "name": "Chainlink",
        "symbol": "LINK",
        "color": "#375bd2",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "link.png")
    },
    "NEAR": {
        "id": "near",
        "name": "NEAR",
        "symbol": "NEAR",
        "color": "#00e599",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "near.png")
    },
    "SUI": {
        "id": "sui",
        "name": "Sui",
        "symbol": "SUI",
        "color": "#4da2ff",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "sui.png")
    },
    "APT": {
        "id": "aptos",
        "name": "Aptos",
        "symbol": "APT",
        "color": "#2ed8a7",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "apt.png")
    },
    "DOT": {
        "id": "polkadot",
        "name": "Polkadot",
        "symbol": "DOT",
        "color": "#e6007a",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "dot.png")
    },
    "ICP": {
        "id": "internet-computer",
        "name": "Internet Computer",
        "symbol": "ICP",
        "color": "#29abe2",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "icp.png")
    },
    "UNI": {
        "id": "uniswap",
        "name": "Uniswap",
        "symbol": "UNI",
        "color": "#ff007a",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "uni.png")
    },
    "BCH": {
        "id": "bitcoin-cash",
        "name": "Bitcoin Cash",
        "symbol": "BCH",
        "color": "#8dc351",
        "decimals": 2,
        "icon": os.path.join(ICONS_DIR, "bch.png")
    },
    "XLM": {
        "id": "stellar",
        "name": "Stellar",
        "symbol": "XLM",
        "color": "#14b6eb",
        "decimals": 4,
        "icon": os.path.join(ICONS_DIR, "xlm.png")
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

# High-End Design Colors
COLORS = {
    "navy_text": (16, 17, 22),         # Dark charcoal for light badges
    "white": (255, 255, 255),
    "card_bg": (12, 13, 17, 245),      # Sleek obsidian container
    "pill_bg": (246, 244, 240, 255),   # Off-white porcelain capsule
    "pill_border": (255, 255, 255, 200),
    "green": (0, 230, 118),            # Vibrant neon/mint green
    "red": (255, 65, 65),              # Vibrant coral red
    "gray_text": (125, 133, 150),      # Clean slate metadata
    "chart_stroke_green": (0, 230, 118, 255),
    "chart_stroke_red": (255, 65, 65, 255),
    "brand_orange": (245, 132, 16),
}

_font_cache: Dict[Tuple[int, int], ImageFont.FreeTypeFont] = {}

def get_font(size: int, bold: bool = True, weight: Any = "bold") -> ImageFont.FreeTypeFont:
    """
    Load Inter variable font with exact typography weight (400 to 900) or system fallback.
    weight: "regular" (400), "medium" (500), "semibold" (600), "bold" (700), "extrabold" (800)
    """
    if isinstance(weight, str):
        w_map = {
            "regular": 400, "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
            "extrabold": 800, "heavy": 800,
            "black": 900
        }
        numeric_weight = w_map.get(weight.lower(), 700 if bold else 400)
    elif isinstance(weight, (int, float)):
        numeric_weight = int(weight)
    else:
        numeric_weight = 700 if bold else 400

    cache_key = (size, numeric_weight)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    if os.path.exists(FONT_PATH):
        try:
            font = ImageFont.truetype(FONT_PATH, size)
            font.set_variation_by_axes([14, numeric_weight])
            _font_cache[cache_key] = font
            return font
        except Exception:
            pass

    # Fallback to Windows system fonts by weight
    fallback = FALLBACK_FONT_BOLD if numeric_weight >= 600 else FALLBACK_FONT_REGULAR
    if os.path.exists(fallback):
        try:
            font = ImageFont.truetype(fallback, size)
            _font_cache[cache_key] = font
            return font
        except Exception:
            pass

    font = ImageFont.load_default()
    _font_cache[cache_key] = font
    return font

def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
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
    draw.ellipse([1, 1, size - 2, size - 2], fill=(245, 247, 252, 255), outline=(50, 50, 70, 200), width=2)
    font_size = int(size * 0.55)
    font = get_font(font_size, bold=True, weight="bold")
    bbox = font.getbbox(symbol)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), symbol, fill=(16, 17, 22), font=font)
    return badge
