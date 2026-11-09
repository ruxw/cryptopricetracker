"""
Currencing Bot — Emoji Registry
================================
Fill in your custom Telegram emoji IDs below.
Leave custom_id as "" to use the Unicode fallback automatically.

How it works
------------
In HTML parse mode, Telegram renders custom emojis like:
  <tg-emoji emoji-id="5368324170671202286">fallback</tg-emoji>

Usage in handlers (HTML parse mode):
  from bot.emojis import E, coin_emoji, coin_fallback, ui_fallback
  text = f"{coin_emoji('BTC')} Bitcoin"
  text = f"Market {E('chart')} Overview"

For Telegram inline button labels (which require plain text):
  btn_text = f"{coin_fallback('BTC')} BTC"
"""

from typing import Dict

# ─── COIN CUSTOM EMOJIS ───────────────────────────────────────────────────────
# Map: coin symbol → {"custom_id": "...", "fallback": "..."}
# Replace custom_id values with your Telegram custom emoji IDs.

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
    "TRX":   {"custom_id": "5969739043741636059", "fallback": "▲"},
    "LTC":   {"custom_id": "5771379449509448765", "fallback": "Ł"},
    "XMR":   {"custom_id": "5970037608393218118", "fallback": "ɱ"},
    "SHIB":  {"custom_id": "5463383281674232341", "fallback": "🐕"},
    "PEPE":  {"custom_id": "5384547868465968644", "fallback": "🐸"},
}

# ─── UI / GENERAL EMOJIS ──────────────────────────────────────────────────────
# Emojis used in bot messages and buttons.

UI_EMOJIS: Dict[str, Dict[str, str]] = {
    "chart":    {"custom_id": "5231200819986047254", "fallback": "📊"},
    "stats":    {"custom_id": "5028746137645876535", "fallback": "📈"},
    "ath":      {"custom_id": "5188481279963715781", "fallback": "🚀"},
    "convert":  {"custom_id": "5402186569006210455", "fallback": "💱"},
    "refresh":  {"custom_id": "5244758760429213978", "fallback": "🔄"},
    "menu":     {"custom_id": "5974098293813152457", "fallback": "☰"},
    "help":     {"custom_id": "6303059485510345037", "fallback": "ℹ️"},
    "check":    {"custom_id": "6305073687733215410", "fallback": "✅"},
    "cross":    {"custom_id": "6303267288913027285", "fallback": "❌"},
    "fire":     {"custom_id": "5424972470023104089", "fallback": "🔥"},
    "gem":      {"custom_id": "5235630047959727475", "fallback": "💎"},
    "up":       {"custom_id": "5449683594425410231", "fallback": "▲"},
    "down":     {"custom_id": "5447183459602669338", "fallback": "▼"},
    "meme":     {"custom_id": "5422545753371321761", "fallback": "🐸"},
    "dollar":   {"custom_id": "5409048419211682843", "fallback": "$"},
    "inline":   {"custom_id": "5258396243666681152", "fallback": "🔎"},
    "group":    {"custom_id": "6032594876506312598", "fallback": "👥"},
    "lock":     {"custom_id": "5393302369024882368", "fallback": "🔒"},
    "wave":     {"custom_id": "5343984088493599366", "fallback": "👋"},
    "time":     {"custom_id": "5451732530048802485", "fallback": "⏳"},
}


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

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
    """Return the clean plain text fallback emoji for a coin (no doubling)."""
    entry = COIN_EMOJIS.get(symbol.upper(), {})
    return entry.get("fallback", "")


def ui_fallback(key: str) -> str:
    """Return the clean plain text fallback emoji for a UI key."""
    entry = UI_EMOJIS.get(key, {})
    return entry.get("fallback", "")
