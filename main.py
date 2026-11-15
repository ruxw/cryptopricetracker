import asyncio
import logging
import os
import sys
from aiohttp import web
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    filters
)

from bot.config import BOT_TOKEN, BACKGROUND_SYNC_INTERVAL
from bot.database import init_db
from bot.services.crypto_api import crypto_service
from bot.handlers.start import start_command, help_command, start_callback, check_force_join_callback
from bot.handlers.overview import overview_command, overview_callback
from bot.handlers.stats import stats_command, stats_callback
from bot.handlers.ath import ath_command, ath_callback
from bot.handlers.convert import convert_command, convert_callback
from bot.handlers.crypto import crypto_command, coin_shortcut, top_command
from bot.handlers.meme import (
    satoshi_command, cope_command, panic_command,
    wagmi_command, predict_command, didyouknow_command,
    me_command, firstseen_command, lookup_command,
    chatvibe_command
)
from bot.handlers.sponsored import sponsored_command, sponsored_callback
from bot.handlers.broadcast import broadcast_command, broadcast_callback
from bot.handlers.owner_messages import owner_message_handler
from bot.handlers.inline import inline_query_handler
from bot.handlers.group import group_fallback_handler, bot_added_to_group_handler

# Configure rich logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CURRENCING_BOT")

async def background_market_sync():
    """Background task to continuously keep crypto market cache fresh."""
    logger.info("Starting background crypto market data sync task...")
    while True:
        try:
            await crypto_service.refresh_market_data(force=True)
        except Exception as e:
            logger.error("Error in background market sync: %s", e)
        await asyncio.sleep(BACKGROUND_SYNC_INTERVAL)

async def start_health_server():
    """Lightweight HTTP server to satisfy Render Free Web Service health checks."""
    port = int(os.getenv("PORT", "10000"))
    async def handle_ping(request):
        return web.Response(text="Currencing Bot OK", status=200)

    server = web.Application()
    server.router.add_get("/", handle_ping)
    server.router.add_get("/health", handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Render health server active on port %d", port)
    return runner

def setup_application(token: str):
    """Build and configure the Telegram Bot Application."""
    from telegram.ext import Application
    app = ApplicationBuilder().token(token).build()

    # ── Owner-only commands (registered first so they intercept before all else) ──
    app.add_handler(CommandHandler(["bd", "broadcast"], broadcast_command))
    app.add_handler(CommandHandler("sponsored", sponsored_command))

    # ── Callback Queries: owner wizards (must be before generic CBQ handlers) ──
    app.add_handler(CallbackQueryHandler(sponsored_callback, pattern="^sp:"))
    app.add_handler(CallbackQueryHandler(broadcast_callback, pattern="^bd:"))

    # ── Owner wizard private messages (group=0 → runs before regular handlers) ──
    async def _owner_msg_wrapper(update, context):
        """Wraps owner_message_handler; stops propagation if handled."""
        from telegram.ext import ApplicationHandlerStop
        if await owner_message_handler(update, context):
            raise ApplicationHandlerStop()

    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, _owner_msg_wrapper),
        group=0
    )

    # ── Public Commands ──
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["overview", "market"], overview_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("crypto", crypto_command))
    app.add_handler(CommandHandler("ath", ath_command))
    app.add_handler(CommandHandler("convert", convert_command))

    # ── 👻 Fun & Meme Commands ──
    app.add_handler(CommandHandler("satoshi", satoshi_command))
    app.add_handler(CommandHandler("cope", cope_command))
    app.add_handler(CommandHandler("panic", panic_command))
    app.add_handler(CommandHandler("wagmi", wagmi_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("didyouknow", didyouknow_command))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("firstseen", firstseen_command))
    app.add_handler(CommandHandler("lookup", lookup_command))
    app.add_handler(CommandHandler("chatvibe", chatvibe_command))

    # Per-coin shortcuts (14 Coins with Custom Emojis)
    shortcuts = {
        "btc": "BTC", "eth": "ETH", "sol": "SOL", "bnb": "BNB", "xrp": "XRP",
        "doge": "DOGE", "ada": "ADA", "avax": "AVAX", "ton": "GRAM", "gram": "GRAM",
        "trx": "TRX", "ltc": "LTC", "xmr": "XMR", "shib": "SHIB", "pepe": "PEPE"
    }
    for cmd, sym in shortcuts.items():
        app.add_handler(CommandHandler(cmd, lambda u, c, s=sym: coin_shortcut(u, c, s)))

    # Inline Queries (Group Guest Mode & Everywhere)
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # ── Public Callback Queries ──
    app.add_handler(CallbackQueryHandler(overview_callback, pattern="^(nav_overview|refresh_overview)$"))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="^(stats_.*|refresh_stats_.*|nav_stats_menu)$"))
    app.add_handler(CallbackQueryHandler(ath_callback, pattern="^(ath_.*|nav_ath_menu)$"))
    app.add_handler(CallbackQueryHandler(convert_callback, pattern="^(conv_.*|nav_convert_menu)$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^nav_help$"))
    app.add_handler(CallbackQueryHandler(start_callback, pattern="^(nav_start|help:menu)$"))
    app.add_handler(CallbackQueryHandler(check_force_join_callback, pattern="^check_force_join$"))

    # Group guest mode fallback & member updates (group=1 so owner handler runs first)
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_fallback_handler), group=1)
    app.add_handler(ChatMemberHandler(bot_added_to_group_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    return app

async def main():
    if not BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set in environment or .env file!\n"
            "Please create a .env file with TELEGRAM_BOT_TOKEN=<your_token>."
        )
        sys.exit(1)

    # 1. Initialize persistent SQLite database
    await init_db()

    # 2. Warm up crypto cache on startup
    logger.info("Warming up cryptocurrency market data cache...")
    await crypto_service.refresh_market_data(force=True)

    # 3. Start background sync
    asyncio.create_task(background_market_sync())

    # 4. Start health server for Render Free Web Service
    health_runner = None
    if os.getenv("PORT") or os.getenv("RENDER"):
        try:
            health_runner = await start_health_server()
        except Exception as e:
            logger.warning("Could not start HTTP health server: %s", e)

    # 5. Build application & start polling
    app = setup_application(BOT_TOKEN)

    # 5. Register BotFather command menu
    from telegram import BotCommand
    commands = [
        BotCommand("btc",        "Bitcoin price & 7-day chart"),
        BotCommand("eth",        "Ethereum price & 7-day chart"),
        BotCommand("sol",        "Solana price & 7-day chart"),
        BotCommand("bnb",        "BNB price & 7-day chart"),
        BotCommand("xrp",        "XRP price & 7-day chart"),
        BotCommand("doge",       "Dogecoin price & 7-day chart"),
        BotCommand("ton",        "Toncoin/Gram price & 7-day chart"),
        BotCommand("shib",       "Shiba Inu price & 7-day chart"),
        BotCommand("pepe",       "Pepe price & 7-day chart"),
        BotCommand("crypto",     "Track any of 23+ cryptocurrencies"),
        BotCommand("top",        "Market overview – top coins"),
        BotCommand("ath",        "All-time high records"),
        BotCommand("convert",    "Currency converter (e.g. $100 eth)"),
        BotCommand("satoshi",    "Random quote from Satoshi Nakamoto"),
        BotCommand("cope",       "Gain vs All-Time Low (ATL)"),
        BotCommand("panic",      "Emergency panic index & checklist"),
        BotCommand("wagmi",      "Today's top rocket gainers"),
        BotCommand("predict",    "100% technical price prediction"),
        BotCommand("didyouknow", "Crypto history & trivia"),
        BotCommand("me",         "Your usage intelligence recap"),
        BotCommand("firstseen",  "Price change since first check"),
        BotCommand("lookup",     "Compare last check vs now"),
        BotCommand("chatvibe",   "This chat's most-checked coins"),
        BotCommand("help",       "Help & full command menu"),
    ]

    logger.info("Currencing Crypto Intelligence & Statistics Bot is now running!")

    async with app:
        await app.start()
        # Register bot command menu with BotFather
        try:
            await app.bot.set_my_commands(commands)
            logger.info("Bot command menu registered successfully.")
        except Exception as e:
            logger.warning("Could not set bot commands: %s", e)
        await app.updater.start_polling(drop_pending_updates=True)
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            if health_runner:
                await health_runner.cleanup()
            await app.updater.stop()
            await app.stop()
            await crypto_service.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
