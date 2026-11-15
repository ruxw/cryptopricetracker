import re
import logging
from typing import Optional, Tuple, Dict, Any
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bot.database import get_sponsored_settings

logger = logging.getLogger(__name__)

STYLE_MAP = {
    "red": "danger",
    "danger": "danger",
    "green": "success",
    "success": "success",
    "blue": "primary",
    "primary": "primary",
}

def parse_sponsored_button_input(raw: str) -> Optional[Tuple[Optional[str], str, str]]:
    """
    Parse button input matching:
      #(primary|success|danger|blue|green|red) Button Text - https://link
    Returns: (style, button_text, url)
    Ensures the link NEVER appears on button text.
    """
    raw = raw.strip()
    match = re.match(
        r"^(?:#(primary|success|danger|blue|green|red)\s+)?(.*?)\s*[-—]\s*(https?://\S+|t\.me/\S+)$",
        raw,
        re.IGNORECASE
    )
    if not match:
        return None

    raw_style, btn_text, btn_url = match.groups()
    btn_text = btn_text.strip()
    btn_url = btn_url.strip()

    if not btn_url.startswith("http://") and not btn_url.startswith("https://"):
        btn_url = "https://" + btn_url

    style = STYLE_MAP.get((raw_style or "").lower(), "primary")
    return style, btn_text, btn_url

def create_styled_button(text: str, url: str, style: Optional[str] = None) -> InlineKeyboardButton:
    """Create InlineKeyboardButton with Bot API 8.0 button style support."""
    kwargs = {"url": url}
    if style:
        try:
            return InlineKeyboardButton(text, style=style, **kwargs)
        except TypeError:
            pass
    return InlineKeyboardButton(text, **kwargs)

async def get_sponsored_button() -> Optional[InlineKeyboardButton]:
    """Return configured sponsored button if enabled."""
    sp = await get_sponsored_settings()
    if not sp or not sp["button_enabled"] or not sp["button_text"] or not sp["button_url"]:
        return None

    return create_styled_button(sp["button_text"], sp["button_url"], sp.get("button_style"))

async def get_sponsored_button_markup() -> Optional[InlineKeyboardMarkup]:
    """Return InlineKeyboardMarkup with single sponsored button."""
    btn = await get_sponsored_button()
    if not btn:
        return None
    return InlineKeyboardMarkup([[btn]])

async def attach_sponsored_content(
    text: Optional[str] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    """
    Central wrapper:
    - Appends active sponsored text formatted as <blockquote>...</blockquote> (Telegram quotation)
    - Appends active sponsored button to reply_markup
    - Works for both private messages and group messages
    """
    sp = await get_sponsored_settings()
    if not sp:
        return text, reply_markup

    # 1. Append quotation text if enabled
    if sp["text_enabled"] and sp["text_html"]:
        content = sp["text_html"].strip()
        # Ensure wrapped in <blockquote> tag (Telegram quotation style as in ctrl+shift+.)
        if content.startswith("<blockquote>") and content.endswith("</blockquote>"):
            sp_block = content
        else:
            sp_block = f"<blockquote>{content}</blockquote>"

        if text:
            text = f"{text}\n\n{sp_block}"
        else:
            text = sp_block

    # 2. Append sponsored button if enabled
    if sp["button_enabled"] and sp["button_text"] and sp["button_url"]:
        sp_btn = create_styled_button(sp["button_text"], sp["button_url"], sp.get("button_style"))
        if reply_markup and hasattr(reply_markup, "inline_keyboard"):
            new_kb = [list(r) for r in reply_markup.inline_keyboard]
            new_kb.append([sp_btn])
            reply_markup = InlineKeyboardMarkup(new_kb)
        else:
            reply_markup = InlineKeyboardMarkup([[sp_btn]])

    return text, reply_markup
