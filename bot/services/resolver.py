"""
Coin alias resolver — maps full names, alternate tickers and common aliases
to the canonical symbol used in the COINS dict.
"""

COIN_ALIASES = {
    # Bitcoin
    "btc": "BTC", "bitcoin": "BTC",
    # Ethereum
    "eth": "ETH", "ethereum": "ETH", "ether": "ETH",
    # Solana
    "sol": "SOL", "solana": "SOL",
    # BNB
    "bnb": "BNB", "binance": "BNB", "binancecoin": "BNB",
    # XRP
    "xrp": "XRP", "ripple": "XRP",
    # Dogecoin
    "doge": "DOGE", "dogecoin": "DOGE",
    # Cardano
    "ada": "ADA", "cardano": "ADA",
    # Avalanche
    "avax": "AVAX", "avalanche": "AVAX", "avalanche-2": "AVAX",
    # Gram / TON
    "gram": "GRAM", "ton": "GRAM", "toncoin": "GRAM",
    "the-open-network": "GRAM", "opennetwork": "GRAM",
    # Tron
    "trx": "TRX", "tron": "TRX",
    # Litecoin
    "ltc": "LTC", "litecoin": "LTC",
    # Monero
    "xmr": "XMR", "monero": "XMR",
    # Shiba Inu
    "shib": "SHIB", "shibainu": "SHIB", "shiba": "SHIB",
    # Pepe
    "pepe": "PEPE", "pepecoin": "PEPE",
}


def resolve_coin(raw: str) -> str | None:
    """
    Resolve a user-supplied string to a canonical coin symbol.
    Returns None if unrecognised.
    """
    if not raw:
        return None
    cleaned = raw.lower().strip().replace(" ", "").replace("-", "").replace("_", "")
    if cleaned in COIN_ALIASES:
        return COIN_ALIASES[cleaned]
    # Check original lower string
    return COIN_ALIASES.get(raw.lower().strip())
