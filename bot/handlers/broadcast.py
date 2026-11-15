import os
import io
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter, Forbidden
from telegram.ext import ContextTypes

from bot.config import is_owner
from bot.database import (
    get_verified_users_count,
    get_active_groups_count,
    get_active_users,
    get_active_groups,
    set_user_active,
    set_group_active,
    create_broadcast,
    record_broadcast_recipient,
    finish_broadcast,
    get_broadcast_recipients
)
from bot.emojis import E

logger = logging.getLogger(__name__)

# Track active broadcast task so multiple broadcasts don't run at once
_active_broadcast_task: Optional[asyncio.Task] = None

def human_time(seconds: float) -> str:
    """Format duration nicely."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate broadcast wizard (/bd or /broadcast) - Owner only."""
    user = update.effective_user
    if not user or not is_owner(user.id):
        await update.message.reply_text(f"{E('cross')} Unauthorized. This command is restricted to bot owners.")
        return

    user_count = await get_verified_users_count()
    group_count = await get_active_groups_count()
    total_both = user_count + group_count

    text = (
        f"<b>📢 Currencing Broadcast Engine</b>\n\n"
        f"Select the broadcast destination mode:\n\n"
        f"• <b>Bot Users:</b> {user_count} active users\n"
        f"• <b>Deal GCs:</b> {group_count} active groups\n"
        f"• <b>Both:</b> {total_both} total targets"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👤 All Bot Users ({user_count})", callback_data="bd:dest:users")],
        [InlineKeyboardButton(f"👥 All Deal GCs ({group_count})", callback_data="bd:dest:groups")],
        [InlineKeyboardButton(f"🌐 Both ({total_both})", callback_data="bd:dest:both")],
        [InlineKeyboardButton("❌ Cancel", callback_data="bd:cancel")],
    ])

    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast wizard callbacks."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user or not is_owner(user.id):
        await query.answer("❌ Owner access required.", show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1]

    if action == "cancel":
        context.user_data.pop("broadcast_setup", None)
        try:
            await query.message.edit_text("❌ Broadcast cancelled.")
        except Exception:
            pass
        return

    elif action == "dest":
        target_type = parts[2]
        context.user_data["broadcast_setup"] = {"target_type": target_type}
        
        mode_labels = {
            "users": "All Bot Users",
            "groups": "All Deal GCs",
            "both": "Both (Bot Users + Deal GCs)"
        }
        dest_label = mode_labels.get(target_type, target_type.upper())

        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="bd:cancel")]])
        await query.message.edit_text(
            f"<b>📢 Broadcast Content — {dest_label}</b>\n\n"
            f"Now send or forward the message you want to broadcast.\n\n"
            f"Supports media, stickers, videos, photos, documents, custom emojis, and formatted text.\n"
            f"Click Cancel below to abort.",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_kb
        )

    elif action == "confirm":
        setup = context.user_data.pop("broadcast_setup", None)
        if not setup:
            await query.message.edit_text("❌ Broadcast session expired. Run /bd again.")
            return

        global _active_broadcast_task
        if _active_broadcast_task and not _active_broadcast_task.done():
            await query.message.edit_text("⚠️ Another broadcast is currently running. Please wait.")
            return

        await query.message.edit_text("⏳ <b>Starting broadcast…</b> Live progress updates will follow.", parse_mode=ParseMode.HTML)
        _active_broadcast_task = asyncio.create_task(
            execute_broadcast(
                bot=context.bot,
                owner_id=query.from_user.id,
                target_type=setup["target_type"],
                from_chat_id=setup["from_chat_id"],
                message_id=setup["message_id"]
            )
        )

async def execute_broadcast(bot, owner_id: int, target_type: str, from_chat_id: int, message_id: int) -> None:
    """Rate-limited robust broadcast execution engine copied and adapted from test_otcbot.py."""
    started_at = time.time()
    targets: List[Dict[str, Any]] = []

    if target_type == "users":
        u_list = await get_active_users()
        for u in u_list:
            u["is_group"] = 0
            targets.append(u)
    elif target_type == "groups":
        g_list = await get_active_groups()
        for g in g_list:
            g["is_group"] = 1
            targets.append(g)
    else:  # both
        u_list = await get_active_users()
        for u in u_list:
            u["is_group"] = 0
            targets.append(u)
        g_list = await get_active_groups()
        for g in g_list:
            g["is_group"] = 1
            targets.append(g)

    total = len(targets)
    broadcast_id = await create_broadcast(
        sender_id=owner_id,
        target_type=target_type,
        message_id=message_id,
        from_chat_id=from_chat_id,
        total_targets=total,
        started_at=started_at
    )

    success_cnt = 0
    failed_cnt = 0
    blocked_cnt = 0
    progress_msg = None

    try:
        progress_msg = await bot.send_message(
            chat_id=owner_id,
            text=f"📢 <b>Broadcast #{broadcast_id} in progress:</b> 0/{total}",
            parse_mode=ParseMode.HTML
        )
    except TelegramError:
        pass

    last_update_time = time.time()

    for idx, t in enumerate(targets, start=1):
        target_id = t["id"]
        is_grp = t.get("is_group", 0)
        status = "SUCCESS"
        error_msg = None

        try:
            # copy_message perfectly preserves media, stickers, videos, custom emojis & formatting
            await bot.copy_message(chat_id=target_id, from_chat_id=from_chat_id, message_id=message_id)
            success_cnt += 1
        except RetryAfter as exc:
            wait = float(getattr(exc, "retry_after", 3.0))
            await asyncio.sleep(wait)
            try:
                await bot.copy_message(chat_id=target_id, from_chat_id=from_chat_id, message_id=message_id)
                success_cnt += 1
            except Exception as retry_exc:
                failed_cnt += 1
                status = "FAILED"
                error_msg = str(retry_exc)[:200]
        except Forbidden as exc:
            blocked_cnt += 1
            status = "BLOCKED"
            error_msg = str(exc)[:200]
            if is_grp:
                await set_group_active(target_id, 0)
            else:
                await set_user_active(target_id, 0)
        except TelegramError as exc:
            failed_cnt += 1
            status = "FAILED"
            error_msg = str(exc)[:200]

        await record_broadcast_recipient(
            broadcast_id=broadcast_id,
            target_id=target_id,
            target_name=t.get("name") or "Unknown",
            target_username=t.get("username"),
            is_group=is_grp,
            status=status,
            error_msg=error_msg,
            created_at=time.time()
        )

        # Periodic live progress update every 3s
        if progress_msg and (time.time() - last_update_time > 3.0 or idx == total):
            try:
                await progress_msg.edit_text(
                    f"📢 <b>Broadcast #{broadcast_id} Progress:</b>\n"
                    f"Processed: <b>{idx}/{total}</b> | Success: <b>{success_cnt}</b> | Failed: <b>{failed_cnt}</b>",
                    parse_mode=ParseMode.HTML
                )
                last_update_time = time.time()
            except TelegramError:
                pass

        await asyncio.sleep(0.04)

    finished_at = time.time()
    duration = max(0.1, finished_at - started_at)

    await finish_broadcast(
        broadcast_id=broadcast_id,
        success_count=success_cnt,
        failed_count=failed_cnt,
        blocked_count=blocked_cnt,
        finished_at=finished_at,
        status="COMPLETED"
    )

    report_text = (
        f"<b>✅ Broadcast #{broadcast_id} Completed!</b>\n\n"
        f"• <b>Destination:</b> {target_type.upper()}\n"
        f"• <b>Total Recipients:</b> {total}\n"
        f"• <b>Successful:</b> {success_cnt}\n"
        f"• <b>Failed:</b> {failed_cnt}\n"
        f"• <b>Blocked/Kicked:</b> {blocked_cnt}\n"
        f"• <b>Duration:</b> {human_time(duration)}"
    )

    recipients = await get_broadcast_recipients(broadcast_id)
    if len(recipients) <= 20:
        lines = ["\n<b>Recipient Breakdown:</b>"]
        for r in recipients:
            uname = f"@{r['target_username']}" if r["target_username"] else "None"
            lines.append(f"• [{r['status']}] {r['target_name']} ({uname}, ID <code>{r['target_id']}</code>)")
        report_text += "\n" + "\n".join(lines)
        await bot.send_message(owner_id, report_text, parse_mode=ParseMode.HTML)
    else:
        buf = io.StringIO()
        buf.write("=====================================================\n")
        buf.write(f"CURRENCING BOT — BROADCAST REPORT #{broadcast_id}\n")
        buf.write("=====================================================\n")
        buf.write(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        buf.write(f"Destination: {target_type.upper()}\n")
        buf.write(f"Total: {total} | Success: {success_cnt} | Failed: {failed_cnt} | Blocked: {blocked_cnt}\n")
        buf.write(f"Duration: {human_time(duration)}\n")
        buf.write("-----------------------------------------------------\n")
        buf.write("RECIPIENT BREAKDOWN:\n")
        for r in recipients:
            uname = f"@{r['target_username']}" if r["target_username"] else "None"
            err = f" | Error: {r['error_msg']}" if r["error_msg"] else ""
            buf.write(f"[{r['status']}] ID: {r['target_id']} | Name: {r['target_name']} | Username: {uname}{err}\n")
        buf.seek(0)
        doc = io.BytesIO(buf.getvalue().encode("utf-8"))
        doc.name = f"broadcast_report_{broadcast_id}.txt"
        await bot.send_document(owner_id, document=doc, caption=report_text, parse_mode=ParseMode.HTML)
