import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
import aiohttp
from bot.config import COINGECKO_API_BASE, CACHE_TTL_SECONDS
from bot.graphics.assets import COINS, FIAT_CURRENCIES

logger = logging.getLogger(__name__)

# Fallback baseline data in case API is temporarily unreachable on cold start
INITIAL_FALLBACK = {
    "BTC": {
        "id": "bitcoin", "symbol": "BTC", "name": "Bitcoin",
        "current_price": 74820.63, "change_24h": -1.36, "change_7d": -3.67,
        "ath": 126080.0, "ath_date": "2025-10-06T10:57:42.000Z",
        "sparkline": [74820.63 + i * 2 for i in range(168)]
    },
    "ETH": {
        "id": "ethereum", "symbol": "ETH", "name": "Ethereum",
        "current_price": 2124.17, "change_24h": -4.98, "change_7d": -6.96,
        "ath": 4946.05, "ath_date": "2025-08-24T11:21:03.000Z",
        "sparkline": [2124.17 - i * 1.5 for i in range(168)]
    },
    "SOL": {
        "id": "solana", "symbol": "SOL", "name": "Solana",
        "current_price": 86.79, "change_24h": -2.91, "change_7d": -7.86,
        "ath": 259.96, "ath_date": "2021-11-06T21:54:35.825Z",
        "sparkline": [86.79 for _ in range(168)]
    },
    "GRAM": {
        "id": "the-open-network", "symbol": "GRAM", "name": "Gram",
        "current_price": 1.05, "change_24h": -1.10, "change_7d": -12.18,
        "ath": 8.25, "ath_date": "2024-06-15T00:00:00.000Z",
        "sparkline": [1.05 for _ in range(168)]
    },
    "LTC": {
        "id": "litecoin", "symbol": "LTC", "name": "Litecoin",
        "current_price": 51.44, "change_24h": -0.76, "change_7d": -6.09,
        "ath": 410.26, "ath_date": "2021-05-10T03:13:07.904Z",
        "sparkline": [51.44 for _ in range(168)]
    },
    "XMR": {
        "id": "monero", "symbol": "XMR", "name": "Monero",
        "current_price": 599.51, "change_24h": -0.20, "change_7d": -1.58,
        "ath": 542.33, "ath_date": "2021-05-09T07:44:09.309Z",
        "sparkline": [599.51 for _ in range(168)]
    },
    "XRP": {
        "id": "ripple", "symbol": "XRP", "name": "XRP",
        "current_price": 1.11, "change_24h": -4.68, "change_7d": -11.59,
        "ath": 3.84, "ath_date": "2018-01-04T00:00:00.000Z",
        "sparkline": [1.11 for _ in range(168)]
    },
    "BNB": {
        "id": "binancecoin", "symbol": "BNB", "name": "BNB",
        "current_price": 686.71, "change_24h": -1.58, "change_7d": -2.50,
        "ath": 1369.99, "ath_date": "2025-10-13T00:41:24.000Z",
        "sparkline": [686.71 for _ in range(168)]
    },
    "TRX": {
        "id": "tron", "symbol": "TRX", "name": "Tron",
        "current_price": 0.3174, "change_24h": -0.87, "change_7d": 0.39,
        "ath": 0.44, "ath_date": "2024-12-04T00:00:00.000Z",
        "sparkline": [0.3174 for _ in range(168)]
    },
    "DOGE": {
        "id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin",
        "current_price": 0.254, "change_24h": 1.25, "change_7d": 8.40,
        "ath": 0.7376, "ath_date": "2021-05-08T05:08:48.000Z",
        "sparkline": [0.254 for _ in range(168)]
    },
    "ADA": {
        "id": "cardano", "symbol": "ADA", "name": "Cardano",
        "current_price": 0.742, "change_24h": -1.15, "change_7d": 4.10,
        "ath": 3.10, "ath_date": "2021-09-02T06:00:10.000Z",
        "sparkline": [0.742 for _ in range(168)]
    },
    "AVAX": {
        "id": "avalanche-2", "symbol": "AVAX", "name": "Avalanche",
        "current_price": 32.50, "change_24h": 2.10, "change_7d": 6.80,
        "ath": 146.22, "ath_date": "2021-11-21T13:48:00.000Z",
        "sparkline": [32.50 for _ in range(168)]
    },
    "SHIB": {
        "id": "shiba-inu", "symbol": "SHIB", "name": "Shiba Inu",
        "current_price": 0.0000185, "change_24h": 1.80, "change_7d": 5.60,
        "ath": 0.00008845, "ath_date": "2021-10-28T11:00:00.000Z",
        "sparkline": [0.0000185 for _ in range(168)]
    },
    "PEPE": {
        "id": "pepe", "symbol": "PEPE", "name": "Pepe",
        "current_price": 0.0000105, "change_24h": 3.40, "change_7d": 12.80,
        "ath": 0.00002524, "ath_date": "2024-11-14T02:00:00.000Z",
        "sparkline": [0.0000105 for _ in range(168)]
    }
}

class CryptoApiService:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = dict(INITIAL_FALLBACK)
        self._last_fetch_time: float = 0
        self._fiat_rates: Dict[str, float] = {
            "USD": 1.0,
            "EUR": 0.89,
            "GBP": 0.75,
            "JPY": 155.0,
            "CAD": 1.41,
            "AUD": 1.45,
            "CHF": 0.88,
            "CNY": 7.25,
            "INR": 86.5,
            "RUB": 97.0
        }
        self._rates_last_fetch: float = 0
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": "Currencing-CryptoBot/1.0"},
                timeout=timeout
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def refresh_market_data(self, force: bool = False) -> None:
        """Fetch fresh market data from CoinGecko with caching and error resilience."""
        now = time.time()
        if not force and (now - self._last_fetch_time < CACHE_TTL_SECONDS):
            return

        async with self._lock:
            # Double check inside lock
            if not force and (time.time() - self._last_fetch_time < CACHE_TTL_SECONDS):
                return

            coin_ids = [m["id"] for m in COINS.values()]
            ids_param = ",".join(coin_ids)
            url = (
                f"{COINGECKO_API_BASE}/coins/markets"
                f"?vs_currency=usd&ids={ids_param}"
                f"&sparkline=true&price_change_percentage=24h,7d"
            )

            try:
                session = await self._get_session()
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Map received data back by symbol
                        # Note: 'the-open-network' is mapped to GRAM in COINS
                        id_to_sym = {m["id"]: sym for sym, m in COINS.items()}

                        for item in data:
                            cid = item.get("id")
                            sym = id_to_sym.get(cid)
                            if not sym:
                                continue

                            sparkline_raw = item.get("sparkline_in_7d", {}).get("price", [])
                            # Ensure at least valid sparkline points
                            if not sparkline_raw:
                                sparkline_raw = self._cache.get(sym, {}).get("sparkline", [item.get("current_price", 0.0)] * 168)

                            self._cache[sym] = {
                                "id": cid,
                                "symbol": sym,
                                "name": COINS[sym]["name"],
                                "current_price": float(item.get("current_price") or 0.0),
                                "change_24h": float(item.get("price_change_percentage_24h_in_currency") or item.get("price_change_percentage_24h") or 0.0),
                                "change_7d": float(item.get("price_change_percentage_7d_in_currency") or 0.0),
                                "ath": float(item.get("ath") or 0.0),
                                "ath_date": item.get("ath_date") or "",
                                "sparkline": sparkline_raw
                            }

                        self._last_fetch_time = time.time()
                        logger.info("Successfully refreshed market data for %d coins", len(data))
                    elif resp.status == 429:
                        logger.warning("CoinGecko rate limit (429) hit. Serving from warm cache.")
                    else:
                        logger.warning("CoinGecko API returned status %d", resp.status)
            except Exception as e:
                logger.error("Failed to fetch CoinGecko market data: %s. Using cached data.", e)

            # Also refresh fiat rates periodically
            await self._refresh_fiat_rates()

    async def _refresh_fiat_rates(self) -> None:
        """Fetch fiat currency exchange rates."""
        now = time.time()
        if now - self._rates_last_fetch < 600:  # 10 minutes cache for fiat
            return

        url = f"{COINGECKO_API_BASE}/exchange_rates"
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rates = data.get("rates", {})
                    usd_val = rates.get("usd", {}).get("value")
                    if usd_val and usd_val > 0:
                        for fiat_code in FIAT_CURRENCIES.keys():
                            key = fiat_code.lower()
                            if key in rates:
                                fiat_btc_val = rates[key].get("value")
                                if fiat_btc_val:
                                    # Rate = Fiat / USD
                                    self._fiat_rates[fiat_code] = float(fiat_btc_val) / float(usd_val)
                        self._rates_last_fetch = time.time()
                        logger.info("Refreshed fiat exchange rates: %s", self._fiat_rates)
        except Exception as e:
            logger.debug("Failed to refresh fiat rates: %s", e)

    async def get_coin_data(self, symbol: str) -> Dict[str, Any]:
        """Get live or cached market data for an individual coin."""
        symbol = symbol.upper()
        await self.refresh_market_data()
        return self._cache.get(symbol, INITIAL_FALLBACK.get(symbol, {
            "symbol": symbol,
            "name": symbol,
            "current_price": 0.0,
            "change_24h": 0.0,
            "change_7d": 0.0,
            "ath": 0.0,
            "ath_date": "",
            "sparkline": [0.0] * 168
        }))

    async def get_all_overview_data(self) -> List[Dict[str, Any]]:
        """Get market overview for all 9 supported cryptocurrencies in standard order."""
        await self.refresh_market_data()
        ordered_syms = ["BTC", "ETH", "SOL", "GRAM", "LTC", "XMR", "XRP", "BNB", "TRX"]
        result = []
        for sym in ordered_syms:
            coin = self._cache.get(sym, INITIAL_FALLBACK.get(sym))
            if coin:
                result.append({
                    "symbol": sym,
                    "name": coin.get("name", sym),
                    "price": coin.get("current_price", 0.0),
                    "change_24h": coin.get("change_24h", 0.0)
                })
        return result

    async def convert(self, crypto_symbol: str, amount: float, fiat_symbol: str = "USD") -> Dict[str, Any]:
        """Convert a cryptocurrency amount to fiat currency."""
        crypto_symbol = crypto_symbol.upper()
        fiat_symbol = fiat_symbol.upper()

        coin_data = await self.get_coin_data(crypto_symbol)
        usd_price = coin_data.get("current_price", 0.0)
        total_usd = amount * usd_price

        fiat_rate = self._fiat_rates.get(fiat_symbol, 1.0)
        fiat_val = total_usd * fiat_rate

        return {
            "crypto_symbol": crypto_symbol,
            "crypto_amount": amount,
            "fiat_symbol": fiat_symbol,
            "fiat_value": fiat_val,
            "usd_price": usd_price,
            "fiat_rate": fiat_rate
        }

# Global singleton service
crypto_service = CryptoApiService()
