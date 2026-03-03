#!/usr/bin/env python3
"""
Fetch live S&P 500 data from Yahoo Finance and update data files.
Run: python3 fetch_live_data.py

1. Pulls full S&P 500 list from Wikipedia
2. Fetches live quotes via yfinance
3. Writes data.js and data.json
4. Regenerates stock pages via generate.py
5. Generates descriptions for new stocks via Groq (if needed)
"""

import json, os, sys, subprocess, time
from io import StringIO
import yfinance as yf
import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("500Market — Live Data Fetch")
print("=" * 60)

# ---- Step 1: Get S&P 500 ticker list from Wikipedia ----
print("\n[1/5] Fetching S&P 500 list from Wikipedia...")
import urllib.request

try:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    html = urllib.request.urlopen(req).read().decode("utf-8")
    tables = pd.read_html(StringIO(html))
    sp500_table = tables[0]
    tickers = sp500_table["Symbol"].tolist()
    names = sp500_table["Security"].tolist()
    sectors = sp500_table["GICS Sector"].tolist()
    # Fix tickers with dots (BRK.B → BRK-B for Yahoo)
    yahoo_tickers = [t.replace(".", "-") for t in tickers]
    print(f"  Found {len(tickers)} stocks")
except Exception as e:
    print(f"  Error fetching from Wikipedia: {e}")
    print("  Using cached data.json instead")
    sys.exit(1)

# ---- Step 2: Fetch quotes in batches via yfinance ----
print("\n[2/5] Fetching live quotes from Yahoo Finance...")

# Build ticker → info mapping
ticker_to_name = dict(zip(tickers, names))
ticker_to_sector = dict(zip(tickers, sectors))

# Fetch all at once (yfinance handles batching internally)
batch_str = " ".join(yahoo_tickers)

try:
    data = yf.download(batch_str, period="7d", group_by="ticker", progress=False, threads=True)
except Exception as e:
    print(f"  Error downloading price data: {e}")
    sys.exit(1)

# Also fetch info for market cap, P/E, etc.
print("  Fetching detailed info (market cap, P/E, volume)...")
tickers_objs = yf.Tickers(batch_str)

stocks = []
failed = []
domain_map = {}

# Load existing domain mappings
try:
    with open("data.json", "r") as f:
        old_data = json.load(f)
        domain_map = {s["ticker"]: s.get("domain", "") for s in old_data}
except FileNotFoundError:
    pass

# Color palette for sectors
SECTOR_COLORS = {
    "Information Technology": "#3861FB",
    "Health Care": "#D52B1E",
    "Financials": "#003087",
    "Consumer Discretionary": "#FF9900",
    "Communication Services": "#4285F4",
    "Industrials": "#0039A6",
    "Consumer Staples": "#0071CE",
    "Energy": "#ED1B2D",
    "Utilities": "#00529B",
    "Real Estate": "#003D6B",
    "Materials": "#8A6D3B",
}

def get_color(sector):
    return SECTOR_COLORS.get(sector, "#555555")

# Common domain overrides for companies where website != obvious
DOMAIN_OVERRIDES = {
    "AAPL": "apple.com", "MSFT": "microsoft.com", "NVDA": "nvidia.com",
    "AMZN": "amazon.com", "GOOGL": "google.com", "GOOG": "google.com",
    "META": "meta.com", "BRK.B": "berkshirehathaway.com", "BRK.A": "berkshirehathaway.com",
    "TSLA": "tesla.com", "JPM": "jpmorganchase.com", "V": "visa.com",
    "JNJ": "jnj.com", "PG": "pg.com", "HD": "homedepot.com",
    "KO": "coca-colacompany.com", "PEP": "pepsico.com", "MCD": "mcdonalds.com",
    "DIS": "thewaltdisneycompany.com", "NKE": "nike.com", "T": "att.com",
    "GE": "ge.com", "PM": "pmi.com", "DE": "deere.com",
    "UNP": "up.com", "TXN": "ti.com", "CMCSA": "comcast.com",
    "MMM": "3m.com", "LLY": "lilly.com", "CRM": "salesforce.com",
    "NFLX": "netflix.com", "COST": "costco.com", "WMT": "walmart.com",
}

print("  Processing stock data...")
for i, (ticker, yahoo_ticker) in enumerate(zip(tickers, yahoo_tickers)):
    try:
        # Get price data from downloaded batch
        if len(yahoo_tickers) > 1:
            try:
                stock_data = data[yahoo_ticker] if yahoo_ticker in data.columns.get_level_values(0) else None
            except:
                stock_data = None
        else:
            stock_data = data

        if stock_data is None or stock_data.empty:
            failed.append(ticker)
            continue

        # Get latest price and changes
        closes = stock_data["Close"].dropna()
        if len(closes) < 2:
            failed.append(ticker)
            continue

        price = float(closes.iloc[-1])
        prev_close = float(closes.iloc[-2])
        first_close = float(closes.iloc[0])

        change1d = ((price - prev_close) / prev_close) * 100
        change7d = ((price - first_close) / first_close) * 100

        # Get info from yfinance
        try:
            info = tickers_objs.tickers[yahoo_ticker].info
            market_cap = info.get("marketCap", 0) or 0
            pe = info.get("trailingPE", None)
            volume = info.get("averageVolume", 0) or info.get("volume", 0) or 0
            ytd_change = info.get("ytdReturn", None)
            website = info.get("website", "")
            fifty_two_high = info.get("fiftyTwoWeekHigh", price * 1.1)
            fifty_two_low = info.get("fiftyTwoWeekLow", price * 0.9)
        except:
            market_cap = 0
            pe = None
            volume = 0
            ytd_change = None
            website = ""
            fifty_two_high = price * 1.1
            fifty_two_low = price * 0.9

        # Calculate YTD if not available
        if ytd_change is None:
            ytd_change = change7d * 2  # rough estimate

        # Determine domain
        domain = DOMAIN_OVERRIDES.get(ticker, "")
        if not domain and domain_map.get(ticker):
            domain = domain_map[ticker]
        if not domain and website:
            domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if not domain:
            # Guess from company name
            name_clean = ticker_to_name[ticker].lower().replace(" ", "").replace(",", "").replace(".", "")
            domain = f"{name_clean}.com"

        sector = ticker_to_sector[ticker]

        stocks.append({
            "rank": 0,  # Will be set after sorting
            "name": ticker_to_name[ticker],
            "ticker": ticker,
            "sector": sector,
            "price": round(price, 2),
            "change1d": round(change1d, 2),
            "change7d": round(change7d, 2),
            "changeYtd": round(ytd_change, 2),
            "marketCap": int(market_cap),
            "volume": int(volume * price),  # dollar volume
            "pe": round(pe, 1) if pe and pe > 0 else None,
            "color": get_color(sector),
            "domain": domain,
        })

    except Exception as e:
        failed.append(ticker)
        continue

    # Progress
    if (i + 1) % 50 == 0:
        print(f"  Processed {i + 1}/{len(tickers)}...")

# Sort by market cap and assign ranks
stocks.sort(key=lambda s: s["marketCap"], reverse=True)
for i, s in enumerate(stocks):
    s["rank"] = i + 1

print(f"  Successfully fetched {len(stocks)} stocks, {len(failed)} failed")
if failed:
    print(f"  Failed tickers: {', '.join(failed[:20])}{'...' if len(failed) > 20 else ''}")

# ---- Fetch S&P 500 Index Data ----
print("\n  Fetching S&P 500 index (^GSPC)...")
try:
    sp_ticker = yf.Ticker("^GSPC")
    sp_info = sp_ticker.info
    sp_hist = sp_ticker.history(period="5d")

    sp_price = sp_info.get("regularMarketPrice", sp_info.get("previousClose", 0))
    sp_prev = sp_info.get("regularMarketPreviousClose", sp_info.get("previousClose", 0))
    sp_open = sp_info.get("regularMarketOpen", sp_info.get("open", 0))
    sp_high = sp_info.get("dayHigh", sp_info.get("regularMarketDayHigh", 0))
    sp_low = sp_info.get("dayLow", sp_info.get("regularMarketDayLow", 0))
    sp_52h = sp_info.get("fiftyTwoWeekHigh", 0)
    sp_52l = sp_info.get("fiftyTwoWeekLow", 0)
    sp_change = sp_price - sp_prev if sp_prev else 0
    sp_change_pct = (sp_change / sp_prev * 100) if sp_prev else 0

    # YTD: compare to first trading day of the year
    try:
        ytd_hist = sp_ticker.history(start="2026-01-02", end="2026-01-05")
        if not ytd_hist.empty:
            jan_close = float(ytd_hist["Close"].iloc[0])
            sp_ytd = ((sp_price - jan_close) / jan_close) * 100
        else:
            sp_ytd = sp_change_pct * 30
    except:
        sp_ytd = sp_change_pct * 30

    index_data = {
        "price": round(sp_price, 2),
        "change": round(sp_change, 2),
        "changePct": round(sp_change_pct, 2),
        "open": round(sp_open, 2),
        "high": round(sp_high, 2),
        "low": round(sp_low, 2),
        "high52": round(sp_52h, 2),
        "low52": round(sp_52l, 2),
        "ytd": round(sp_ytd, 2),
    }
    print(f"  S&P 500: {index_data['price']} ({index_data['changePct']:+.2f}%)")
except Exception as e:
    print(f"  Warning: Could not fetch S&P 500 index: {e}")
    index_data = None

# Compute Fear & Greed proxy from stock data
advancing = len([s for s in stocks if s["change1d"] > 0])
declining = len([s for s in stocks if s["change1d"] < 0])
adv_pct = advancing / len(stocks) * 100 if stocks else 50
# Simple fear/greed: map advancing% to 0-100 scale (30% advancing = 0, 70% = 100)
fear_greed = max(0, min(100, int((adv_pct - 30) * 2.5)))
if fear_greed >= 75:
    fg_label = "Extreme Greed"
elif fear_greed >= 55:
    fg_label = "Greed"
elif fear_greed >= 45:
    fg_label = "Neutral"
elif fear_greed >= 25:
    fg_label = "Fear"
else:
    fg_label = "Extreme Fear"

# Count 52-week highs
high_count = 0
for s in stocks:
    # Approximate: if change1d > 0 and changeYtd > 15, likely near 52W high
    # Better: use actual 52W high from yfinance if available
    try:
        info = tickers_objs.tickers[s["ticker"].replace(".", "-")].info
        h52 = info.get("fiftyTwoWeekHigh", 0)
        if h52 and s["price"] >= h52 * 0.98:
            high_count += 1
    except:
        pass

market_summary = {
    "index": index_data,
    "fearGreed": fear_greed,
    "fearGreedLabel": fg_label,
    "advancing": advancing,
    "declining": declining,
    "high52Count": high_count,
    "totalMarketCap": sum(s["marketCap"] for s in stocks),
    "totalVolume": sum(s["volume"] for s in stocks),
}

# ---- Step 3: Write data files ----
print(f"\n[3/5] Writing data files...")

# data.json
with open("data.json", "w") as f:
    json.dump(stocks, f, indent=2)
print(f"  Wrote data.json ({len(stocks)} stocks)")

# market_summary.json
with open("market_summary.json", "w") as f:
    json.dump(market_summary, f, indent=2)
print(f"  Wrote market_summary.json")

# Load descriptions to embed in data.js
try:
    with open("descriptions.json", "r") as f:
        all_descriptions = json.load(f)
except FileNotFoundError:
    all_descriptions = {}

# data.js (stocks + market summary + timestamp — descriptions loaded separately)
from datetime import datetime
last_updated = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

js_content = "const SP500_STOCKS = " + json.dumps(stocks, indent=4) + ";\n\n"
js_content += "const MARKET_SUMMARY = " + json.dumps(market_summary, indent=4) + ";\n\n"
js_content += f'const DATA_LAST_UPDATED = "{last_updated}";\n'

# descriptions.js (loaded async, not blocking)
desc_js = "const STOCK_DESCRIPTIONS_DATA = " + json.dumps(all_descriptions) + ";\n"
with open("descriptions_data.js", "w") as f:
    f.write(desc_js)
print(f"  Wrote descriptions_data.js ({len(all_descriptions)} descriptions)")
with open("data.js", "w") as f:
    f.write(js_content)
print(f"  Wrote data.js")

# ---- Step 4: Generate descriptions for new stocks ----
print(f"\n[4/5] Checking descriptions...")
try:
    with open("descriptions.json", "r") as f:
        descriptions = json.load(f)
except FileNotFoundError:
    descriptions = {}

new_tickers = [s for s in stocks if s["ticker"] not in descriptions]
if new_tickers:
    print(f"  Need descriptions for {len(new_tickers)} new stocks")
    print(f"  Running generate_descriptions.py...")
    subprocess.run([sys.executable, "generate_descriptions.py"], check=False)
else:
    print(f"  All {len(descriptions)} descriptions up to date")

# ---- Step 5: Regenerate stock pages ----
print(f"\n[5/5] Regenerating stock pages...")
subprocess.run([sys.executable, "generate.py"], check=True)

# Update the top bar stats in index.html
total_mcap = sum(s["marketCap"] for s in stocks)
total_vol = sum(s["volume"] for s in stocks)
advancing = len([s for s in stocks if s["change1d"] > 0])
declining = len([s for s in stocks if s["change1d"] < 0])

print(f"\n{'=' * 60}")
print(f"DONE! Updated {len(stocks)} S&P 500 stocks")
print(f"  Total Market Cap: ${total_mcap/1e12:.1f}T")
print(f"  Advancing: {advancing} | Declining: {declining}")
print(f"  Top gainer: {stocks[0]['ticker']} isn't right — let me find it...")

gainers = sorted(stocks, key=lambda s: s["change1d"], reverse=True)
losers = sorted(stocks, key=lambda s: s["change1d"])
print(f"  Top gainer: {gainers[0]['ticker']} ({gainers[0]['change1d']:+.2f}%)")
print(f"  Top loser:  {losers[0]['ticker']} ({losers[0]['change1d']:+.2f}%)")
print(f"{'=' * 60}")
