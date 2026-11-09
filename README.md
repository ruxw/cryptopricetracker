# Currencing – Cryptocurrency Intelligence & Statistics Telegram Bot

A production-ready cryptocurrency price-tracking, market-intelligence, and conversion Telegram bot built with Python, `python-telegram-bot`, `aiohttp`, `aiosqlite`, and `Pillow`.

> **Note:** Currencing is an intelligence, statistics, and conversion tool. It is **NOT** a cryptocurrency exchange, trading desk, deposit, or swapping platform.

---

## 🌟 Visual Identity & Currencing Branding

The bot dynamically renders four core image templates featuring the **Currencing** brand identity and the official brand icon from `Logo.png`:

1. **Individual Coin Statistics with 7-Day Price Chart** (`1024 × 640`)
2. **3×3 Multi-Coin Market Overview Grid** (`1024 × 614`)
3. **All-Time High (ATH) Statistics Card** (`1024 × 640`)
4. **Cryptocurrency-to-Fiat Conversion Card** (`1024 × 640`)

All 9 coin icons (`BTC, ETH, SOL, GRAM, LTC, XMR, XRP, BNB, TRX`) are circular badges with transparent backgrounds.

---

## 📢 Force Join Channels & Groups System

You can require users to join specific Telegram channels or group chats before using any bot features:

In `.env`:
```ini
# Supports: @username, t.me/link, https://t.me/link (comma-separated)
FORCE_JOINS=@CurrencingNews, t.me/CurrencingChat, https://t.me/CryptoAlerts
# Or:
# Force_joins=t.me/link1, t.me/link2
```

### How It Works:
- When a user interacts with the bot (via `/start`, commands, callbacks, or inline mode), their membership is verified across all specified channels.
- If not joined, the bot presents a prompt with **column-stacked buttons (one channel per row)**:
  ```
  [ 📢 Join @CurrencingNews ]
  [ 📢 Join @CurrencingChat ]
  [ 📢 Join @CryptoAlerts   ]
  [   ✅ I Have Joined      ]
  ```
- Tapping **`✅ I Have Joined`** instantly re-checks membership. Once joined, access to all features is granted immediately.

---

## ⚙️ Configuration & Environment Variables

```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=@CurrencingBot

# Force Join (optional)
FORCE_JOINS=@CurrencingNews, t.me/CurrencingChat

DB_PATH=data/currencing_bot.db
CACHE_TTL_SECONDS=60
BACKGROUND_SYNC_INTERVAL=120
```

---

## 🚀 Quickstart

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Enable inline mode in `@BotFather` (`/setinline`).
3. Run tests:
   ```bash
   pytest tests
   ```
4. Start the bot:
   ```bash
   python main.py
   ```
