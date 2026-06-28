<<<<<<< HEAD
# 📈 Daily Stock Tracker

Automatically scrapes broker upgrades and initiations from top Wall Street firms every weekday morning and stores them in a table.

## What It Does
- Scrapes **MarketBeat** and **StockAnalysis** for analyst upgrades/initiations
- Filters for **target brokers** (B. Riley, Oppenheimer, Jefferies, Goldman, Morgan Stanley, etc.)
- Keeps only **bullish ratings** (Overweight, Buy, Outperform, Strong Buy)
- Enriches each stock with **Finnhub** data (price target, analyst consensus, current price)
- Saves everything to `data/stocks.csv` — with deduplication (no repeated rows)
- Runs automatically **every weekday at 9am EST** via GitHub Actions

## data/stocks.csv Columns

| Column | Description |
|--------|-------------|
| date | Date of the call |
| ticker | Stock symbol |
| company | Company name |
| broker | Brokerage firm |
| rating | Rating given (Overweight, Buy, etc.) |
| price_target | PT from the article |
| current_price | Live price from Finnhub |
| finnhub_target_mean | Average analyst PT (Finnhub) |
| finnhub_target_high | Highest analyst PT |
| finnhub_target_low | Lowest analyst PT |
| finnhub_analyst_count | Number of analysts covering it |
| consensus_strong_buy | # analysts with Strong Buy |
| consensus_buy | # analysts with Buy |
| consensus_hold | # analysts with Hold |
| consensus_sell | # analysts with Sell |
| source_name | Where the data came from |
| source | Direct link to source page |

## Setup

See the full setup instructions in the conversation where this was generated.
Add your `FINNHUB_API_KEY` as a GitHub Secret (optional but recommended).
=======
# stock-tracker
Automate tracking of most recommend stock by broker
>>>>>>> 9601ea61640d8fcedd1de61d3631ae3fa9bb75b9
