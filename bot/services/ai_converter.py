import os
import re
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
import aiohttp

from bot.config import GEMINI_API_KEY
from bot.graphics.assets import COINS, FIAT_CURRENCIES
from bot.services.resolver import resolve_coin
from bot.services.crypto_api import crypto_service

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Standard synonyms
SLANG_MAP = {
    "bucks": "USD",
    "buck": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "euro": "EUR",
    "euros": "EUR",
    "pound": "GBP",
    "pounds": "GBP",
    "yen": "JPY",
    "rupee": "INR",
    "rupees": "INR",
    "ruble": "RUB",
    "rubles": "RUB",
    "ton": "GRAM",
    "solana": "SOL",
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "ether": "ETH",
    "dogecoin": "DOGE",
    "shiba": "SHIB",
}

def _clean_token(t: str) -> str:
    return t.strip().lower().strip(".,;:?!'\"()[]{}")

def parse_conversion_query_local(query: str) -> Optional[Dict[str, Any]]:
    """
    Ultra-fast, deterministic natural language parser for crypto conversions.
    Handles:
      - '$100 eth', '100$ in sol', '50 bucks to btc'
      - '0.5 btc', '0.5 btc eur', '0.5 btc to usd'
      - '100 usd in btc', '500 eur to sol'
      - 'convert 2 eth to usd'
    """
    raw = query.strip()
    if not raw:
        return None

    # Remove words like "convert", "calculate", "how much is", "in", "to", "into"
    tokens = [t for t in re.split(r"\s+", raw) if t]
    filtered_tokens = []
    for t in tokens:
        cl = _clean_token(t)
        if cl in ["convert", "how", "much", "is", "worth", "of", "into", "to", "in"]:
            continue
        filtered_tokens.append(t)

    # 1. Check for leading/trailing $ or € or £ sign: e.g. '$100 eth' or '100$ eth'
    m_dollar = re.search(r"([$€£¥₹₽])\s*([\d,.]+)", raw) or re.search(r"([\d,.]+)\s*([$€£¥₹₽])", raw)
    if m_dollar:
        symbol_char = m_dollar.group(1) if m_dollar.group(1) in "$€£¥₹₽" else m_dollar.group(2)
        amt_str = m_dollar.group(2) if m_dollar.group(1) in "$€£¥₹₽" else m_dollar.group(1)
        fiat_map = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "₽": "RUB"}
        fiat = fiat_map.get(symbol_char, "USD")
        try:
            amount = float(amt_str.replace(",", ""))
            # Search for crypto in the remaining text
            remaining = raw.replace(m_dollar.group(0), "")
            for word in re.findall(r"[A-Za-z]+", remaining):
                w_norm = SLANG_MAP.get(word.lower(), word.upper())
                c = resolve_coin(w_norm) or (w_norm if w_norm in COINS else None)
                if c:
                    return {"amount": amount, "from_currency": fiat, "to_currency": c}
        except Exception:
            pass

    # 2. General token scan: look for amount + from + to
    amount: Optional[float] = None
    from_curr: Optional[str] = None
    to_curr: Optional[str] = None

    # Find number
    for t in filtered_tokens:
        clean = re.sub(r"[^\d.]", "", t)
        if clean and amount is None:
            try:
                amount = float(clean)
                continue
            except ValueError:
                pass

        # Check currency / crypto token
        cl = _clean_token(t)
        norm = SLANG_MAP.get(cl, cl.upper())
        c_coin = resolve_coin(norm) or (norm if norm in COINS else None)
        if c_coin:
            if from_curr is None:
                from_curr = c_coin
            elif to_curr is None:
                to_curr = c_coin
            continue

        if norm in FIAT_CURRENCIES:
            if from_curr is None:
                from_curr = norm
            elif to_curr is None:
                to_curr = norm
            continue

    if amount is None:
        amount = 1.0

    if from_curr and not to_curr:
        if from_curr in FIAT_CURRENCIES:
            to_curr = "BTC"
        else:
            to_curr = "USD"
    elif not from_curr and to_curr:
        from_curr = "USD" if to_curr in COINS else "BTC"

    if from_curr and to_curr:
        return {"amount": amount, "from_currency": from_curr, "to_currency": to_curr}

    return None

async def parse_conversion_query_gemini(query: str) -> Optional[Dict[str, Any]]:
    """Use Gemini AI API to parse natural language conversion queries."""
    if not GEMINI_API_KEY:
        return None

    prompt = (
        "Extract currency conversion details from this query into JSON only.\n"
        "Return format:\n"
        "{\"amount\": float, \"from_currency\": \"SYMBOL\", \"to_currency\": \"SYMBOL\"}\n"
        "Normalize names to standard symbols like BTC, ETH, SOL, USD, EUR, GBP, DOGE, GRAM, etc.\n"
        f"Query: \"{query}\""
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
    }

    try:
        timeout = aiohttp.ClientTimeout(total=2.5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        # Extract JSON object from output
                        m = re.search(r"\{[^}]+\}", text)
                        if m:
                            parsed = json.loads(m.group(0))
                            amt = float(parsed.get("amount", 1.0))
                            f_c = parsed.get("from_currency", "").upper().strip()
                            t_c = parsed.get("to_currency", "").upper().strip()
                            if f_c and t_c:
                                return {"amount": amt, "from_currency": f_c, "to_currency": t_c}
    except Exception as e:
        logger.debug("Gemini AI conversion parser fallback: %s", e)

    return None

async def parse_conversion_query(query: str) -> Dict[str, Any]:
    """Parse conversion query using Gemini AI with fallback to local NLP parser."""
    # Try Gemini first if key available
    if GEMINI_API_KEY:
        try:
            ai_res = await parse_conversion_query_gemini(query)
            if ai_res:
                return ai_res
        except Exception:
            pass

    # Fast deterministic local fallback
    local_res = parse_conversion_query_local(query)
    if local_res:
        return local_res

    # Default fallback
    return {"amount": 1.0, "from_currency": "BTC", "to_currency": "USD"}

async def execute_conversion(query: str) -> Dict[str, Any]:
    """
    Execute conversion end-to-end:
    - Parses natural user intent via Gemini AI / smart parser
    - Fetches live rates
    - Calculates conversion & exchange rates
    - Returns structured metadata ready for rendering and response
    """
    parsed = await parse_conversion_query(query)
    amount = float(parsed["amount"])
    from_c = parsed["from_currency"].upper()
    to_c = parsed["to_currency"].upper()

    # Determine which is crypto and which is fiat
    is_from_crypto = from_c in COINS
    is_to_crypto = to_c in COINS
    is_from_fiat = from_c in FIAT_CURRENCIES
    is_to_fiat = to_c in FIAT_CURRENCIES

    # Case 1: Crypto to Fiat (e.g. 0.5 BTC -> USD)
    if is_from_crypto and (is_to_fiat or not is_to_crypto):
        crypto_symbol = from_c
        fiat_symbol = to_c if is_to_fiat else "USD"
        coin_data = await crypto_service.get_coin_data(crypto_symbol)
        usd_price = coin_data["current_price"]
        fiat_rate = crypto_service.get_fiat_rate(fiat_symbol)
        unit_price = usd_price * fiat_rate
        fiat_value = amount * unit_price

        return {
            "crypto_symbol": crypto_symbol,
            "crypto_amount": amount,
            "fiat_symbol": fiat_symbol,
            "fiat_value": fiat_value,
            "reverse": False,
            "unit_price": unit_price,
            "summary": f"{amount:,.4g} {crypto_symbol} = {fiat_value:,.2f} {fiat_symbol}"
        }

    # Case 2: Fiat to Crypto (e.g. $100 USD -> BTC)
    elif is_from_fiat and is_to_crypto:
        crypto_symbol = to_c
        fiat_symbol = from_c
        coin_data = await crypto_service.get_coin_data(crypto_symbol)
        usd_price = coin_data["current_price"]
        fiat_rate = crypto_service.get_fiat_rate(fiat_symbol)
        unit_price = usd_price * fiat_rate
        crypto_amount = amount / unit_price if unit_price > 0 else 0.0

        return {
            "crypto_symbol": crypto_symbol,
            "crypto_amount": crypto_amount,
            "fiat_symbol": fiat_symbol,
            "fiat_value": amount,
            "reverse": True,
            "unit_price": unit_price,
            "summary": f"{amount:,.2f} {fiat_symbol} = {crypto_amount:,.4g} {crypto_symbol}"
        }

    # Case 3: Crypto to Crypto (e.g. 1 BTC -> ETH)
    elif is_from_crypto and is_to_crypto:
        c1_data = await crypto_service.get_coin_data(from_c)
        c2_data = await crypto_service.get_coin_data(to_c)
        p1 = c1_data["current_price"]
        p2 = c2_data["current_price"]
        val_usd = amount * p1
        target_amount = val_usd / p2 if p2 > 0 else 0.0

        return {
            "crypto_symbol": from_c,
            "crypto_amount": amount,
            "fiat_symbol": to_c,
            "fiat_value": target_amount,
            "reverse": False,
            "unit_price": p1 / p2 if p2 > 0 else 0.0,
            "summary": f"{amount:,.4g} {from_c} = {target_amount:,.4g} {to_c}"
        }

    # Fallback: Default to BTC -> USD
    coin_data = await crypto_service.get_coin_data("BTC")
    p = coin_data["current_price"]
    return {
        "crypto_symbol": "BTC",
        "crypto_amount": amount,
        "fiat_symbol": "USD",
        "fiat_value": amount * p,
        "reverse": False,
        "unit_price": p,
        "summary": f"{amount:,.4g} BTC = {amount * p:,.2f} USD"
    }
