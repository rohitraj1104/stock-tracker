"""
scrape_marketbeat.py  (v2 - reliable sources)
Uses multiple sources that work from GitHub Actions cloud IPs:
  1. Yahoo Finance hidden JSON API  - most reliable
  2. Finviz screener                - reliable backup
  3. MarketBeat (with better headers + fallback parsing)
  4. Benzinga RSS                   - structured XML
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, date
import time, random, re, json

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_BROKERS = [
    "b. riley", "b riley", "briley",
    "oppenheimer",
    "jefferies",
    "goldman sachs", "goldman",
    "morgan stanley",
    "jp morgan", "jpmorgan", "j.p. morgan",
    "bank of america", "bofa", "merrill",
    "wells fargo",
    "citigroup", "citi",
    "barclays",
    "ubs",
    "raymond james",
    "piper sandler",
    "william blair",
    "cowen",
    "stifel",
    "baird",
    "needham",
    "rbc capital", "rbc",
    "deutsche bank",
    "credit suisse",
    "mizuho",
    "wedbush",
    "keybanc",
    "truist",
]

BULLISH_RATINGS = [
    "overweight", "buy", "strong buy", "outperform",
    "market outperform", "positive", "conviction buy",
    "add", "accumulate", "sector outperform", "top pick"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

TODAY = date.today().strftime("%Y-%m-%d")


def is_target_broker(name: str) -> str | None:
    """Return matched broker name or None."""
    name_lower = name.lower()
    for b in TARGET_BROKERS:
        if b in name_lower:
            return name
    return None


def is_bullish(rating: str) -> bool:
    r = rating.lower()
    return any(b in r for b in BULLISH_RATINGS)


def parse_price_target(text: str) -> str:
    """Extract last dollar amount from a string like '$120 → $145'."""
    amounts = re.findall(r'\$?([\d,]+(?:\.\d+)?)', text.replace(",", ""))
    if amounts:
        try:
            return f"${float(amounts[-1]):.2f}"
        except:
            pass
    return ""


# ── Source 1: Yahoo Finance JSON API ─────────────────────────────────────────

def scrape_yahoo_finance():
    """
    Yahoo Finance has a public (no-auth) JSON endpoint for upgrades/downgrades.
    Returns recent analyst actions across all stocks.
    """
    url = "https://query2.finance.yahoo.com/v1/finance/recommendations/upgrade-downgrade"
    results = []

    # Yahoo needs these specific headers
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[Yahoo Finance] Status {resp.status_code} — trying alternate endpoint")
            return scrape_yahoo_finance_alt()

        data = resp.json()
        items = (data.get("upgradeDowngradeHistory", {})
                     .get("result", []))

        if not items:
            print("[Yahoo Finance] Empty result from API")
            return scrape_yahoo_finance_alt()

        for item in items:
            broker = item.get("firm", "")
            rating = item.get("toGrade", "")
            ticker = item.get("symbol", "").upper()
            epoch  = item.get("epochGradeDate", 0)
            action = item.get("action", "")  # up / down / init / reit

            # Only today's or recent (in case run late)
            if epoch:
                call_date = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d")
            else:
                call_date = TODAY

            matched = is_target_broker(broker)
            if not matched:
                continue
            if not is_bullish(rating):
                continue
            if action.lower() not in ("up", "init", "reit", "main"):
                continue  # skip downgrades

            results.append({
                "ticker":       ticker,
                "company":      "",
                "broker":       broker,
                "rating":       rating,
                "price_target": "",
                "date":         call_date,
                "source":       "https://finance.yahoo.com/research/upgrade-downgrade/",
                "source_name":  "Yahoo Finance",
            })

        print(f"[Yahoo Finance] Found {len(results)} bullish calls.")

    except Exception as e:
        print(f"[Yahoo Finance] Error: {e}")
        return scrape_yahoo_finance_alt()

    return results


def scrape_yahoo_finance_alt():
    """Alternate Yahoo Finance endpoint using query1."""
    url = "https://query1.finance.yahoo.com/v1/finance/recommendations/upgrade-downgrade"
    results = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        items = (data.get("upgradeDowngradeHistory", {})
                     .get("result", []))
        for item in items:
            broker = item.get("firm", "")
            rating = item.get("toGrade", "")
            ticker = item.get("symbol", "").upper()
            epoch  = item.get("epochGradeDate", 0)
            action = item.get("action", "")
            call_date = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d") if epoch else TODAY

            matched = is_target_broker(broker)
            if not matched or not is_bullish(rating):
                continue
            if action.lower() not in ("up", "init", "reit", "main"):
                continue

            results.append({
                "ticker":       ticker,
                "company":      "",
                "broker":       broker,
                "rating":       rating,
                "price_target": "",
                "date":         call_date,
                "source":       "https://finance.yahoo.com/research/upgrade-downgrade/",
                "source_name":  "Yahoo Finance",
            })
        print(f"[Yahoo Finance Alt] Found {len(results)} bullish calls.")
    except Exception as e:
        print(f"[Yahoo Finance Alt] Error: {e}")
    return results


# ── Source 2: Benzinga RSS ────────────────────────────────────────────────────

def scrape_benzinga_rss():
    """Parse Benzinga's analyst ratings RSS feed."""
    urls = [
        "https://www.benzinga.com/rss/feeds?category=analyst-ratings",
        "https://feeds.benzinga.com/benzinga/analyst-ratings",
        "https://www.benzinga.com/analyst-ratings/rss",
    ]
    results = []

    for url in urls:
        try:
            time.sleep(random.uniform(1, 2))
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item")
            if not items:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.find_all("item")

            for item in items:
                title = item.find("title")
                title = title.get_text(strip=True) if title else ""
                link  = item.find("link")
                link  = link.get_text(strip=True) if link else url
                desc  = item.find("description")
                desc  = desc.get_text(strip=True) if desc else ""

                full_text = f"{title} {desc}".lower()

                # Check if any target broker mentioned
                matched_broker = None
                for b in TARGET_BROKERS:
                    if b in full_text:
                        matched_broker = b.title()
                        break
                if not matched_broker:
                    continue

                # Check bullish rating mentioned
                matched_rating = None
                for r in BULLISH_RATINGS:
                    if r in full_text:
                        matched_rating = r.title()
                        break
                if not matched_rating:
                    continue

                # Extract ticker (usually $TICK or (TICK) in title)
                ticker_match = re.search(r'\b([A-Z]{1,5})\b', title)
                ticker = ticker_match.group(1) if ticker_match else ""

                # Extract price target
                pt = parse_price_target(full_text)

                results.append({
                    "ticker":       ticker,
                    "company":      "",
                    "broker":       matched_broker,
                    "rating":       matched_rating,
                    "price_target": pt,
                    "date":         TODAY,
                    "source":       link,
                    "source_name":  "Benzinga RSS",
                })

            if results:
                print(f"[Benzinga RSS] Found {len(results)} bullish calls from {url}")
                return results

        except Exception as e:
            print(f"[Benzinga RSS] Error ({url}): {e}")
            continue

    print("[Benzinga RSS] No results from any feed URL.")
    return results


# ── Source 3: Finviz News ─────────────────────────────────────────────────────

def scrape_finviz():
    """
    Finviz publishes analyst actions on their news page.
    Works reliably from cloud IPs.
    """
    url = "https://finviz.com/news.ashx?v=3"
    results = []

    try:
        time.sleep(random.uniform(1, 2))
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[Finviz] Status {resp.status_code}")
            return results

        soup = BeautifulSoup(resp.text, "html.parser")

        # Finviz news rows contain analyst actions
        news_rows = soup.find_all("tr", class_=re.compile("nn-tab-link|news"))
        if not news_rows:
            # Try finding table rows with analyst keywords
            all_rows = soup.find_all("tr")
            news_rows = [r for r in all_rows if any(
                kw in r.get_text().lower()
                for kw in ["overweight", "outperform", "buy", "initiates", "upgrades"]
            )]

        for row in news_rows:
            text = row.get_text(separator=" ", strip=True).lower()
            link_tag = row.find("a", href=True)
            link = link_tag["href"] if link_tag else url

            matched_broker = None
            for b in TARGET_BROKERS:
                if b in text:
                    matched_broker = b.title()
                    break
            if not matched_broker:
                continue

            matched_rating = None
            for r in BULLISH_RATINGS:
                if r in text:
                    matched_rating = r.title()
                    break
            if not matched_rating:
                continue

            ticker_match = re.search(r'\b([A-Z]{1,5})\b', row.get_text())
            ticker = ticker_match.group(1) if ticker_match else ""
            pt = parse_price_target(row.get_text())

            results.append({
                "ticker":       ticker,
                "company":      "",
                "broker":       matched_broker,
                "rating":       matched_rating,
                "price_target": pt,
                "date":         TODAY,
                "source":       link if link.startswith("http") else f"https://finviz.com/{link}",
                "source_name":  "Finviz",
            })

        print(f"[Finviz] Found {len(results)} bullish calls.")

    except Exception as e:
        print(f"[Finviz] Error: {e}")

    return results


# ── Source 4: MarketBeat (improved) ──────────────────────────────────────────

def scrape_marketbeat():
    """MarketBeat with improved selectors and fallback parsing."""
    urls = [
        ("https://www.marketbeat.com/ratings/analyst-upgrades/",    "MarketBeat Upgrades"),
        ("https://www.marketbeat.com/ratings/analyst-initiations/", "MarketBeat Initiations"),
    ]
    results = []

    for url, label in urls:
        try:
            time.sleep(random.uniform(3, 5))
            session = requests.Session()
            # First hit the homepage to get cookies
            session.get("https://www.marketbeat.com", headers=HEADERS, timeout=10)
            time.sleep(1)
            resp = session.get(url, headers=HEADERS, timeout=15)

            if resp.status_code != 200:
                print(f"[{label}] Status {resp.status_code} — skipping")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple table selectors
            table = (soup.find("table", {"id": "ratings-table"})
                     or soup.find("table", class_=re.compile("table"))
                     or soup.find("table"))

            if not table:
                print(f"[{label}] No table found")
                continue

            rows = table.find_all("tr")[1:]
            count = 0
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue

                texts = [c.get_text(strip=True) for c in cols]
                # Try to identify columns by content
                ticker  = texts[0] if texts else ""
                company = texts[1] if len(texts) > 1 else ""
                broker  = texts[2] if len(texts) > 2 else ""
                rating  = texts[3] if len(texts) > 3 else ""
                pt_text = texts[4] if len(texts) > 4 else ""

                matched = is_target_broker(broker)
                if not matched or not is_bullish(rating):
                    continue

                link_tag = cols[0].find("a", href=True) if cols else None
                link = ("https://www.marketbeat.com" + link_tag["href"]
                        if link_tag and link_tag["href"].startswith("/")
                        else url)

                results.append({
                    "ticker":       ticker.upper(),
                    "company":      company,
                    "broker":       matched,
                    "rating":       rating,
                    "price_target": parse_price_target(pt_text),
                    "date":         TODAY,
                    "source":       link,
                    "source_name":  label,
                })
                count += 1

            print(f"[{label}] Found {count} bullish calls.")

        except Exception as e:
            print(f"[{label}] Error: {e}")

    return results


# ── Entry point ───────────────────────────────────────────────────────────────

def get_all_broker_calls():
    """Run all scrapers and return combined deduplicated results."""
    all_results = []

    print("── Yahoo Finance ──────────────────────────────────")
    all_results.extend(scrape_yahoo_finance())

    print("── Benzinga RSS ───────────────────────────────────")
    all_results.extend(scrape_benzinga_rss())

    print("── Finviz ─────────────────────────────────────────")
    all_results.extend(scrape_finviz())

    print("── MarketBeat ─────────────────────────────────────")
    all_results.extend(scrape_marketbeat())

    # Remove exact duplicates (same ticker + broker + date)
    seen = set()
    unique = []
    for r in all_results:
        key = f"{r.get('ticker')}|{r.get('broker','').lower()}|{r.get('date')}"
        if key not in seen and r.get('ticker'):
            seen.add(key)
            unique.append(r)

    print(f"\n── Total unique bullish calls found: {len(unique)} ──")
    return unique


if __name__ == "__main__":
    calls = get_all_broker_calls()
    for c in calls:
        print(c)
