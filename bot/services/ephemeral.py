import asyncio
import logging
from typing import Optional
from telegram import Bot, Message
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

async def _schedule_delete(bot: Bot, chat_id: int, message_id: int, delay_seconds: int) -> None:
    """Wait for delay_seconds and delete the message safely."""
    try:
        await asyncio.sleep(delay_seconds)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        # Message was already deleted or bot lacks permission; ignore safely
        pass
    except Exception as e:
        logger.debug("Failed to delete ephemeral message %d in chat %d: %s", message_id, chat_id, e)

async def send_ephemeral(
    bot: Bot,
    chat_id: int,
    text: str,
    auto_delete_seconds: int = 45,
    reply_to_message_id: Optional[int] = None,
    parse_mode: str = ParseMode.HTML
) -> Message:
    """
    Send an ephemeral message that automatically self-deletes after auto_delete_seconds.
    Keeps chat history completely clean without manual deletion.
    """
    footer = f"\n\n⏱️ <i>Self-deleting in {auto_delete_seconds}s</i>"
    full_text = text + footer

    msg = await bot.send_message(
        chat_id=chat_id,
        text=full_text,
        parse_mode=parse_mode,
        reply_to_message_id=reply_to_message_id,
        disable_web_page_preview=True
    )

    # Spawn background task to delete message after delay
    asyncio.create_task(_schedule_delete(bot, chat_id, msg.message_id, auto_delete_seconds))
    return msg
