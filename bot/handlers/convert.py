import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.graphics.templates import render_conversion
from bot.graphics.assets import COINS, FIAT_CURRENCIES, format_price
from bot.emojis import coin_fallback, ui_fallback

logger = logging.getLogger(__name__)

def get_crypto_selector_keyboard() -> InlineKeyboardMarkup:
    """Step 1: Select cryptocurrency — clean single emoji buttons."""
    keyboard = [
        [
            InlineKeyboardButton(f"{coin_fallback('BTC')} BTC", callback_data="conv_c_BTC"),
            InlineKeyboardButton(f"{coin_fallback('ETH')} ETH", callback_data="conv_c_ETH"),
            InlineKeyboardButton(f"{coin_fallback('SOL')} SOL", callback_data="conv_c_SOL"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('BNB')} BNB", callback_data="conv_c_BNB"),
            InlineKeyboardButton(f"{coin_fallback('XRP')} XRP", callback_data="conv_c_XRP"),
            InlineKeyboardButton(f"{coin_fallback('DOGE')} DOGE", callback_data="conv_c_DOGE"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('GRAM')} GRAM", callback_data="conv_c_GRAM"),
            InlineKeyboardButton(f"{coin_fallback('ADA')} ADA", callback_data="conv_c_ADA"),
            InlineKeyboardButton(f"{coin_fallback('AVAX')} AVAX", callback_data="conv_c_AVAX"),
        ],
        [
            InlineKeyboardButton(f"{coin_fallback('LTC')} LTC", callback_data="conv_c_LTC"),
            InlineKeyboardButton(f"{coin_fallback('SHIB')} SHIB", callback_data="conv_c_SHIB"),
            InlineKeyboardButton(f"{coin_fallback('PEPE')} PEPE", callback_data="conv_c_PEPE"),
        ],
        [
            InlineKeyboardButton(f"{ui_fallback('chart')} Market Overview", callback_data="nav_overview"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_amount_preset_keyboard(crypto: str) -> InlineKeyboardMarkup:
    """Step 2: Select or customize amount."""
    # Context-aware presets based on coin price scale
    if crypto in ["BTC", "ETH"]:
        presets = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
    elif crypto in ["LTC", "SOL", "BNB", "XMR", "AVAX"]:
        presets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    elif crypto in ["SHIB", "PEPE"]:
        presets = [100000, 500000, 1000000, 5000000, 10000000, 50000000]
    else:  # DOGE, GRAM, XRP, TRX, ADA
        presets = [10.0, 50.0, 100.0, 500.0, 1000.0, 5000.0]

    keyboard = [
        [
            InlineKeyboardButton(f"{presets[0]:,}" if isinstance(presets[0], int) else f"{presets[0]}", callback_data=f"conv_a_{crypto}_{presets[0]}"),
            InlineKeyboardButton(f"{presets[1]:,}" if isinstance(presets[1], int) else f"{presets[1]}", callback_data=f"conv_a_{crypto}_{presets[1]}"),
            InlineKeyboardButton(f"{presets[2]:,}" if isinstance(presets[2], int) else f"{presets[2]}", callback_data=f"conv_a_{crypto}_{presets[2]}")
        ],
        [
            InlineKeyboardButton(f"{presets[3]:,}" if isinstance(presets[3], int) else f"{presets[3]}", callback_data=f"conv_a_{crypto}_{presets[3]}"),
            InlineKeyboardButton(f"{presets[4]:,}" if isinstance(presets[4], int) else f"{presets[4]}", callback_data=f"conv_a_{crypto}_{presets[4]}"),
            InlineKeyboardButton(f"{presets[5]:,}" if isinstance(presets[5], int) else f"{presets[5]}", callback_data=f"conv_a_{crypto}_{presets[5]}")
        ],
        [
            InlineKeyboardButton("Change Asset", callback_data="nav_convert_menu"),
            InlineKeyboardButton("Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_fiat_selector_keyboard(crypto: str, amount: float) -> InlineKeyboardMarkup:
    """Step 3: Select target fiat currency with colorful flags."""
    keyboard = [
        [
            InlineKeyboardButton("💵 USD ($)", callback_data=f"conv_f_{crypto}_{amount}_USD"),
            InlineKeyboardButton("💶 EUR (€)", callback_data=f"conv_f_{crypto}_{amount}_EUR"),
            InlineKeyboardButton("💷 GBP (£)", callback_data=f"conv_f_{crypto}_{amount}_GBP")
        ],
        [
            InlineKeyboardButton("💴 JPY (¥)", callback_data=f"conv_f_{crypto}_{amount}_JPY"),
            InlineKeyboardButton("🍁 CAD ($)", callback_data=f"conv_f_{crypto}_{amount}_CAD"),
            InlineKeyboardButton("🇦🇺 AUD ($)", callback_data=f"conv_f_{crypto}_{amount}_AUD")
        ],
        [
            InlineKeyboardButton("🇮🇳 INR (₹)", callback_data=f"conv_f_{crypto}_{amount}_INR"),
            InlineKeyboardButton("🇨🇭 CHF (Fr)", callback_data=f"conv_f_{crypto}_{amount}_CHF"),
            InlineKeyboardButton("🇷🇺 RUB (₽)", callback_data=f"conv_f_{crypto}_{amount}_RUB")
        ],
        [
            InlineKeyboardButton("🔙 Change Amount", callback_data=f"conv_c_{crypto}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="nav_start")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_conversion_result_keyboard(crypto: str, amount: float, current_fiat: str) -> InlineKeyboardMarkup:
    """Navigation keyboard on conversion result."""
    # Alternate fiat options
    alt_fiats = [f for f in ["USD", "EUR", "GBP", "JPY"] if f != current_fiat][:3]
    fiat_buttons = [
        InlineKeyboardButton(f"To {f}", callback_data=f"conv_f_{crypto}_{amount}_{f}")
        for f in alt_fiats
    ]

    keyboard = [
        fiat_buttons,
        [
            InlineKeyboardButton("🔄 Change Amount", callback_data=f"conv_c_{crypto}"),
            InlineKeyboardButton("💱 Convert Other Asset", callback_data="nav_convert_menu")
        ],
        [
            InlineKeyboardButton(f"📈 {crypto} Chart & Stats", callback_data=f"stats_{crypto}"),
            InlineKeyboardButton("📊 Market Overview", callback_data="nav_overview")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /convert command.
    Supports:
    - /convert                        → opens interactive wizard
    - /convert 0.5 btc                → 0.5 BTC → USD
    - /convert 0.5 btc eur            → 0.5 BTC → EUR
    - /convert $100 eth               → how much ETH $100 buys  (USD → crypto)
    - /convert <crypto> <amount>      → crypto→USD legacy order
    """
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    args = context.args or []

    # ── no arguments → interactive wizard ─────────────────────────────────────
    if not args:
        await update.message.reply_text(
            "How to use /convert\n"
            "Type /convert, an amount and a coin:\n\n"
            "/convert 0.5 btc: 0.5 BTC in USD\n"
            "/convert $100 eth: how much ETH $100 buys",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_crypto_selector_keyboard(),
        )
        return

    # ── detect "$100 eth" mode (USD → crypto) ─────────────────────────────────
    if args[0].startswith("$"):
        try:
            usd_amount = float(args[0][1:].replace(",", ""))
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid amount. Example: `/convert $100 eth`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        raw_coin = args[1] if len(args) > 1 else ""
        symbol = resolve_coin(raw_coin) or (raw_coin.upper() if raw_coin.upper() in COINS else None)
        if not symbol:
            await update.message.reply_text(
                f"❌ Unknown coin `{raw_coin}`. Example: `/convert $100 eth`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        status_msg = await context.bot.send_message(
            chat_id, "⏳ _Generating conversion card..._", parse_mode=ParseMode.MARKDOWN
        )
        try:
            coin_data = await crypto_service.get_coin_data(symbol)
            usd_price = coin_data["current_price"]
            crypto_amount = usd_amount / usd_price  # e.g. $100 / $2131 = 0.0469 ETH

            # Render card: top = "Ethereum | 0.0469", bottom = "$100.00 | USD $"
            image_buf = render_conversion(
                crypto_symbol=symbol,
                crypto_amount=crypto_amount,
                fiat_symbol="USD",
                fiat_value=usd_amount,
                reverse=True,  # signals the template to swap display sides
            )

            coin_name = COINS[symbol]["name"]
            caption = (
                f"**{coin_name}** you get for **${usd_amount:,.2f} USD**\n"
                f"`{crypto_amount:.6f} {symbol}` at `${format_price(usd_price)} / {symbol}`"
            )

            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_buf,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.error("Error in reverse convert command: %s", e)
            await context.bot.send_message(chat_id, "❌ Conversion error. Please try again.")
        finally:
            try:
                await status_msg.delete()
            except Exception:
                pass
        return

    # ── normal mode: /convert 0.5 btc [fiat] ──────────────────────────────────
    crypto: Optional[str] = None
    amount: Optional[float] = None
    fiat: str = "USD"

    try:
        amount = float(args[0].replace(",", ""))
        raw_coin = args[1] if len(args) > 1 else ""
        crypto = resolve_coin(raw_coin) or (raw_coin.upper() if raw_coin.upper() in COINS else None)
        if len(args) > 2:
            fiat = args[2].upper()
    except (ValueError, IndexError):
        # Legacy order: /convert LTC 0.3
        raw_coin = args[0]
        crypto = resolve_coin(raw_coin) or (raw_coin.upper() if raw_coin.upper() in COINS else None)
        if len(args) > 1:
            try:
                amount = float(args[1].replace(",", ""))
            except ValueError:
                amount = None
        if len(args) > 2:
            fiat = args[2].upper()

    if not crypto or crypto not in COINS or amount is None or amount <= 0:
        await update.message.reply_text(
            "How to use /convert\n"
            "Type /convert, an amount and a coin:\n\n"
            "/convert 0.5 btc: 0.5 BTC in USD\n"
            "/convert $100 eth: how much ETH $100 buys",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_crypto_selector_keyboard(),
        )
        return

    if fiat not in FIAT_CURRENCIES:
        fiat = "USD"

    status_msg = await context.bot.send_message(
        chat_id, "⏳ _Generating live conversion card..._", parse_mode=ParseMode.MARKDOWN
    )
    try:
        res = await crypto_service.convert(crypto, amount, fiat)
        image_buf = render_conversion(
            crypto_symbol=crypto,
            crypto_amount=amount,
            fiat_symbol=fiat,
            fiat_value=res["fiat_value"],
        )

        fiat_info = FIAT_CURRENCIES[fiat]
        f_sign = fiat_info["symbol"]
        f_val_str = f"{f_sign}{format_price(res['fiat_value'], decimals=fiat_info['decimals'])}"
        coin_name = COINS[crypto]["name"]

        caption = (
            f"**{amount} {coin_name}** = **{f_val_str} {fiat}**\n"
            f"Rate: `1 {crypto} = ${format_price(res['usd_price'])} USD`"
        )
        kb = get_conversion_result_keyboard(crypto, amount, fiat)

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_buf,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
    except Exception as e:
        logger.error("Error in convert command: %s", e)
        await context.bot.send_message(chat_id, "❌ Conversion error. Please try again.")
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass

async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive conversion wizard steps."""
    query = update.callback_query
    await query.answer()

    if not await check_user_authorization(update, context):
        return

    data = query.data
    chat_id = update.effective_chat.id

    # Menu request
    if data == "nav_convert_menu":
        await context.bot.send_message(
            chat_id,
            "💱 **Currencing Crypto Converter**\n\nStep 1: Select the cryptocurrency you want to convert:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_crypto_selector_keyboard()
        )
        return

    # From stats shortcut: conv_from_BTC
    if data.startswith("conv_from_"):
        crypto = data.replace("conv_from_", "").upper()
        await context.bot.send_message(
            chat_id,
            f"💱 **Converting {COINS.get(crypto, {}).get('name', crypto)} ({crypto})**\n\nStep 2: Select an amount or type `/convert <amount> {crypto}`:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_amount_preset_keyboard(crypto)
        )
        return

    # Step 1 -> Step 2: Selected crypto (conv_c_BTC)
    if data.startswith("conv_c_"):
        crypto = data.replace("conv_c_", "").upper()
        coin_name = COINS.get(crypto, {}).get("name", crypto)
        await context.bot.send_message(
            chat_id,
            f"💱 **Converting {coin_name} ({crypto})**\n\nStep 2: Choose amount preset:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_amount_preset_keyboard(crypto)
        )
        return

    # Step 2 -> Step 3: Selected amount (conv_a_BTC_0.5)
    if data.startswith("conv_a_"):
        parts = data.split("_")
        if len(parts) >= 4:
            crypto = parts[2].upper()
            amount = float(parts[3])
            coin_name = COINS.get(crypto, {}).get("name", crypto)
            await context.bot.send_message(
                chat_id,
                f"💱 **Converting {amount} {coin_name} ({crypto})**\n\nStep 3: Select target fiat currency:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_fiat_selector_keyboard(crypto, amount)
            )
            return

    # Step 3 -> Generate Card: Selected fiat (conv_f_BTC_0.5_USD)
    if data.startswith("conv_f_"):
        parts = data.split("_")
        if len(parts) >= 5:
            crypto = parts[2].upper()
            amount = float(parts[3])
            fiat = parts[4].upper()

            res = await crypto_service.convert(crypto, amount, fiat)
            image_buf = render_conversion(
                crypto_symbol=crypto,
                crypto_amount=amount,
                fiat_symbol=fiat,
                fiat_value=res["fiat_value"]
            )

            fiat_info = FIAT_CURRENCIES.get(fiat, {"symbol": "$", "decimals": 2})
            f_sign = fiat_info["symbol"]
            f_val_str = f"{f_sign}{format_price(res['fiat_value'], decimals=fiat_info['decimals'])}"
            coin_name = COINS.get(crypto, {}).get("name", crypto)

            caption = (
                f"💱 **Currencing Conversion Result**\n"
                f"• **Asset:** `{amount} {coin_name} ({crypto})`\n"
                f"• **Converted Value:** `{f_val_str}` ({fiat})\n"
                f"• **Rate:** `1 {crypto} = ${format_price(res['usd_price'])} USD`\n\n"
                f"_Professional conversion card generated dynamically:_"
            )
            kb = get_conversion_result_keyboard(crypto, amount, fiat)

            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_buf,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
            return
