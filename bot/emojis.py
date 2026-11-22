"""
Currencing Bot — Emoji Registry & Custom Emoji Engine
=====================================================
Supports Telegram Custom Emojis in BOTH:
1. Message / Caption HTML texts: <tg-emoji emoji-id="123456789">fallback</tg-emoji>
2. Inline Keyboard Buttons: InlineKeyboardButton(text=..., icon_custom_emoji_id="123456789")

Usage in handlers (HTML parse mode):
  from bot.emojis import E, coin_emoji, custom_btn
  text = f"{coin_emoji('BTC')} Bitcoin {E('currencing')}"

For Telegram inline button labels:
  btn = custom_btn("BTC 7-Day Chart", callback_data="stats_BTC", coin="BTC")
  btn = custom_btn("Subscribe", callback_data="sub:BTC", icon="bell")
"""

import re
from typing import Dict, Optional, Any
from telegram import InlineKeyboardButton

# Leading unicode emoji pattern to eliminate doubled emojis on buttons
_LEADING_EMOJI_RE = re.compile(
    r"^[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u200d\ufe0f⚡₿📈🚀🔔🔕🎲😂🐸📊🔄ℹ️✅❌🔒👋⏳🔎👥\s]+",
    re.UNICODE
)

def strip_leading_emojis(text: str) -> str:
    """Remove leading Unicode emojis so only native Telegram custom emoji is displayed on buttons."""
    cleaned = _LEADING_EMOJI_RE.sub("", text).strip()
    return cleaned or text

# ─── COIN CUSTOM EMOJIS ───────────────────────────────────────────────────────
# Map: coin symbol → {"custom_id": "...", "fallback": "..."}

COIN_EMOJIS: Dict[str, Dict[str, str]] = {
    "BTC":   {"custom_id": "5969756601567943062", "fallback": "₿"},
    "ETH":   {"custom_id": "5769374258127965397", "fallback": "Ξ"},
    "SOL":   {"custom_id": "5969851490280413043", "fallback": "◎"},
    "BNB":   {"custom_id": "5969931273592903807", "fallback": "🔶"},
    "XRP":   {"custom_id": "5969642587366103835", "fallback": "✕"},
    "DOGE":  {"custom_id": "5460891238569882118", "fallback": "Ð"},
    "ADA":   {"custom_id": "5289634288134793049", "fallback": "₳"},
    "AVAX":  {"custom_id": "5832482690804225948", "fallback": "▲"},
    "GRAM":  {"custom_id": "5969840323365443558", "fallback": "💎"},
    "TON":   {"custom_id": "5969840323365443558", "fallback": "💎"},
    "TRX":   {"custom_id": "5969739043741636059", "fallback": "▲"},
    "LTC":   {"custom_id": "5771379449509448765", "fallback": "Ł"},
    "XMR":   {"custom_id": "5970037608393218118", "fallback": "ɱ"},
    "SHIB":  {"custom_id": "5463383281674232341", "fallback": "🐕"},
    "PEPE":  {"custom_id": "5384547868465968644", "fallback": "🐸"},
    "LINK":  {"custom_id": "", "fallback": "🔗"},
    "NEAR":  {"custom_id": "", "fallback": "Ⓝ"},
    "SUI":   {"custom_id": "", "fallback": "💧"},
    "APT":   {"custom_id": "", "fallback": "⬡"},
    "DOT":   {"custom_id": "", "fallback": "●"},
    "ICP":   {"custom_id": "", "fallback": "∞"},
    "UNI":   {"custom_id": "", "fallback": "🦄"},
    "BCH":   {"custom_id": "", "fallback": "₿"},
    "XLM":   {"custom_id": "", "fallback": "🚀"},
}

# ─── UI / GENERAL EMOJIS ──────────────────────────────────────────────────────
# Emojis used in bot messages and buttons.

UI_EMOJIS: Dict[str, Dict[str, str]] = {
    "chart":      {"custom_id": "5231200819986047254", "fallback": "📊"},
    "stats":      {"custom_id": "5028746137645876535", "fallback": "📈"},
    "ath":        {"custom_id": "5188481279963715781", "fallback": "🚀"},
    "convert":    {"custom_id": "5402186569006210455", "fallback": "💱"},
    "refresh":    {"custom_id": "5244758760429213978", "fallback": "🔄"},
    "menu":       {"custom_id": "5974098293813152457", "fallback": "☰"},
    "help":       {"custom_id": "6303059485510345037", "fallback": "ℹ️"},
    "check":      {"custom_id": "6305073687733215410", "fallback": "✅"},
    "cross":      {"custom_id": "6303267288913027285", "fallback": "❌"},
    "fire":       {"custom_id": "5424972470023104089", "fallback": "🔥"},
    "gem":        {"custom_id": "5235630047959727475", "fallback": "💎"},
    "up":         {"custom_id": "5449683594425410231", "fallback": "▲"},
    "down":       {"custom_id": "5447183459602669338", "fallback": "▼"},
    "meme":       {"custom_id": "5422545753371321761", "fallback": "🐸"},
    "dollar":     {"custom_id": "5409048419211682843", "fallback": "$"},
    "inline":     {"custom_id": "5258396243666681152", "fallback": "🔎"},
    "group":      {"custom_id": "6032594876506312598", "fallback": "👥"},
    "lock":       {"custom_id": "5393302369024882368", "fallback": "🔒"},
    "wave":       {"custom_id": "5343984088493599366", "fallback": "👋"},
    "time":       {"custom_id": "5451732530048802485", "fallback": "⏳"},
    "currencing": {"custom_id": "5235630047959727475", "fallback": "⚡"},
    "bell":       {"custom_id": "", "fallback": "🔔"},
    "sub":        {"custom_id": "6305073687733215410", "fallback": "✅"},
    "unsub":      {"custom_id": "6303267288913027285", "fallback": "🔕"},
    "quote":      {"custom_id": "5422545753371321761", "fallback": "💬"},
    "dice":       {"custom_id": "5424972470023104089", "fallback": "🎲"},
}


# ─── TEXT RENDERING HELPERS (HTML parse mode) ──────────────────────────────────

def _render(entry: Dict[str, str]) -> str:
    """Return custom emoji HTML tag if ID is set, else plain fallback."""
    cid = entry.get("custom_id", "").strip()
    fb  = entry.get("fallback", "?")
    if cid:
        return f'<tg-emoji emoji-id="{cid}">{fb}</tg-emoji>'
    return fb


def coin_emoji(symbol: str) -> str:
    """Return the emoji for a coin symbol (HTML custom tag or fallback)."""
    entry = COIN_EMOJIS.get(symbol.upper())
    if not entry:
        return ""
    return _render(entry)


def E(key: str) -> str:
    """Return a UI emoji by key (HTML custom tag or fallback)."""
    entry = UI_EMOJIS.get(key)
    if not entry:
        return ""
    return _render(entry)


def coin_fallback(symbol: str) -> str:
    """Return the clean plain text fallback emoji for a coin."""
    entry = COIN_EMOJIS.get(symbol.upper(), {})
    return entry.get("fallback", "")


def ui_fallback(key: str) -> str:
    """Return the clean plain text fallback emoji for a UI key."""
    entry = UI_EMOJIS.get(key, {})
    return entry.get("fallback", "")


# ─── BUTTON RENDERING HELPERS (Bot API 8.0+ icon_custom_emoji_id) ──────────────

def btn_icon(key: str) -> Optional[str]:
    """Return the Telegram custom emoji ID for an inline button icon."""
    entry = UI_EMOJIS.get(key)
    if entry and entry.get("custom_id"):
        return entry["custom_id"]
    return None


def btn_coin_icon(symbol: str) -> Optional[str]:
    """Return the Telegram custom emoji ID for a coin on an inline button."""
    entry = COIN_EMOJIS.get(symbol.upper())
    if entry and entry.get("custom_id"):
        return entry["custom_id"]
    return None


def custom_btn(
    text: str,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    icon: Optional[str] = None,
    coin: Optional[str] = None,
    style: Optional[str] = None,
    **kwargs: Any
) -> InlineKeyboardButton:
    """
    Construct an InlineKeyboardButton utilizing Telegram native custom emoji icons.
    - icon: key from UI_EMOJIS (e.g. 'bell', 'chart', 'ath', 'refresh')
    - coin: ticker from COIN_EMOJIS (e.g. 'BTC', 'ETH', 'SOL')
    - style: optional button style ('primary', 'success', 'danger')
    """
    emoji_id: Optional[str] = None
    if coin:
        emoji_id = btn_coin_icon(coin)
    elif icon:
        emoji_id = btn_icon(icon)

    # When native custom emoji icon is attached, eliminate redundant Unicode emoji from label
    clean_label = strip_leading_emojis(text) if emoji_id else text

    btn_kwargs = dict(kwargs)
    if callback_data is not None:
        btn_kwargs["callback_data"] = callback_data
    if url is not None:
        btn_kwargs["url"] = url
    if style:
        btn_kwargs["style"] = style
    if emoji_id:
        btn_kwargs["icon_custom_emoji_id"] = emoji_id

    try:
        return InlineKeyboardButton(text=clean_label, **btn_kwargs)
    except TypeError:
        # Graceful fallback if telegram library lacks style or icon_custom_emoji_id
        btn_kwargs.pop("icon_custom_emoji_id", None)
        btn_kwargs.pop("style", None)
        return InlineKeyboardButton(text=text, **btn_kwargs)
