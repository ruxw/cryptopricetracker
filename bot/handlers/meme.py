"""
Fun and Meme Command Handlers for Currencing Bot:
- /satoshi    — Random quote from Satoshi Nakamoto card (expanded pool, non-repeating)
- /daily      — Daily crypto thought & philosophical insight card
- /meme       — Relatable crypto degen meme & trading truth card
- /cope       — Calculates your gain vs the All-Time Low (ATL) card
- /panic      — Emergency panic index meter & calming checklist card
- /wagmi      — Today's top market gainers card
- /predict    — Technical price target projection card
- /didyouknow — Interesting crypto history and trivia card
- /me         — User intelligence profile card
- /firstseen  — Date/time you first checked that coin and price change since then card
- /lookup     — Compares price when you last checked vs right now card
- /chatvibe   — Top checked coins inside this Telegram group card

Note: Incomplete commands teach users via clean Usage: /cmd <coin name> format.
Buttons only display native custom emojis without redundant doubled Unicode emojis.
"""

import random
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import deque
from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes

from bot.middlewares.auth import check_user_authorization
from bot.services.crypto_api import crypto_service
from bot.services.resolver import resolve_coin
from bot.services.sponsored import attach_sponsored_content
from bot.database import (
    get_user_first_seen, get_user_last_lookup,
    get_user_profile_stats, get_chat_top_coins,
    record_coin_lookup
)
from bot.graphics.templates import (
    render_satoshi_quote, render_daily_quote, render_meme_card,
    render_cope_card, render_panic_card, render_wagmi_card,
    render_predict_card, render_didyouknow_card, render_me_profile_card,
    render_firstseen_card, render_lookup_card, render_chatvibe_card
)
from bot.graphics.assets import COINS
from bot.emojis import E, coin_emoji, custom_btn

logger = logging.getLogger(__name__)

# ─── 35+ ICONIC SATOSHI NAKAMOTO ARCHIVE QUOTES ────────────────────────────────
SATOSHI_QUOTES = [
    "If you don't believe it or don't get it, I don't have the time to try to convince you, sorry.",
    "The root problem with conventional currency is all the trust that's required to make it work. Central banks must be trusted not to debase the currency, but fiat history is full of breaches.",
    "It might make sense just to get some in case it catches on. If enough people think the same way, that becomes a self-fulfilling prophecy.",
    "Lost coins only make everyone else's coins worth slightly more. Think of it as a donation to everyone.",
    "I'm sure that in 20 years there will either be very large transaction volume or no volume.",
    "The nature of Bitcoin is such that once version 0.1 was released, the core design was set in stone for the rest of its lifetime.",
    "With e-currency based on cryptographic proof, without trusting middlemen, money can be secure and transactions effortless.",
    "A lot of people automatically dismiss e-currency as a lost cause because of all the companies that failed since the 1990s. It's obvious it was only the centrally controlled nature that doomed them.",
    "Bitcoin is an electronic payment system based on cryptographic proof instead of trust, allowing any two willing parties to transact directly.",
    "At first, most users would run network nodes, but as the network grows, more will be left to server farms of specialized hardware.",
    "Nodes can leave and rejoin the network at will, accepting the longest proof-of-work chain as proof of what happened while they were gone.",
    "Proof-of-work has the nice property that it can be relayed through untrusted middlemen. It doesn't matter who delivers it.",
    "The steady addition of a constant amount of new coins is analogous to gold miners expending resources to add gold to circulation.",
    "In this sense, it's more typical of a precious metal. Instead of the supply changing to keep the value the same, the supply is predetermined and the value changes.",
    "As the number of users grows, the value per coin increases. It has the potential for a positive feedback loop; as users increase, the value goes up.",
    "I've moved on to other things. It's in good hands with Gavin and everyone.",
    "Right now, the network is tiny. But when someone needs to send a payment across the world quickly without permission, Bitcoin is unmatched.",
    "We can win a major battle in the arms race and gain a new territory of freedom for several years.",
    "Governments are good at cutting off the heads of a centrally controlled network like Napster, but pure P2P networks like Gnutella and Tor seem to hold their own.",
    "It is strictly necessary that the longest chain always be considered the valid one. Proof-of-work is the consensus.",
    "The possibility to be anonymous or pseudonymous relies on you not revealing any identifying information about yourself in connection with the bitcoin addresses you use.",
    "Writing a description for this thing for general audiences is bloody hard. There's nothing to relate it to.",
    "The incentive may help encourage nodes to stay honest. If a greedy attacker is able to assemble more CPU power than all the honest nodes, he would find it more profitable to play by the rules.",
    "It's very attractive to the libertarian viewpoint if we can explain it properly. I'm better with code than with words, though.",
    "Total circulation will be 21,000,000 coins. It will be distributed to network nodes when they make blocks, with the amount halved every 4 years.",
    "When there are multiple chains of equal length, nodes work on the first one received but keep the other in case it becomes longer.",
    "The computer was originally an amplifier for human thought. Bitcoin is an amplifier for human economic sovereignty.",
    "Central banks have shown time and again they will debase currency whenever political pressure rises. Mathematics has no such loyalty.",
    "Commerce on the Internet has come to rely almost exclusively on financial institutions serving as trusted third parties. This trust cost is what we eliminate.",
    "There is no mechanism to undo a transaction once it is buried under enough proof-of-work. That finality is freedom.",
    "To generate coins, a node computes a hash of the block header. The difficulty targets self-adjust every two weeks to maintain the 10-minute cadence.",
    "Sovereignty means not having to ask anyone for permission to spend, save, or store the fruit of your labor.",
    "If you have extra processing power, putting it towards verifying blocks secures the entire global ledger.",
    "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks. (Genesis Block embedded message)",
    "Once an encrypted electronic transaction is broadcast, it spreads across nodes peer-to-peer like ripples across water."
]

# ─── 35+ INSPIRING DAILY CRYPTO THOUGHTS & WISDOM ─────────────────────────────
DAILY_THOUGHTS = [
    ("Running Bitcoin.", "Hal Finney, First Bitcoin Contributor (2009)", "Bitcoin History"),
    ("Bitcoin is a remarkable cryptographic achievement, and the ability to create something that is not duplicable in the digital world has enormous value.", "Eric Schmidt, Former CEO of Google", "Tech Visionaries"),
    ("Money is the bubble that never pops. Gold was the first, and Bitcoin is the digital evolution.", "Naval Ravikant, Investor & Philosopher", "Crypto Economics"),
    ("Ethereum is a decentralized platform that runs smart contracts: applications that run exactly as programmed without any possibility of downtime or third-party interference.", "Vitalik Buterin, Founder of Ethereum", "Decentralized Apps"),
    ("I see Bitcoin as ultimately becoming a reserve currency for banks, playing much the same role as gold did in the early days of banking.", "Hal Finney (1956–2014)", "Cypherpunk Archives"),
    ("Bitcoin does what the entire banking system cannot: it transfers absolute value globally at the speed of light without counterparty risk.", "Andreas Antonopoulos, Author of Mastering Bitcoin", "Financial Sovereignty"),
    ("You can't stop Bitcoin. It's like trying to stop the internet. Math and code are impervious to executive orders.", "John McAfee", "Blockchain Culture"),
    ("Bitcoin is a bank in cyberspace, run by software that has never called in sick, never taken a holiday, and never discriminated against anyone.", "Michael Saylor, Founder of MicroStrategy", "Corporate Treasury"),
    ("Smart contracts guarantee performance. In an untrusted world, code is the purest mediator of agreements.", "Nick Szabo, Computer Scientist & Cryptographer", "Smart Contracts"),
    ("Every fiat currency in human history has eventually returned to its intrinsic value: zero. Bitcoin fixes this.", "Milton Friedman Predicted Digital Cash in 1999", "Economic Theory"),
    ("In a world of infinite printing, scarcity is power. 21 million is the hard cap of digital reality.", "Saifedean Ammous, Author of The Bitcoin Standard", "Sound Money"),
    ("Web3 is about ownership. Web1 was read, Web2 was read-write, Web3 is read-write-own.", "Chris Dixon, Technologist & Investor", "Next Gen Web"),
    ("Volatility is the price you pay for uncapped upside. You cannot have generational returns with fixed-deposit predictability.", "Raoul Pal, Macro Investor", "Market Cycles"),
    ("Do not save what is left after spending; invest in scarce digital assets first, then spend what is left.", "Crypto Principle for Wealth Preservation", "Wealth Strategy"),
    ("A decentralized network has no central point of failure. Attack one node, and ten thousand others continue verifying the ledger unbroken.", "Gavin Andresen, Early Bitcoin Developer", "Distributed Systems"),
    ("The beauty of open source money is that anyone with an internet connection has the exact same financial privileges as a billionaire.", "Jack Dorsey, Co-founder of Twitter", "Open Financial System"),
    ("Bear markets build character and infrastructure. Bull markets reward the conviction cultivated in the cold.", "WAGMI Wisdom", "Market Psychology"),
    ("Self-custody of your private keys is the highest form of personal responsibility in the 21st century.", "Cypherpunk Manifesto", "Key Security"),
    ("Gold has physical weight, requires vaults, and is difficult to verify. Bitcoin is weightless, travels anywhere in seconds, and verifies instantly.", "Wences Casares, Pioneer of Bitcoin", "Digital Gold"),
    ("The strongest hands are forged when the charts look red. Conviction without testing is just wishful thinking.", "Veteran Trader Maxim", "Trading Discipline"),
    ("Bitcoin is the exit strategy from a debt-based monetary system designed to erode your purchasing power every single year.", "Robert Breedlove, What Is Money Show", "Macro Economics"),
    ("Ethereum turned the blockchain from a distributed calculator into a global distributed world computer.", "Camila Russo, Author of The Infinite Machine", "Ethereum Revolution"),
    ("Don't verify by trusting a brand or politician; verify by running your own node and auditing the ledger.", "Blockchain First Principle", "Zero Trust Architecture"),
    ("Patience in crypto is rewarded disproportionately. The most profitable trade is often simply holding through the noise.", "Charlie Lee, Creator of Litecoin", "Long-term Investing"),
    ("Decentralized finance means transparent liquidity pools, open protocols, and financial inclusion for the 2 billion unbanked.", "Stani Kulechov, Founder of Aave", "DeFi Frontiers"),
    ("Inflation is a hidden tax on everyone who works and saves in fiat. Cryptographic scarcity is the antidote.", "Friedrich Hayek, Nobel Laureate in Economics", "Economic Liberty"),
    ("When you own your Bitcoin in cold storage, no court, bank, or government can freeze your wealth with the click of a button.", "Alex Gladstein, Human Rights Foundation", "Human Rights"),
    ("Crypto does not sleep. Markets operate 24/7/365 across every timezone on Earth without closing bells.", "Global Liquidity Principle", "Market Structure"),
    ("The most revolutionary technology of our generation is not AI alone, but the cryptographic rails that enable digital ownership and truth.", "Balaji Srinivasan, Author of The Network State", "Digital Frontier"),
    ("Always remember: when price dumps 10%, the underlying blockchain still produced blocks every 10 minutes without a hiccup.", "Network Health Principle", "On-Chain Reality"),
    ("Generational wealth is made during the quiet accumulation phases when tourists have left and builders remain.", "Crypto Founder Maxim", "Builder Sentiment"),
    ("A wallet address is an open doorway to the global financial system. No permission slip, ID photo, or credit score required.", "Open Finance Ethos", "Inclusion"),
    ("The ledger does not lie. Proof of work bridges digital abstractions with thermodynamics and physics.", "Satoshi Nakamoto", "Proof of Work"),
    ("Hold onto sound money, continue learning every day, and never let short-term market noise cloud long-term vision.", "Currencing Daily Intelligence", "Daily Motivation")
]

# ─── 35+ RELATABLE CRYPTO MEMES & TRADING TRUTHS ──────────────────────────────
MEME_VAULT = [
    ("Buying The Dip", "You bought the dip, but then the dip dipped, and the dip's dip took a deeper dip into the abyss.", "Verdict: You are now a proud long-term holder."),
    ("The 3 AM Portfolio Check", "Waking up at 3:17 AM in pitch darkness to check your 1-minute candle chart like an undercover CIA operative.", "Verdict: Down $4.80. Heart rate: 160 BPM."),
    ("DCA Masterclass", "Dollar Cost Averaging all the way from the All-Time High straight into generational depression.", "Verdict: True Chad discipline. Respect."),
    ("1 BTC = 1 BTC", "Explaining to your landlord that your net worth dropped 30% today, but mathematically 1 Bitcoin still equals 1 Bitcoin.", "Verdict: Landlord only accepts dirty fiat."),
    ("The Family Dinner", "Your uncle asking how your 'internet play-money' is doing while he deposits cash into a 0.05% bank account.", "Verdict: Stay silent anon, the bull run is coming."),
    ("Taking Profits Dilemma", "Never taking profits because 'it's definitely going higher,' followed by panic selling at the absolute bottom wick.", "Verdict: Peak retail trader behavior."),
    ("Gas Fee Shock", "Attempting to swap $12 worth of a meme coin and being politely asked to pay $84.20 in Ethereum gas fees.", "Verdict: Vitalik please grant us L2 salvation."),
    ("The Fibonacci Expert", "Drawing 47 rainbow trendlines, 3 triangles, and an acoustic bat pattern on TradingView to justify buying more.", "Verdict: 100% scientific horoscope."),
    ("Diamond Hands Reality", "Claiming you have diamond hands until you see a single 5-minute red candle and sweat through your mattress.", "Verdict: Paper hands disguised in armor."),
    ("Ramen vs Lambo", "Eating instant noodles for 6 straight months so you can buy 0.04 more Solana at resistance.", "Verdict: Priorities are immaculate anon."),
    ("The Crypto Sleep Cycle", "Going to sleep up 40% and waking up liquidated because a whale sneezed on Binance at 4:21 AM.", "Verdict: Rest in peace limit orders."),
    ("Meme Coin Philosophy", "Reading a 60-page whitepaper on zero-knowledge rollups vs blindly aping $500 into a dog with a hat.", "Verdict: The dog coin pumped 300%."),
    ("Touching Grass Protocol", "Your friends telling you to go outside and touch grass, but grass doesn't have 24h trading volume or staking APY.", "Verdict: Nature has terrible tokenomics."),
    ("The Tax Season Panic", "Staring at 4,800 micro-swaps on Uniswap trying to remember if swapping PEPE for SHIB was a taxable event.", "Verdict: Good luck to your accountant."),
    ("Cold Storage Paranoia", "Writing your 24-word seed phrase on steel plates, burying it in 3 different continents, and forgetting where.", "Verdict: Ultimate cryptographic security."),
    ("HODL Until Retirement", "Telling everyone you are holding until 2045, but checking the price 180 times between lunch and dinner.", "Verdict: Emotional roller coaster enthusiast."),
    ("The Telegram Alpha Group", "Joining a private VIP trading group where the 'expert analyst' posts a chart with one green arrow pointing to the moon.", "Verdict: Financial advisor licensed in MS Paint."),
    ("Bear Market Survival", "Surviving an 85% market crash and feeling completely immune to any psychological pain in ordinary human life.", "Verdict: Unshakable stoic warrior."),
    ("The Influencer Target", "Crypto YouTuber making an open-mouth thumbnail: 'URGENT BITCOIN ALERT!! MASSIVE CRASH OR $250K TONIGHT?!'", "Verdict: Nobody knows anything."),
    ("Hardware Wallet Ceremony", "Entering your pin on a Ledger Nano like you are disarming a nuclear warhead in a Mission Impossible film.", "Verdict: Clean transaction approved."),
    ("Altcoin Season Delusion", "Watching Bitcoin break all-time highs while your favorite obscure altcoin sits completely motionless like a statue.", "Verdict: Patience anon, rotation is coming."),
    ("The Accidental Long-Term Investor", "Aping into a high-leverage pump and dump, losing 80%, and suddenly declaring: 'I actually believe in the tech.'", "Verdict: Copium levels: Maximum."),
    ("The Crypto Millionaire Friend", "Watching a 19-year-old on Twitter make 2 million dollars trading virtual hamster tokens while you work 9-5.", "Verdict: We live in a simulation."),
    ("Market Order Regret", "Hitting market buy without checking the order book depth and slipping 14% into the liquidity void.", "Verdict: Always use limit orders anon."),
    ("The Bull Market Genius", "Making 400% in a raging bull market and convincing yourself you are superior to Warren Buffett and Ray Dalio combined.", "Verdict: Everyone is a genius in an uptrend."),
    ("The Liquidation Text", "Seeing that dreaded Telegram alert: 'Your position has reached 90% margin threshold.'", "Verdict: Time to delete the app and take a walk."),
    ("The Airdrop Farmer", "Bridging $5 across 17 different testnets for 8 consecutive months to receive an airdrop worth $3.12.", "Verdict: Honest work for honest farmers."),
    ("Satoshi's Wallet Watcher", "Monitoring Satoshi Nakamoto's wallet every day like a hawk just in case the legend wakes up and sells a satoshi.", "Verdict: 1.1 million Bitcoin still resting peacefully."),
    ("The Staking Lockup", "Locking your tokens for 12 months for 18% APY only for the underlying token to dump 90% during the lockup.", "Verdict: Math is cruel sometimes."),
    ("Zero Balance Awakening", "Opening your wallet and it displays $0.00 because RPC failed to connect for 3 seconds. Heart stops instantly.", "Verdict: 3 seconds of sheer panic."),
    ("The Exchange Maintenance", "Bitcoin drops 10% and suddenly every major crypto exchange goes into 'scheduled emergency server maintenance.'", "Verdict: Classic Wall Street tradition digitized."),
    ("The Next 100x Coin", "Your friend whispering: 'Bro, I found the next Solana, it's called MegaSafeRocketElon.'", "Verdict: Run away as fast as possible."),
    ("The Cycle Veteran", "Listening to newcomers panic over a 5% drop when you lived through Mt. Gox, the 2018 winter, and the FTX collapse.", "Verdict: Scars of glory."),
    ("Green Candles Therapy", "One single 15-minute green candle turning the entire sentiment of Twitter from suicide hotline to Lambo shopping.", "Verdict: Crypto sentiment moves at light speed.")
]

# ─── NON-REPEATING HISTORY TRACKERS ───────────────────────────────────────────
_recent_satoshi: Dict[int, deque] = {}
_recent_daily: Dict[int, deque] = {}
_recent_meme: Dict[int, deque] = {}

def _get_next_index(chat_id: int, pool_size: int, history_dict: Dict[int, deque]) -> int:
    """Select a random index while ensuring no recent repetition."""
    if chat_id not in history_dict:
        history_dict[chat_id] = deque(maxlen=max(1, min(pool_size - 1, 20)))

    recent = set(history_dict[chat_id])
    available = [i for i in range(pool_size) if i not in recent]
    if not available:
        history_dict[chat_id].clear()
        available = list(range(pool_size))

    idx = random.choice(available)
    history_dict[chat_id].append(idx)
    return idx

async def _send_fun_card(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    image_buf: Any,
    reply_msg_id: Optional[int] = None,
    kb: Optional[InlineKeyboardMarkup] = None
) -> None:
    """Send image card with active sponsored quotation caption and sponsored button."""
    sp_caption, sp_markup = await attach_sponsored_content(reply_markup=kb)
    send_kwargs = {
        "chat_id": chat_id,
        "photo": image_buf,
        "reply_markup": sp_markup,
    }
    if reply_msg_id:
        send_kwargs["reply_to_message_id"] = reply_msg_id
    if sp_caption:
        send_kwargs["caption"] = sp_caption
        send_kwargs["parse_mode"] = ParseMode.HTML

    await context.bot.send_photo(**send_kwargs)

# ─── 1. /satoshi (Expanded & Non-Repeating) ────────────────────────────────────
async def satoshi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send random Satoshi Nakamoto quote card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    # Immediate chat action — NO temporary text message!
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        idx = _get_next_index(chat_id, len(SATOSHI_QUOTES), _recent_satoshi)
        quote = SATOSHI_QUOTES[idx]
        image_buf = render_satoshi_quote(quote)

        # Interactive action buttons with single custom emojis
        kb = InlineKeyboardMarkup([
            [custom_btn("Another Quote", callback_data="fun:satoshi", icon="dice")],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing"),
             custom_btn("BTC Live", callback_data="stats_BTC", coin="BTC")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /satoshi: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Satoshi card. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 2. /daily (New Daily Thought Quote Card) ─────────────────────────────────
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send daily crypto thought & wisdom card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    # Chat action without loading message
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        idx = _get_next_index(chat_id, len(DAILY_THOUGHTS), _recent_daily)
        quote, author, source = DAILY_THOUGHTS[idx]
        image_buf = render_daily_quote(quote, author, source)

        kb = InlineKeyboardMarkup([
            [custom_btn("Next Thought", callback_data="fun:daily", icon="dice")],
            [custom_btn("Fun Meme", callback_data="fun:meme", icon="meme"),
             custom_btn("Top Overview", callback_data="nav_overview", icon="chart")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /daily: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Daily card. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 3. /meme (New Daily Fun Crypto Meme Card) ─────────────────────────────────
async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send daily fun crypto meme & degen truth card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    # Chat action without loading message
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        idx = _get_next_index(chat_id, len(MEME_VAULT), _recent_meme)
        title, body, punchline = MEME_VAULT[idx]
        image_buf = render_meme_card(title, body, punchline)

        kb = InlineKeyboardMarkup([
            [custom_btn("Another Meme", callback_data="fun:meme", icon="meme")],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing"),
             custom_btn("Top Rockets", callback_data="fun:wagmi", icon="ath")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /meme: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Meme card. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── FUN COMMANDS CALLBACK HANDLER ─────────────────────────────────────────────
async def fun_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive button callbacks for /satoshi, /daily, /meme."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "fun:satoshi":
        await satoshi_command(update, context)
    elif data == "fun:daily":
        await daily_command(update, context)
    elif data == "fun:meme":
        await meme_command(update, context)
    elif data == "fun:wagmi":
        await wagmi_command(update, context)

# ─── 4. /cope <coin> ──────────────────────────────────────────────────────────
async def cope_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /cope card vs All-Time Low."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/cope &lt;coin name&gt;\n<i>ex /cope btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_sym = args[0]
    symbol = resolve_coin(raw_sym) or raw_sym.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"<b>Unknown coin:</b> {raw_sym}\n\n<b>Usage:</b>\n/cope &lt;coin name&gt;\n<i>ex /cope btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data.get("current_price", 1.0)
        atl_info = crypto_service.get_atl_data(symbol)
        atl_price = atl_info.get("atl", 0.01)
        atl_date = atl_info.get("date", "Historical")

        image_buf = render_cope_card(symbol, price, atl_price, atl_date)
        kb = InlineKeyboardMarkup([
            [custom_btn(f"{symbol} Chart", callback_data=f"stats_{symbol}", coin=symbol),
             custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /cope: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Cope card for {symbol}.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 5. /panic <coin> ─────────────────────────────────────────────────────────
async def panic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send emergency /panic index meter & calming protocol card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/panic &lt;coin name&gt;\n<i>ex /panic btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_sym = args[0]
    symbol = resolve_coin(raw_sym) or raw_sym.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"<b>Unknown coin:</b> {raw_sym}\n\n<b>Usage:</b>\n/panic &lt;coin name&gt;\n<i>ex /panic btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data.get("current_price", 1.0)
        change_24h = coin_data.get("change_24h", 0.0)

        image_buf = render_panic_card(symbol, price, change_24h)
        kb = InlineKeyboardMarkup([
            [custom_btn("Cope ATL", callback_data="fun:satoshi", icon="gem"),
             custom_btn(f"{symbol} ATH", callback_data=f"ath_{symbol}", icon="ath")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /panic: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Panic card for {symbol}.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 6. /wagmi ────────────────────────────────────────────────────────────────
async def wagmi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /wagmi rocket leaderboard card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        gainers = await crypto_service.get_top_gainers(limit=5)
        image_buf = render_wagmi_card(gainers)
        kb = InlineKeyboardMarkup([
            [custom_btn("Top Market Overview", callback_data="nav_overview", icon="chart")],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /wagmi: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate WAGMI card.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 7. /predict <coin> ───────────────────────────────────────────────────────
async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send technical price target projection card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/predict &lt;coin name&gt;\n<i>ex /predict btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_sym = args[0]
    symbol = resolve_coin(raw_sym) or raw_sym.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"<b>Unknown coin:</b> {raw_sym}\n\n<b>Usage:</b>\n/predict &lt;coin name&gt;\n<i>ex /predict btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        coin_data = await crypto_service.get_coin_data(symbol)
        price = coin_data.get("current_price", 100.0)

        # Mathematical humorous targets based on fibonacci golden ratio multipliers
        multipliers = [1.618, 2.618, 3.1415, 4.20, 7.77]
        m = random.choice(multipliers)
        prediction_target = price * m
        predicted_gain = (m - 1.0) * 100.0

        image_buf = render_predict_card(symbol, price, prediction_target, predicted_gain)
        kb = InlineKeyboardMarkup([
            [custom_btn(f"{symbol} 7-Day Chart", callback_data=f"stats_{symbol}", coin=symbol)],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /predict: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Prediction card for {symbol}.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 8. /didyouknow <coin> ────────────────────────────────────────────────────
DID_YOU_KNOW_FACTS = {
    "BTC": ("The Legendary 10,000 BTC Pizza", "On May 22, 2010, Laszlo Hanyecz bought two pizzas for 10,000 Bitcoins. At peak prices, those two pizzas were worth over $900 million dollars!"),
    "ETH": ("Vitalik's World of Warcraft Origin", "Vitalik Buterin created Ethereum after Blizzard nerfed his beloved World of Warcraft character. He realized the horrors of centralized services and set out to build decentralized applications."),
    "SOL": ("Proof of History Breakthrough", "Solana was conceptualized by Anatoly Yakovenko while drinking coffee and beer. He realized time could be verified cryptographically through recursive SHA-256 hashing, solving the clock synchronization problem."),
    "DOGE": ("Created in 3 Hours as a Joke", "Billy Markus and Jackson Palmer coded Dogecoin in roughly 3 hours in 2013 by forking Luckycoin and replacing the font with Comic Sans. It went on to reach an $80 billion market cap."),
    "TON": ("The Telegram Gram Resurgence", "Telegram raised $1.7 billion for the original Gram ICO in 2018. When SEC halted it, open-source developers kept the code alive, which Telegram eventually officially embraced."),
    "XMR": ("The Ultimate Untraceable Fungibility", "Monero utilizes Ring Signatures, Stealth Addresses, and RingCT so that neither the sender, receiver, nor transaction amount is ever visible on the public blockchain."),
    "LTC": ("The Silver to Bitcoin's Gold", "Charlie Lee created Litecoin in 2011 with 2.5-minute blocks and Scrypt proof-of-work, making it one of the longest continuously running operational blockchains in history."),
    "BNB": ("From ICO to Ecosystem Juggernaut", "Binance launched BNB in July 2017 via an ICO raising $15 million at roughly $0.15 per token. It has since appreciated over 400,000%."),
    "XRP": ("Pre-Dating Bitcoin Concepts", "The conceptual roots of RipplePay date back to 2004 by Ryan Fugger, years before Satoshi published the Bitcoin whitepaper in late 2008."),
    "TRX": ("High Volume Stablecoin Highway", "TRON currently settles more USDT (Tether) daily transaction volume than the Ethereum network, making it the highest volume stablecoin settlement layer in the world.")
}

async def didyouknow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /didyouknow crypto history & lore card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/didyouknow &lt;coin name&gt;\n<i>ex /didyouknow btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_sym = args[0]
    symbol = resolve_coin(raw_sym) or raw_sym.upper()

    fact = DID_YOU_KNOW_FACTS.get(symbol.upper(), DID_YOU_KNOW_FACTS["BTC"])
    title, body = fact

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        image_buf = render_didyouknow_card(symbol, title, body)
        kb = InlineKeyboardMarkup([
            [custom_btn("Another Trivia", callback_data="fun:satoshi", icon="help"),
             custom_btn(f"{symbol} Chart", callback_data=f"stats_{symbol}", coin=symbol)]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /didyouknow: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Trivia card for {symbol}.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 9. /me ───────────────────────────────────────────────────────────────────
async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /me user profile card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    user = update.effective_user
    if not user:
        return

    try:
        stats = await get_user_profile_stats(user.id)
        image_buf = render_me_profile_card(
            user_id=stats["user_id"],
            username=stats["username"],
            first_name=stats["first_name"],
            joined_at=stats["joined_at"],
            total_lookups=stats["total_lookups"],
            favorite_coin=stats["favorite_coin"]
        )
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id)
    except Exception as e:
        logger.error("Error in /me: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Profile card.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 10. /firstseen <coin> ────────────────────────────────────────────────────
async def firstseen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /firstseen time capsule card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/firstseen &lt;coin name&gt;\n<i>ex /firstseen btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_sym = args[0]
    symbol = resolve_coin(raw_sym) or raw_sym.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"<b>Unknown coin:</b> {raw_sym}\n\n<b>Usage:</b>\n/firstseen &lt;coin name&gt;\n<i>ex /firstseen btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    user = update.effective_user
    if not user:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        fs = await get_user_first_seen(user.id, symbol)
        coin_data = await crypto_service.get_coin_data(symbol)
        curr_price = coin_data.get("current_price", 100.0)

        if not fs:
            await record_coin_lookup(user.id, symbol, curr_price, chat_id=chat_id)
            first_price = curr_price
            first_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        else:
            first_price = fs["price"]
            first_time = fs["created_at"]

        image_buf = render_firstseen_card(symbol, first_price, curr_price, str(first_time)[:16])
        kb = InlineKeyboardMarkup([
            [custom_btn(f"{symbol} Chart", callback_data=f"stats_{symbol}", coin=symbol)]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /firstseen: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate First Seen card for {symbol}.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 11. /lookup <coin> ───────────────────────────────────────────────────────
async def lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /lookup price delta card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "<b>Usage:</b>\n/lookup &lt;coin name&gt;\n<i>ex /lookup btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    raw_sym = args[0]
    symbol = resolve_coin(raw_sym) or raw_sym.upper()

    if symbol not in COINS:
        await update.message.reply_text(
            f"<b>Unknown coin:</b> {raw_sym}\n\n<b>Usage:</b>\n/lookup &lt;coin name&gt;\n<i>ex /lookup btc</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
        return

    user = update.effective_user
    if not user:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        last_rec = await get_user_last_lookup(user.id, symbol)
        coin_data = await crypto_service.get_coin_data(symbol)
        curr_price = coin_data.get("current_price", 100.0)

        if not last_rec:
            await record_coin_lookup(user.id, symbol, curr_price, chat_id=chat_id)
            last_price = curr_price
            last_time = "Just now"
        else:
            last_price = last_rec["price"]
            last_time = str(last_rec["created_at"])[:16]

        image_buf = render_lookup_card(symbol, last_price, curr_price, last_time)
        kb = InlineKeyboardMarkup([
            [custom_btn(f"{symbol} Chart", callback_data=f"stats_{symbol}", coin=symbol)]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /lookup: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Lookup card for {symbol}.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 12. /chatvibe ────────────────────────────────────────────────────────────
async def chatvibe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /chatvibe group market pulse card."""
    if not await check_user_authorization(update, context):
        return

    chat = update.effective_chat
    if not chat:
        return

    reply_msg_id = update.effective_message.message_id if update.effective_message else None
    await context.bot.send_chat_action(chat_id=chat.id, action="upload_photo")

    title = chat.title or "Private Intelligence"
    try:
        top_coins = await get_chat_top_coins(chat.id, limit=5)
        image_buf = render_chatvibe_card(title, top_coins)
        kb = InlineKeyboardMarkup([
            [custom_btn("Global Overview", callback_data="nav_overview", icon="chart")]
        ])
        await _send_fun_card(context, chat.id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /chatvibe: %s", e)
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"{E('cross')} Failed to generate Chat Vibe card.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )
