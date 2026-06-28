"""
update_table.py
Main orchestrator. Run daily by GitHub Actions.

Flow:
  1. Load existing data/stocks.csv (or create empty one)
  2. Scrape broker calls from MarketBeat + StockAnalysis
  3. Enrich new rows with Finnhub data
  4. Dedup: skip rows already in the CSV (same ticker + broker + date)
  5. Append new rows and save
  6. Print a summary of what was added
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add scripts dir to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

from scrape_marketbeat import get_all_broker_calls
from fetch_finnhub import enrich_with_finnhub

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR    = os.path.join(PROJECT_DIR, "data")
CSV_PATH    = os.path.join(DATA_DIR, "stocks.csv")

# ── Column order for the CSV ──────────────────────────────────────────────────

COLUMNS = [
    "date",
    "ticker",
    "company",
    "broker",
    "rating",
    "price_target",
    "current_price",
    "finnhub_target_mean",
    "finnhub_target_high",
    "finnhub_target_low",
    "finnhub_analyst_count",
    "consensus_strong_buy",
    "consensus_buy",
    "consensus_hold",
    "consensus_sell",
    "consensus_period",
    "source_name",
    "source",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_existing() -> pd.DataFrame:
    """Load existing CSV or return empty DataFrame."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH, dtype=str)
        print(f"[Table] Loaded {len(df)} existing rows from {CSV_PATH}")
        return df
    else:
        print("[Table] No existing CSV found — starting fresh.")
        return pd.DataFrame(columns=COLUMNS)


def make_dedup_key(row: dict) -> str:
    """Unique key: ticker + broker + date."""
    return f"{row.get('ticker','').upper()}|{row.get('broker','').lower()}|{row.get('date','')}"


def existing_keys(df: pd.DataFrame) -> set:
    """Build set of dedup keys from existing data."""
    keys = set()
    for _, row in df.iterrows():
        keys.add(make_dedup_key(row.to_dict()))
    return keys


def rows_to_df(rows: list) -> pd.DataFrame:
    """Convert list of dicts to DataFrame with correct columns."""
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(rows)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[COLUMNS]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today = datetime.today().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Stock Tracker — Daily Run: {today}")
    print(f"{'='*60}\n")

    # Step 1: Load existing data
    existing_df = load_existing()
    known_keys  = existing_keys(existing_df)

    # Step 2: Scrape broker calls
    print("\n[Step 2] Scraping broker calls...")
    new_calls = get_all_broker_calls()
    print(f"  Total scraped (before dedup): {len(new_calls)}")

    if not new_calls:
        print("\n  No broker calls found today. Exiting without changes.")
        return

    # Step 3: Dedup
    print("\n[Step 3] Deduplicating...")
    fresh_rows = []
    skipped    = 0
    for row in new_calls:
        key = make_dedup_key(row)
        if key in known_keys:
            skipped += 1
        else:
            fresh_rows.append(row)
            known_keys.add(key)  # prevent duplicates within today's batch too

    print(f"  Skipped (already in table): {skipped}")
    print(f"  New rows to add:            {len(fresh_rows)}")

    if not fresh_rows:
        print("\n  Nothing new today. Table unchanged.")
        return

    # Step 4: Enrich with Finnhub
    print("\n[Step 4] Enriching with Finnhub data...")
    enriched_rows = enrich_with_finnhub(fresh_rows)

    # Step 5: Append and save
    print("\n[Step 5] Saving updated table...")
    new_df      = rows_to_df(enriched_rows)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)

    # Sort: newest first
    combined_df["date"] = pd.to_datetime(combined_df["date"], errors="coerce")
    combined_df.sort_values("date", ascending=False, inplace=True)
    combined_df["date"] = combined_df["date"].dt.strftime("%Y-%m-%d")

    combined_df.to_csv(CSV_PATH, index=False)
    print(f"  Saved {len(combined_df)} total rows to {CSV_PATH}")

    # Step 6: Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY — {len(enriched_rows)} new stock(s) added today")
    print(f"{'='*60}")
    for row in enriched_rows:
        pt = row.get("price_target") or row.get("finnhub_target_mean") or "N/A"
        print(f"  {row['ticker']:6s} | {row['broker']:20s} | {row['rating']:20s} | PT: {pt}")
    print()


if __name__ == "__main__":
    main()
