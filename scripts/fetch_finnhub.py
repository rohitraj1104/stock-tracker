"""
fetch_finnhub.py
Uses Finnhub free API to enrich stocks with:
  - Current price
  - Analyst consensus (buy/hold/sell counts)
  - Price target (mean, high, low)

Free API key from https://finnhub.io — no credit card needed.
Set the key as a GitHub Secret called FINNHUB_API_KEY.
"""

import os
import requests
import time

FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
BASE_URL = "https://finnhub.io/api/v1"

HEADERS = {"X-Finnhub-Token": FINNHUB_KEY}


def get_price_target(ticker: str) -> dict:
    """Fetch analyst price target summary for a ticker."""
    if not FINNHUB_KEY:
        return {}
    try:
        url = f"{BASE_URL}/stock/price-target"
        resp = requests.get(url, params={"symbol": ticker}, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        return {
            "finnhub_target_mean":  data.get("targetMean", ""),
            "finnhub_target_high":  data.get("targetHigh", ""),
            "finnhub_target_low":   data.get("targetLow", ""),
            "finnhub_analyst_count": data.get("targetNumberOfAnalysts", ""),
        }
    except Exception as e:
        print(f"[Finnhub] Price target error for {ticker}: {e}")
        return {}


def get_recommendation_trend(ticker: str) -> dict:
    """Fetch buy/hold/sell counts from Finnhub."""
    if not FINNHUB_KEY:
        return {}
    try:
        url = f"{BASE_URL}/stock/recommendation"
        resp = requests.get(url, params={"symbol": ticker}, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        if not data:
            return {}
        # Most recent period is first
        latest = data[0]
        return {
            "consensus_strong_buy": latest.get("strongBuy", 0),
            "consensus_buy":        latest.get("buy", 0),
            "consensus_hold":       latest.get("hold", 0),
            "consensus_sell":       latest.get("sell", 0),
            "consensus_period":     latest.get("period", ""),
        }
    except Exception as e:
        print(f"[Finnhub] Recommendation error for {ticker}: {e}")
        return {}


def get_current_price(ticker: str) -> str:
    """Fetch latest stock price from Finnhub."""
    if not FINNHUB_KEY:
        return ""
    try:
        url = f"{BASE_URL}/quote"
        resp = requests.get(url, params={"symbol": ticker}, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        price = data.get("c", "")  # 'c' = current price
        return f"${price:.2f}" if price else ""
    except Exception as e:
        print(f"[Finnhub] Quote error for {ticker}: {e}")
        return ""


def enrich_with_finnhub(rows: list) -> list:
    """
    Takes a list of stock dicts and adds Finnhub data.
    Respects Finnhub free tier rate limit: 60 calls/minute.
    We make 3 calls per ticker so process max 20 tickers/min safely.
    """
    if not FINNHUB_KEY:
        print("[Finnhub] No API key set — skipping enrichment. "
              "Add FINNHUB_API_KEY as a GitHub Secret to enable.")
        return rows

    seen_tickers = {}
    enriched = []

    for row in rows:
        ticker = row.get("ticker", "")

        if ticker not in seen_tickers:
            print(f"[Finnhub] Enriching {ticker}...")
            pt     = get_price_target(ticker)
            trend  = get_recommendation_trend(ticker)
            price  = get_current_price(ticker)

            seen_tickers[ticker] = {
                "current_price": price,
                **pt,
                **trend,
            }
            time.sleep(1.1)  # stay under 60 req/min

        row.update(seen_tickers[ticker])
        enriched.append(row)

    return enriched


if __name__ == "__main__":
    # Quick test
    test = [{"ticker": "AAPL"}, {"ticker": "NVDA"}]
    result = enrich_with_finnhub(test)
    for r in result:
        print(r)
