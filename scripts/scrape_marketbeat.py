"""
scrape_marketbeat.py
Scrapes analyst upgrades/initiations from MarketBeat for specific brokers.
Only keeps Overweight / Buy / Outperform / Strong Buy ratings.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import random

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_BROKERS = [
    "b. riley", "b riley",
    "oppenheimer",
    "jefferies",
    "goldman sachs",
    "morgan stanley",
    "jp morgan", "jpmorgan",
    "bank of america", "bofa",
    "wells fargo",
    "citigroup", "citi",
    "barclays",
    "ubs",
    "raymond james",
    "piper sandler",
]

BULLISH_RATINGS = [
    "overweight", "buy", "strong buy", "outperform",
    "market outperform", "positive", "conviction buy",
    "add", "accumulate"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Scrapers ──────────────────────────────────────────────────────────────────

def scrape_marketbeat_upgrades():
    """Scrape today's analyst upgrades from MarketBeat."""
    url = "https://www.marketbeat.com/ratings/analyst-upgrades/"
    results = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # MarketBeat renders a table with class 'table-responsive'
        table = soup.find("table")
        if not table:
            print("[MarketBeat] No table found on upgrades page.")
            return results

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            ticker   = cols[0].get_text(strip=True)
            company  = cols[1].get_text(strip=True)
            broker   = cols[2].get_text(strip=True)
            rating   = cols[3].get_text(strip=True)
            pt_text  = cols[4].get_text(strip=True) if len(cols) > 4 else ""

            # Filter by broker
            broker_lower = broker.lower()
            matched_broker = None
            for b in TARGET_BROKERS:
                if b in broker_lower:
                    matched_broker = broker
                    break
            if not matched_broker:
                continue

            # Filter by bullish rating
            rating_lower = rating.lower()
            if not any(r in rating_lower for r in BULLISH_RATINGS):
                continue

            # Parse price target
            price_target = ""
            for part in pt_text.replace("→", " ").split():
                part = part.replace("$", "").replace(",", "").strip()
                try:
                    float(part)
                    price_target = f"${part}"
                except ValueError:
                    pass

            results.append({
                "ticker":        ticker.upper(),
                "company":       company,
                "broker":        matched_broker,
                "rating":        rating,
                "price_target":  price_target,
                "date":          datetime.today().strftime("%Y-%m-%d"),
                "source":        url,
                "source_name":   "MarketBeat Upgrades",
            })

        print(f"[MarketBeat Upgrades] Found {len(results)} bullish calls from target brokers.")

    except Exception as e:
        print(f"[MarketBeat Upgrades] Error: {e}")

    return results


def scrape_marketbeat_initiations():
    """Scrape new initiations from MarketBeat."""
    url = "https://www.marketbeat.com/ratings/analyst-initiations/"
    results = []

    try:
        time.sleep(random.uniform(2, 4))  # polite delay between requests
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        table = soup.find("table")
        if not table:
            print("[MarketBeat Initiations] No table found.")
            return results

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            ticker  = cols[0].get_text(strip=True)
            company = cols[1].get_text(strip=True)
            broker  = cols[2].get_text(strip=True)
            rating  = cols[3].get_text(strip=True)
            pt_text = cols[4].get_text(strip=True) if len(cols) > 4 else ""

            broker_lower = broker.lower()
            matched_broker = None
            for b in TARGET_BROKERS:
                if b in broker_lower:
                    matched_broker = broker
                    break
            if not matched_broker:
                continue

            rating_lower = rating.lower()
            if not any(r in rating_lower for r in BULLISH_RATINGS):
                continue

            price_target = ""
            for part in pt_text.replace("→", " ").split():
                part = part.replace("$", "").replace(",", "").strip()
                try:
                    float(part)
                    price_target = f"${part}"
                except ValueError:
                    pass

            results.append({
                "ticker":        ticker.upper(),
                "company":       company,
                "broker":        matched_broker,
                "rating":        rating,
                "price_target":  price_target,
                "date":          datetime.today().strftime("%Y-%m-%d"),
                "source":        url,
                "source_name":   "MarketBeat Initiations",
            })

        print(f"[MarketBeat Initiations] Found {len(results)} bullish initiations.")

    except Exception as e:
        print(f"[MarketBeat Initiations] Error: {e}")

    return results


def scrape_stockanalysis():
    """Scrape analyst ratings from StockAnalysis.com."""
    url = "https://stockanalysis.com/actions/upgrades/"
    results = []

    try:
        time.sleep(random.uniform(2, 4))
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        table = soup.find("table")
        if not table:
            print("[StockAnalysis] No table found.")
            return results

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            ticker  = cols[0].get_text(strip=True)
            company = cols[1].get_text(strip=True)
            broker  = cols[2].get_text(strip=True)
            rating  = cols[3].get_text(strip=True)
            pt_text = cols[4].get_text(strip=True) if len(cols) > 4 else ""

            broker_lower = broker.lower()
            matched_broker = None
            for b in TARGET_BROKERS:
                if b in broker_lower:
                    matched_broker = broker
                    break
            if not matched_broker:
                continue

            rating_lower = rating.lower()
            if not any(r in rating_lower for r in BULLISH_RATINGS):
                continue

            price_target = ""
            for part in pt_text.replace("→", " ").split():
                part = part.replace("$", "").replace(",", "").strip()
                try:
                    float(part)
                    price_target = f"${part}"
                except ValueError:
                    pass

            results.append({
                "ticker":        ticker.upper(),
                "company":       company,
                "broker":        matched_broker,
                "rating":        rating,
                "price_target":  price_target,
                "date":          datetime.today().strftime("%Y-%m-%d"),
                "source":        url,
                "source_name":   "StockAnalysis Upgrades",
            })

        print(f"[StockAnalysis] Found {len(results)} bullish calls.")

    except Exception as e:
        print(f"[StockAnalysis] Error: {e}")

    return results


# ── Entry point (used by update_table.py) ────────────────────────────────────

def get_all_broker_calls():
    """Run all scrapers and return combined results."""
    all_results = []
    all_results.extend(scrape_marketbeat_upgrades())
    all_results.extend(scrape_marketbeat_initiations())
    all_results.extend(scrape_stockanalysis())
    return all_results


if __name__ == "__main__":
    calls = get_all_broker_calls()
    for c in calls:
        print(c)
