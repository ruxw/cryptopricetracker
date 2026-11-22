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

from bot.config import BOT_USERNAME

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
    ("Hold onto sound money, continue learning every day, and never let short-term market noise cloud long-term vision.", "Currencing Daily Intelligence", "Daily Motivation"),
    ("Bitcoin is Venice in the 14th century, the printing press in the 15th, and the Internet in the 20th.", "Nic Carter, Castle Island Ventures", "Economic Evolution"),
    ("The Open Network is bringing decentralized freedom to over 900 million Telegram users worldwide.", "Pavel Durov, Telegram & TON Visionary", "Telegram Ecosystem"),
    ("You don't change Bitcoin. Bitcoin changes you.", "Michael Saylor, Executive Chairman MicroStrategy", "Bitcoin Mindset"),
    ("Smart contracts are unstoppable code. Once deployed, they answer to nobody except the laws of mathematics.", "Vitalik Buterin, Co-founder of Ethereum", "World Computer"),
    ("In a financial system built on debt and inflation, holding an unprintable asset is the ultimate act of rebellion.", "Lyn Alden, Macro Economist & Author", "Broken Money"),
    ("Monero proves that privacy is not about having something to hide, but about having boundaries that belong to you.", "Cypherpunk Principle", "Privacy & Sovereignty"),
    ("Solana took the blockchain throughput from a dial-up modem directly into fiber-optic light speeds.", "Anatoly Yakovenko, Co-founder of Solana", "High-Performance Chains"),
    ("When the world realizes that fiat currency is melting ice, they will run towards digital scarcity.", "Dan Morehead, Founder Pantera Capital", "Macro Allocations"),
    ("The hardest money ever conceived by human civilization is Bitcoin.", "Saifedean Ammous", "Austrian Economics"),
    ("Ethereum is creating an entire decentralized economy with zero central banks, zero boardrooms, and pure open liquidity.", "Camila Russo", "DeFi Revolution"),
    ("If you hold your own keys, you are your own central bank, vault, and auditor combined.", "Andreas Antonopoulos", "Sovereign Banking"),
    ("Financial censorship ends where peer-to-peer cryptography begins.", "Open Source Crypto Ethos", "Digital Liberty"),
    ("Every halving reminds the world that human greed cannot alter Bitcoin's mathematical clock.", "Crypto Philosophy", "The Halving Principle"),
    ("Decentralized networks survive bears because code does not panic, capitulate, or doubt itself.", "On-Chain Conviction", "Resilience"),
    ("The dollar was backed by gold, then by promises, and now by printing presses. Bitcoin is backed by thermodynamics.", "Robert Breedlove", "Hard Money"),
    ("Real wealth is freedom of time, freedom of movement, and money that no entity can debase.", "Crypto Sovereign Ethos", "Sovereignty"),
    ("The greatest transfer of wealth in human history is quietly happening right now on public ledgers.", "Macro Intelligence", "Generational Shift"),
    ("Those who understand monetary history buy Bitcoin. Those who understand technology buy Ethereum.", "Crypto Maxim", "Crypto Philosophy"),
    ("Trust code, audit everything, verify keys, and stay humble.", "Currencing Core Maxim", "Timeless Wisdom")
]

# ─── 50+ RELATABLE CRYPTO MEMES & TRADING TRUTHS (REDDIT TOP UPVOTED) ─────────
# Sources: r/CryptoCurrencyMemes, r/SatoshiStreetBets, r/CryptoIndia,
# r/IndianStreetBets, r/IndianDankMemes, r/DesiDankMemes
MEME_VAULT = [
    # ── r/CryptoCurrencyMemes Top Upvoted ──
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
    ("Buy High, Sell Low Legend", "Flawlessly bought the top wick at $69k, sold the bottom wick at $16k, and re-bought the new top at $73k.", "Verdict: Hall of Fame buy-high-sell-low champion."),
    ("In It For The Tech", "Portfolio dumps 85% in 48 hours: 'Honestly, I never cared about the money anyway, the underlying cryptography is truly revolutionary.'", "Verdict: Copium levels: Maximum."),
    ("Crypto vs Stocks", "Stock trader: 'I am down 1.2% this quarter, my life is ruined.' Crypto degen: 'Down 72% before breakfast, feeling quite bullish honestly.'", "Verdict: Built different."),

    # ── r/SatoshiStreetBets Top Upvoted ──
    ("100x Leverage Roulette", "Taking out a personal loan to open a 100x isolated long position because an anonymous anime account tweeted 'LFG'.", "Verdict: Margin call arrived in 42 seconds."),
    ("Wendy's Dumpster Backup Plan", "Preparing the resume update: 'Experienced risk manager transitioning to junior fry-cook and Frosty operations.'", "Verdict: Sir, this is a casino."),
    ("Ape Together Strong", "10,000 retail degens all coordinating to buy a dead shitcoin at 4:20 PM to squeeze the offshore market makers.", "Verdict: Decentralized chaos achieved."),
    ("The Screenshot Rule", "If it's good enough to screenshot, it's good enough to sell. But did you sell? Of course not, you held it all the way back to zero.", "Verdict: Eternal screenshot collector."),
    ("The Influencer Target", "Crypto YouTuber making an open-mouth thumbnail: 'URGENT BITCOIN ALERT!! MASSIVE CRASH OR $250K TONIGHT?!'", "Verdict: Nobody knows anything."),
    ("The Bull Market Genius", "Making 400% in a raging bull market and convincing yourself you are superior to Warren Buffett and Ray Dalio combined.", "Verdict: Everyone is a genius in an uptrend."),
    ("The Airdrop Farmer", "Bridging $5 across 17 different testnets for 8 consecutive months to receive an airdrop worth $3.12.", "Verdict: Honest work for honest farmers."),
    ("Zero Balance Awakening", "Opening your wallet and it displays $0.00 because RPC failed to connect for 3 seconds. Heart stops instantly.", "Verdict: 3 seconds of sheer panic."),

    # ── r/CryptoIndia Top Upvoted ──
    ("30% Tax + 1% TDS Partnership", "Indian crypto traders discovering the Government is an equity partner in their profits, but takes zero responsibility for their losses.", "Verdict: Welcome to Section 115BBH."),
    ("The P2P Bank Account Freeze", "Sold 0.001 BTC on Binance P2P for ₹5,000, now your SBI account with 10 years of savings is frozen by Cyber Crime Police.", "Verdict: Classic Indian P2P baptism."),
    ("Moving to Dubai Dream", "Every Indian crypto bro with $800 in phantom profits researching freelance visas and tax-free apartments in Dubai Marina.", "Verdict: Flights are booked anon."),
    ("Draft Bill Rumor Season", "Panic selling your entire portfolio at midnight because an unverified Twitter handle tweeted 'Cabinet to discuss crypto ban bill tomorrow'.", "Verdict: 6th time this cycle."),
    ("Sandeep Nailwal Vision", "Watching Polygon MATIC grow from a Mumbai apartment to scaling Ethereum worldwide: 'Desi builders on top.'", "Verdict: Desi crypto pride."),

    # ── r/IndianStreetBets Top Upvoted ──
    ("Harshad Mehta Background Score", "Buying $10 worth of Pepe while the 1992 Scam theme plays on full blast on your Bluetooth speaker.", "Verdict: Risk hai toh ishq hai."),
    ("FD vs Crypto Battle", "Father: 'Beta SBI FD is giving guaranteed 7.1% APY.' Me: 'Papa my memecoin did 400% in 12 minutes before the liquidity was pulled.'", "Verdict: Belan protocol activated."),
    ("Double Samosa Pattern", "Drawing a samosa-shaped breakout triangle on TradingView and calling it elite institutional technical analysis.", "Verdict: Guaranteed breakout with green chutney."),
    ("Zomato Delivery vs Trading", "Spending 6 hours day-trading crypto for a net profit of ₹42, while your Zomato delivery guy makes ₹500 in tips.", "Verdict: Financial wizardry."),
    ("Nirmala Ji Watching", "Making a ₹150 profit on Shiba Inu and immediately looking over your shoulder to see if Income Tax department noticed.", "Verdict: Advance tax advance payment."),

    # ── r/IndianDankMemes & r/DesiDankMemes Top Upvoted ──
    ("Sharma Ji Ka Beta Dilemma", "Sharma ji ka beta got ₹35 LPA IT package. You told relatives you are an 'Algorithmic Web3 Quant' (holding 4,000 Dogecoins).", "Verdict: Relative izzat at all-time low."),
    ("Ghar Jayenga Isme", "Looking at the 15-minute liquidations chart and hearing MC Stan whisper in your ear: 'Isme tera ghar chala jayenga'.", "Verdict: Pure street wisdom."),
    ("Ek Din Me Paisa Double", "Watching Laxmi Chit Fund memes while staking coins on a shady decentralized protocol offering 4,000% APY.", "Verdict: Anuradha was Satoshi all along."),
    ("Pehle Investment, Phir Soch", "Investing first, checking the coin whitepaper never, and asking in Telegram group: 'Bhai pump kab hoga?'", "Verdict: The sacred ritual."),
    ("Relatives Asking Career", "Relatives: 'Beta kya karte ho?' Me: 'Decentralized liquidity and sovereign cryptography operations.' (I have ₹400 in Doge).", "Verdict: International finance consultant.", "DOGE"),

    # ── Multi-Coin Dedicated & Universal Memes ──
    ("Bitcoin Halving Anxiety", "Staring at the Bitcoin block countdown clock like it is New Year's Eve, expecting an instant green God candle to blast through your ceiling.", "Verdict: Halving priced in since 2012.", "BTC"),
    ("Ethereum Gas Fees Again", "Paying $48 in gas fees to approve a token contract so you can pay another $72 in gas fees to actually swap it.", "Verdict: Ultrasound gas burns.", "ETH"),
    ("Solana TPS Velocity", "Sending a Solana transaction that confirms before your thumb leaves the screen, only to realize you sent it to the wrong address at light speed.", "Verdict: Unmatched speed of sorrow.", "SOL"),
    ("Telegram Stars & Gram", "Tapping your screen 50,000 times a day in Telegram mini apps to earn $1.40 worth of Gram/TON.", "Verdict: Certified full-time digital laborer.", "GRAM"),
    ("TON Wallet Awakening", "Opening Telegram, finding out Durov sent you TON for being a channel member, and feeling like Satoshi personally blessed your chat.", "Verdict: Pavel Durov is the chosen one.", "GRAM"),
    ("Monero Boating Incident", "Explaining to tax authorities why your hard drive fell into the Marianas Trench during a tragic fishing accident.", "Verdict: 100% untraceable submarine incident.", "XMR"),
    ("XRP Courtroom Marathon", "Holding XRP through 4 US presidential administrations, 3 bear markets, and 8,000 pages of legal filings.", "Verdict: Gary Gensler's retirement gift.", "XRP"),
    ("BNB Launchpool Farming", "Locking all your life savings into BNB launchpool for 3 days to earn 0.0004 of a new gaming governance token.", "Verdict: Funds are SAFU, yield is microscopic.", "BNB"),
    ("Litecoin The Old Reliable", "Litecoin has not halted, failed, or missed a single block in 13 years, but nobody ever talks about it until it pumps 40% out of nowhere.", "Verdict: Digital silver stays unfazed.", "LTC"),
    ("Tron USDT Energy Rental", "Sending $10,000 across the globe on Tron for exactly $1.20 while Ethereum traders look on in absolute disbelief.", "Verdict: Justin Sun's gift to retail.", "TRX"),
    ("Dogecoin Twitter Signal", "Selling your car because an Elon Musk tweet had a Shiba Inu emoji in the bottom-left corner.", "Verdict: Barking at resistance levels.", "DOGE"),
    ("Pepe The Green Candle Prophet", "A green cartoon frog with zero utility outperforming every Wall Street institutional hedge fund on Earth.", "Verdict: Feels extremely good man.", "PEPE"),
    ("Shiba Army Vision", "Calculating how much money you will have when Shiba Inu reaches $1.00 (which would require more money than exists in the galaxy).", "Verdict: Mathematical imagination is infinite.", "SHIB"),
    ("Cardano Whitepaper Reading", "Reading peer-reviewed academic papers in Latin to understand why your ADA stake pool earned 0.002 ADA this epoch.", "Verdict: Charles Hoskinson whiteboard supremacy.", "ADA"),
    ("Avalanche Subnet Rush", "Setting up an Avalanche subnet because you wanted your own sovereign blockchain just to trade digital dog pictures with your friends.", "Verdict: Sub-second finality flex.", "AVAX"),
    ("Chainlink Oracle Supremacy", "Every blockchain on earth arguing about consensus while Sergey Nazarov's oracles feed them all the exact same data anyway.", "Verdict: The fourth industrial revolution runs on oracles.", "LINK"),
    ("100x Short Squeeze", "Deciding to short Bitcoin at resistance, only to watch a green candle punch straight through the atmosphere and liquidation notification arrive.", "Verdict: RIP collateral.", "BTC"),
    ("Telegram Tap-To-Earn Fatigue", "Your phone screen has an actual thumb impression burnt into the OLED glass from tapping hamsters for 4 months.", "Verdict: Silicon Valley is baffled.", "GRAM"),
    ("The Ghost In Monero", "Privacy maximalist sending Monero from a burner laptop in a Faraday cage inside a submarine.", "Verdict: Anonymity level: 9000.", "XMR"),
    ("Ethereum Merge Nostalgia", "Remembering when Ethereum miners used enough electricity to power small European countries, now it runs on pure conviction.", "Verdict: Green energy maxis rejoiced.", "ETH")
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
    kb: Optional[InlineKeyboardMarkup] = None,
    caption: Optional[str] = None
) -> None:
    """Send image card with active sponsored quotation caption or clean default caption."""
    sp_caption, sp_markup = await attach_sponsored_content(reply_markup=kb)
    final_caption = sp_caption or caption
    send_kwargs = {
        "chat_id": chat_id,
        "photo": image_buf,
        "reply_markup": sp_markup,
    }
    if reply_msg_id:
        send_kwargs["reply_to_message_id"] = reply_msg_id
    if final_caption:
        send_kwargs["caption"] = final_caption
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

        # Interactive action buttons in clean single-column layout
        kb = InlineKeyboardMarkup([
            [custom_btn("Another Quote", callback_data="fun:satoshi", icon="dice")],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing")],
            [custom_btn("BTC Live", callback_data="stats_BTC", coin="BTC")]
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
        quote_item = DAILY_THOUGHTS[idx]
        quote, author, source = quote_item[0], quote_item[1], quote_item[2]
        image_buf = render_daily_quote(quote, author, source)

        today_date = datetime.utcnow().strftime("%d/%m")
        clean_caption = (
            f"{E('currencing')} <b>Daily Thoughts · {today_date}</b>\n"
            f"via @{BOT_USERNAME}. Tap /meme or /top for more."
        )

        kb = InlineKeyboardMarkup([
            [custom_btn("Next Thought", callback_data="fun:daily", icon="dice")],
            [custom_btn("Fun Meme", callback_data="fun:meme", icon="meme")],
            [custom_btn("Top Overview", callback_data="nav_overview", icon="chart")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb, caption=clean_caption)
    except Exception as e:
        logger.error("Error in /daily: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Daily card. Please try again.",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_msg_id
        )

# ─── 3. /meme (Daily Fun Crypto Meme Card — Any Coin) ─────────────────────────
async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send daily fun crypto meme & degen truth card for any coin."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    # Chat action without loading message
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        args = context.args or []
        req_sym = None
        if args:
            raw_target = args[0].strip()
            req_sym = resolve_coin(raw_target) or raw_target.upper()
            if req_sym == "TON":
                req_sym = "GRAM"

        # If user asked for specific coin, filter by that coin if available
        matched_indices = []
        if req_sym:
            for i, m in enumerate(MEME_VAULT):
                c_tag = m[3] if len(m) > 3 else "DOGE"
                if c_tag.upper() == req_sym.upper():
                    matched_indices.append(i)

        if matched_indices:
            idx = random.choice(matched_indices)
        else:
            idx = _get_next_index(chat_id, len(MEME_VAULT), _recent_meme)

        meme_item = MEME_VAULT[idx]
        title, body, punchline = meme_item[0], meme_item[1], meme_item[2]
        coin_sym = req_sym if req_sym else (meme_item[3] if len(meme_item) > 3 else random.choice(["BTC", "ETH", "SOL", "GRAM", "LTC", "XMR", "XRP", "BNB", "TRX", "DOGE", "PEPE", "SHIB"]))

        image_buf = render_meme_card(title, body, punchline, coin_symbol=coin_sym)

        today_date = datetime.utcnow().strftime("%d/%m")
        clean_caption = (
            f"{E('meme')} <b>Daily Degen Lore · {today_date}</b>\n"
            f"via @{BOT_USERNAME}. Tap /meme or /top for more."
        )

        kb = InlineKeyboardMarkup([
            [custom_btn("Another Meme", callback_data="fun:meme", icon="meme")],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing")],
            [custom_btn("Top Rockets", callback_data="fun:wagmi", icon="ath")]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb, caption=clean_caption)
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
    elif data.startswith("fun:dyk"):
        parts = data.split(":")
        coin_arg = parts[2] if len(parts) > 2 else ""
        context.args = [coin_arg] if coin_arg else []
        await didyouknow_command(update, context)

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
            [custom_btn(f"{symbol} Chart", callback_data=f"stats_{symbol}", coin=symbol)],
            [custom_btn("Daily Thought", callback_data="fun:daily", icon="currencing")]
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
            [custom_btn("Cope ATL", callback_data="fun:satoshi", icon="gem")],
            [custom_btn(f"{symbol} ATH", callback_data=f"ath_{symbol}", icon="ath")]
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

# ─── 8. /didyouknow & /dyk <coin> ──────────────────────────────────────────────
_DYK_HISTORY: Dict[int, deque] = {}

DID_YOU_KNOW_FACTS: Dict[str, List[Tuple[str, str]]] = {
    "BTC": [
        ("The Legendary 10,000 BTC Pizza", "On May 22, 2010, Laszlo Hanyecz bought two pizzas for 10,000 Bitcoins. At peak prices, those two pizzas were worth over $900 million dollars!"),
        ("Satoshi's Genesis Block Message", "Embedded in Bitcoin's Genesis block is the headline: 'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks' — a permanent critique of fractional reserve banking."),
        ("The Lost Million Bitcoins", "Satoshi Nakamoto is estimated to own over 1.1 million Bitcoins across thousands of early blocks, none of which have moved since 2010."),
        ("The 21 Million Mathematical Limit", "Due to block reward halvings occurring every 210,000 blocks, the total supply of Bitcoin will never exceed 20,999,999.9769 BTC, expected around the year 2140.")
    ],
    "ETH": [
        ("Vitalik's World of Warcraft Origin", "Vitalik Buterin created Ethereum after Blizzard nerfed his beloved World of Warcraft character. He realized the horrors of centralized services and set out to build decentralized applications."),
        ("The Merge Cut Energy by 99.95%", "In September 2022, Ethereum transitioned from Proof-of-Work to Proof-of-Stake in 'The Merge', slashing its worldwide electricity consumption by more than 99.95% overnight."),
        ("The First ICO & The DAO Hack", "Ethereum raised 31,500 BTC in 2014 during its crowd sale. In 2016, the $60M DAO hack forced a controversial hard fork that split Ethereum into ETH and Ethereum Classic (ETC)."),
        ("Smart Contracts Pioneer", "Nick Szabo conceived smart contracts in 1994, but Ethereum was the first Turing-complete blockchain that brought automated programmable agreements into global reality.")
    ],
    "SOL": [
        ("Proof of History Breakthrough", "Solana was conceptualized by Anatoly Yakovenko while drinking coffee and beer. He realized time could be verified cryptographically through recursive SHA-256 hashing, solving the clock synchronization problem."),
        ("Named After Solana Beach", "Solana was named after Solana Beach, a small coastal town in San Diego County where founders Anatoly, Greg, and Stephen lived and surfed while working at Qualcomm."),
        ("Sub-Second Finality", "Solana processes blocks every 400 milliseconds, allowing decentralized applications to achieve the responsiveness and execution speed of traditional Web2 infrastructure."),
        ("Tower BFT Consensus", "Solana utilizes Tower BFT, a PBFT-like consensus algorithm designed specifically to take advantage of the synchronized clock provided by Proof of History.")
    ],
    "GRAM": [
        ("The Telegram Gram Resurgence", "Telegram raised $1.7 billion for the original Gram ICO in 2018. When SEC halted it, open-source developers kept the code alive, which Telegram eventually officially embraced."),
        ("Infinite Sharding Architecture", "TON was designed by Nikolai Durov with dynamic sharding, allowing the network to split into split-chains and shard-chains to process millions of transactions per second."),
        ("Integrated Telegram Ecosystem", "With over 900 million active Telegram users, TON enables peer-to-peer crypto transfers, usernames, virtual phone numbers, and mini-apps directly inside chat."),
        ("World Record TPS Test", "In October 2023, TON officially set a world record by achieving 104,715 transactions per second in a stress test certified by CertiK.")
    ],
    "TON": [
        ("The Telegram Gram Resurgence", "Telegram raised $1.7 billion for the original Gram ICO in 2018. When SEC halted it, open-source developers kept the code alive, which Telegram eventually officially embraced."),
        ("Infinite Sharding Architecture", "TON was designed by Nikolai Durov with dynamic sharding, allowing the network to split into split-chains and shard-chains to process millions of transactions per second."),
        ("Integrated Telegram Ecosystem", "With over 900 million active Telegram users, TON enables peer-to-peer crypto transfers, usernames, virtual phone numbers, and mini-apps directly inside chat."),
        ("World Record TPS Test", "In October 2023, TON officially set a world record by achieving 104,715 transactions per second in a stress test certified by CertiK.")
    ],
    "DOGE": [
        ("Created in 3 Hours as a Joke", "Billy Markus and Jackson Palmer coded Dogecoin in roughly 3 hours in 2013 by forking Luckycoin and replacing the font with Comic Sans. It went on to reach an $80 billion market cap."),
        ("Funded the Jamaican Bobsled Team", "In 2014, the Dogecoin community raised over $30,000 worth of DOGE to send the Jamaican bobsled team to the Sochi Winter Olympics after they qualified but lacked funds."),
        ("DOGE-1 Space Mission", "Geometric Energy Corporation paid SpaceX entirely in Dogecoin to launch the DOGE-1 satellite to the Moon, marking the first commercial lunar payload paid entirely in cryptocurrency.")
    ],
    "XMR": [
        ("The Ultimate Untraceable Fungibility", "Monero utilizes Ring Signatures, Stealth Addresses, and RingCT so that neither the sender, receiver, nor transaction amount is ever visible on the public blockchain."),
        ("Fungibility Without Tainted Coins", "Unlike transparent blockchains where coins can be blacklisted or 'tainted' by previous transactions, every Monero unit is completely fungible and identical to every other."),
        ("Tail Emission Guarantee", "Monero has a perpetual 'tail emission' of 0.6 XMR per 2-minute block, ensuring miners are perpetually incentivized to secure the network even after all primary coins are mined.")
    ],
    "LTC": [
        ("The Silver to Bitcoin's Gold", "Charlie Lee created Litecoin in 2011 with 2.5-minute blocks and Scrypt proof-of-work, making it one of the longest continuously running operational blockchains in history."),
        ("The Testbed for SegWit & Lightning", "Litecoin activated Segregated Witness (SegWit) and completed the first cross-chain atomic swap with Bitcoin months before Bitcoin itself adopted the technology."),
        ("Zero Downtime Record", "Litecoin has operated continuously since October 2011 with 100% network uptime, maintaining unbroken reliability across multiple bear and bull cycles.")
    ],
    "BNB": [
        ("From ICO to Ecosystem Juggernaut", "Binance founder CZ sold his Shanghai apartment in 2014 to go all-in on Bitcoin, later launching BNB via an ICO raising $15M at $0.15 per token."),
        ("The Quarterly Auto-Burn Protocol", "Binance uses an automated formula based on BNB price and blocks produced to burn tokens quarterly, permanently removing supply until 100 million BNB remain."),
        ("From ERC-20 to Layer 1", "BNB initially launched as an ERC-20 token on Ethereum before migrating to its own sovereign high-throughput network powering the BNB Chain ecosystem.")
    ],
    "XRP": [
        ("Pre-Dating Bitcoin Concepts", "The conceptual roots of RipplePay date back to 2004 by Ryan Fugger, years before Satoshi published the Bitcoin whitepaper in late 2008."),
        ("Consensus Without Mining", "XRP uses the Ripple Protocol Consensus Algorithm (RPCA) rather than proof-of-work, enabling transactions to settle in 3 to 5 seconds with negligible energy use."),
        ("The Landmark SEC Legal Ruling", "In July 2023, a US Federal District Court ruled that programmatic sales of XRP on secondary exchanges do not constitute investment contracts, marking a historic crypto legal victory.")
    ],
    "TRX": [
        ("High Volume Stablecoin Highway", "TRON currently settles more USDT (Tether) daily transaction volume than the Ethereum network, making it the highest volume stablecoin settlement layer in the world."),
        ("Acquisition of BitTorrent", "In 2018, Tron founder Justin Sun acquired BitTorrent for $140 million, integrating the world's largest peer-to-peer file-sharing protocol with blockchain incentives."),
        ("Delegated Proof of Stake", "Tron uses 27 Super Representatives (SRs) elected by TRX holders every 6 hours to produce blocks and validate transactions at 2,000 TPS.")
    ],
    "LINK": [
        ("The Universal Decentralized Oracle", "Chainlink was pioneered by Sergey Nazarov in 2017 to solve the 'Oracle Problem' — securely bridging smart contracts with real-world off-chain data and APIs."),
        ("Securing Hundreds of Billions", "Chainlink Price Feeds secure over $20 billion in Total Value Locked across DeFi protocols including Aave, Compound, Synthetix, and major enterprise banking pilots."),
        ("CCIP Cross-Chain Standard", "Chainlink Cross-Chain Interoperability Protocol (CCIP) connects traditional banking giants like Swift, DTCC, and Euroclear to public and private blockchains.")
    ],
    "NEAR": [
        ("Nightshade Dynamic Sharding", "NEAR Protocol uses Nightshade sharding, which splits blocks across multiple parallel shards to achieve virtually unlimited throughput and sub-second finality."),
        ("Human-Readable Named Accounts", "Unlike complex hex addresses, NEAR accounts are human-readable by default (e.g., 'alice.near'), enabling seamless onboarding and account abstraction."),
        ("AI Pioneers Turned Blockchain Founders", "NEAR co-founder Illia Polosukhin was one of the 8 authors of Google's seminal 2017 paper 'Attention Is All You Need', which invented the Transformer AI architecture!")
    ],
    "SUI": [
        ("Object-Centric Move Language", "Sui was built by Mysten Labs (former Meta Diem engineers) using an object-centric data model, allowing parallel transaction execution without global state locks."),
        ("Sub-Second Finality via Mysticeti", "Sui utilizes Mysticeti consensus to finalize transactions in under 400 milliseconds, among the lowest latency of any production blockchain."),
        ("Dynamic & Upgradable NFTs", "On Sui, assets and NFTs can evolve, change metadata, and own other assets directly on-chain, unlocking next-generation Web3 gaming economies.")
    ],
    "APT": [
        ("Born from Meta's Diem Project", "Aptos was founded by former Meta engineers Mo Shaikh and Avery Ching, leveraging years of research on the Move programming language and Diem blockchain."),
        ("Block-STM Parallel Execution", "Aptos utilizes Block-STM (Software Transactional Memory) to execute transactions in parallel without requiring developers to declare dependencies upfront."),
        ("AptosBFT State Synchronization", "Aptos uses an advanced BFT consensus that separates transaction consensus from execution, achieving rapid confirmation times and low fees.")
    ],
    "DOT": [
        ("Created by Ethereum Co-Founder", "Polkadot was founded by Dr. Gavin Wood, who co-founded Ethereum, wrote the Ethereum Yellow Paper, and invented the Solidity smart contract language."),
        ("Heterogeneous Multi-Chain Framework", "Polkadot connects specialized sovereign parachains to a shared Relay Chain, providing pooled security and trustless cross-consensus messaging (XCM)."),
        ("Forkless On-Chain Upgrades", "Polkadot can upgrade its entire codebase on-chain through WebAssembly meta-protocols without requiring contentious hard forks or chain splits.")
    ],
    "ICP": [
        ("The Internet Computer Vision", "Created by Dominic Williams and the DFINITY Foundation, ICP runs software containers directly on the web at web speed, eliminating cloud infrastructure like AWS."),
        ("Chain Key Cryptography", "ICP uses Chain Key Cryptography with a single 48-byte public key to coordinate thousands of independent subnet nodes and sign transactions on Bitcoin and Ethereum."),
        ("Reverse Gas Model", "On ICP, developers pay the 'cycles' (gas) required to run canister smart contracts, meaning end users can browse and interact with Web3 apps completely free of fees.")
    ],
    "UNI": [
        ("Created by a Laid-Off Engineer", "Hayden Adams built Uniswap in 2018 after being laid off from Siemens. Encouraged by a tweet from Vitalik Buterin, he taught himself Ethereum development from scratch."),
        ("The Automated Market Maker Revolution", "Uniswap pioneered the Constant Product Formula (x * y = k), replacing traditional order books with liquidity pools and igniting the 2020 DeFi Summer."),
        ("The Surprise $1,200 UNI Airdrop", "In September 2020, Uniswap airdropped 400 UNI tokens to every single historical user. At all-time highs, that gift was worth over $18,000 per wallet.")
    ],
    "BCH": [
        ("The Blocksize War of 2017", "Bitcoin Cash originated from an ideological hard fork in August 2017 over block size limits, with BCH proponents advocating 8MB (now 32MB) blocks for cheap peer-to-peer cash."),
        ("Sub-Cent Global Transactions", "By scaling on-chain block capacity, Bitcoin Cash transactions reliably cost fractions of a cent, making microtransactions and retail point-of-sale payments practical."),
        ("SmartBCH & CashTokens", "Bitcoin Cash supports CashTokens, enabling native tokens, decentralized applications, and smart contracts directly on the UTXO model.")
    ],
    "XLM": [
        ("Founded by Mt. Gox & Ripple Creator", "Jed McCaleb co-founded Stellar in 2014 after previously creating eDonkey2000, Mt. Gox, and Ripple, focusing on non-profit financial inclusion."),
        ("Stellar Consensus Protocol (SCP)", "Designed by Stanford Professor David Mazières, SCP uses Federated Byzantine Agreement (FBA) to achieve 3-5 second settlement with zero energy waste."),
        ("Powering Global Remittances", "MoneyGram and international NGOs use Stellar to disburse cross-border aid and remittances directly to digital wallets and physical cash pickup locations.")
    ],
    "PEPE": [
        ("The Meme That Shook 2023", "Pepe token reached a $1 billion market cap in just 20 days without any pre-sale, zero taxes, and LP burnt — one of the fastest meme runs in crypto history."),
        ("Matt Furie's Iconic Character", "Pepe the Frog was created by artist Matt Furie in 2005 in his 'Boy's Club' comic before evolving into the universal symbol of internet and crypto culture."),
        ("Fair Launch Ethos", "Pepe launched stealthily with no VC backing or roadmap, relying entirely on viral community memetics and pure decentralized culture.")
    ],
    "SHIB": [
        ("The $1 Billion Covid Relief Gift", "In May 2021, Vitalik Buterin donated 50 trillion SHIB tokens (worth over $1 billion) to Sandeep Nailwal's India Crypto Covid Relief Fund, the largest crypto philanthropic donation in history."),
        ("Burning Half the Supply to Vitalik", "Ryoshi, the pseudonymous creator of Shiba Inu, sent 50% of the total SHIB supply to Vitalik Buterin's public wallet, believing he would never sell or dump them."),
        ("From Meme to Layer 2 Shibarium", "Shiba Inu evolved from a simple ERC-20 token into a full ecosystem with decentralized exchange ShibaSwap, Metaverse land, and its own Shibarium Layer-2 network.")
    ],
    "ADA": [
        ("Named After First Programmer", "Cardano was named after Ada Lovelace, the 19th-century mathematician recognized as the world's first computer programmer."),
        ("Peer-Reviewed Scientific Philosophy", "Cardano is built upon peer-reviewed academic research, developed with the formal verification language Haskell and the Ouroboros Proof-of-Stake protocol."),
        ("Byron to Voltaire Roadmap", "Cardano's roadmap is divided into five poetic eras: Byron (foundation), Shelley (decentralization), Goguen (smart contracts), Basho (scaling), and Voltaire (governance).")
    ],
    "AVAX": [
        ("The Snow Family Consensus", "Avalanche's consensus was proposed anonymously by 'Team Rocket' using sub-sampled voting inspired by epidemic gossip algorithms."),
        ("Three-Chain Architecture", "Avalanche divides network responsibilities across three built-in blockchains: the X-Chain (assets), P-Chain (platform/validators), and C-Chain (EVM smart contracts)."),
        ("Custom Subnet Ecosystem", "Avalanche enables institutions and game studios to spin up sovereign, compliant subnets with custom gas tokens and validator rules while retaining Avalanche security.")
    ],
    "MATIC": [
        ("Born in Mumbai, Scaling Worldwide", "Polygon (formerly Matic Network) was founded in Mumbai in 2017 by Jaynti Kanani, Sandeep Nailwal, and Anurag Arjun to solve Ethereum's scalability bottleneck."),
        ("AggLayer & Zero-Knowledge Evolution", "Polygon has invested over $1 billion in Zero-Knowledge (ZK) technology, creating Polygon zkEVM and the AggLayer to unify fragmented blockchain liquidity."),
        ("Powering Global Brand Web3 Pilots", "Global giants including Starbucks, Nike, Reddit, and Disney selected Polygon for their digital loyalty and NFT collectibles initiatives.")
    ],
    "POL": [
        ("Born in Mumbai, Scaling Worldwide", "Polygon (formerly Matic Network) was founded in Mumbai in 2017 by Jaynti Kanani, Sandeep Nailwal, and Anurag Arjun to solve Ethereum's scalability bottleneck."),
        ("AggLayer & Zero-Knowledge Evolution", "Polygon has invested over $1 billion in Zero-Knowledge (ZK) technology, creating Polygon zkEVM and the AggLayer to unify fragmented blockchain liquidity."),
        ("Powering Global Brand Web3 Pilots", "Global giants including Starbucks, Nike, Reddit, and Disney selected Polygon for their digital loyalty and NFT collectibles initiatives.")
    ]
}

async def didyouknow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send /didyouknow & /dyk crypto history & lore card."""
    if not await check_user_authorization(update, context):
        return

    chat_id = update.effective_chat.id
    reply_msg_id = update.effective_message.message_id if update.effective_message else None

    args = context.args or []
    if args:
        raw_sym = args[0]
        resolved = resolve_coin(raw_sym)
        symbol = resolved or raw_sym.upper()
    else:
        # Default to a random coin so /dyk works out of the box
        symbol = random.choice(["BTC", "ETH", "SOL", "GRAM", "DOGE", "TON", "LINK", "XRP"])

    # Lookup handling: ensure TON and GRAM both resolve to available facts
    lookup_sym = symbol.upper()
    if lookup_sym in ("TON", "TONCOIN"):
        lookup_sym = "TON" if "TON" in DID_YOU_KNOW_FACTS else "GRAM"

    facts = DID_YOU_KNOW_FACTS.get(lookup_sym)
    if not facts:
        # Fallback to GRAM if TON-related, else BTC
        if lookup_sym in ("TON", "GRAM", "THE-OPEN-NETWORK"):
            facts = DID_YOU_KNOW_FACTS.get("GRAM", DID_YOU_KNOW_FACTS["BTC"])
        else:
            facts = DID_YOU_KNOW_FACTS.get("BTC")

    # Anti-repetition selection per chat + coin
    hist_key = abs(hash(f"{chat_id}_{lookup_sym}")) % 100000
    idx = _get_next_index(hist_key, len(facts), _DYK_HISTORY)
    title, body = facts[idx]

    # For display symbol: respect what the user asked (e.g. TON vs GRAM)
    display_sym = "TON" if (args and args[0].upper() in ("TON", "TONCOIN")) else symbol

    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        image_buf = render_didyouknow_card(display_sym, title, body)
        kb = InlineKeyboardMarkup([
            [custom_btn("Another Trivia", callback_data=f"fun:dyk:{display_sym}", icon="help")],
            [custom_btn(f"{display_sym} Chart", callback_data=f"stats_{display_sym}", coin=display_sym)]
        ])
        await _send_fun_card(context, chat_id, image_buf, reply_msg_id, kb)
    except Exception as e:
        logger.error("Error in /didyouknow: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{E('cross')} Failed to generate Trivia card for {display_sym}.",
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
