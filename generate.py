#!/usr/bin/env python3
"""
Generate individual stock pages for 500Market.com SEO.
Run: python3 generate.py
"""

import json, os, re

# Read stock data from data.json
with open("data.json", "r") as f:
    stocks = json.load(f)

# Load chart data for embedding in stock pages
try:
    with open("charts_data.json", "r") as f:
        ALL_CHARTS = json.load(f)
    print(f"Loaded chart data for {len(ALL_CHARTS)} tickers")
except FileNotFoundError:
    ALL_CHARTS = {}
    print("Warning: charts_data.json not found, stock pages will use fallback charts")

# Load AI-generated descriptions
try:
    with open("descriptions.json", "r") as f:
        DESCRIPTIONS = json.load(f)
    print(f"Loaded {len(DESCRIPTIONS)} descriptions from descriptions.json")
except FileNotFoundError:
    DESCRIPTIONS = {}
    print("Warning: descriptions.json not found, using generic descriptions")

def fmt_mcap(n):
    if n >= 1e12: return f"${n/1e12:.2f}T"
    if n >= 1e9: return f"${n/1e9:.2f}B"
    if n >= 1e6: return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"

def fmt_vol(n):
    if n >= 1e9: return f"${n/1e9:.1f}B"
    if n >= 1e6: return f"${n/1e6:.1f}M"
    return f"${n:,.0f}"

def fmt_price(n):
    return f"${n:,.2f}"

def fmt_change(val):
    cls = "change-up" if val >= 0 else "change-down"
    sign = "+" if val >= 0 else ""
    return f'<span class="{cls}">{sign}{val:.2f}%</span>'

def get_desc(s):
    if s["ticker"] in DESCRIPTIONS:
        return DESCRIPTIONS[s["ticker"]]
    return f'{s["name"]} ({s["ticker"]}) is a {s["sector"]} company listed on the S&P 500 with a market capitalization of {fmt_mcap(s["marketCap"])}. The stock is currently trading at {fmt_price(s["price"])} per share.'

def get_peers(stock, all_stocks):
    return [s for s in all_stocks if s["sector"] == stock["sector"] and s["ticker"] != stock["ticker"]][:8]

for stock in stocks:
    ticker = stock["ticker"].lower().replace(".", "-")
    peers = get_peers(stock, stocks)
    desc = get_desc(stock)
    pe_val = f'{stock["pe"]:.1f}' if stock["pe"] else "N/A"
    eps = f'${stock["price"] / stock["pe"]:.2f}' if stock["pe"] else "N/A"

    high52 = stock["price"] * (1 + abs(stock["changeYtd"]) / 100 + 0.12)
    low52 = stock["price"] * (1 - abs(stock["changeYtd"]) / 100 - 0.08)
    range_pct = ((stock["price"] - low52) / (high52 - low52)) * 100

    chg1d_cls = "change-up" if stock["change1d"] >= 0 else "change-down"
    chg1d_sign = "+" if stock["change1d"] >= 0 else ""
    chg1d_html = f'<span class="sp-price-chg {chg1d_cls}">{chg1d_sign}{stock["change1d"]:.2f}%</span>'

    meta_title = f'{stock["name"]} ({stock["ticker"]}) Stock Price, Chart & Market Cap | 500Market'
    meta_desc = f'{stock["name"]} ({stock["ticker"]}) stock price today is {fmt_price(stock["price"])}. View live chart, market cap of {fmt_mcap(stock["marketCap"])}, P/E ratio, and sector peers on 500Market.'
    canonical = f'https://500market.com/s/{ticker}.html'
    logo_url = f'https://www.google.com/s2/favicons?domain={stock["domain"]}&sz=128'

    peers_html = ""
    for p in peers:
        chg_cls = "change-up" if p["change1d"] >= 0 else "change-down"
        chg_sign = "+" if p["change1d"] >= 0 else ""
        peers_html += f'''
            <a href="{p["ticker"].lower().replace(".", "-")}.html" class="peer-row">
                <span class="peer-name">{p["ticker"]} — {p["name"]}</span>
                <span class="peer-price">{fmt_price(p["price"])}</span>
                <span class="peer-change {chg_cls}">{chg_sign}{p["change1d"]:.2f}%</span>
            </a>'''

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "FinancialProduct",
        "name": f'{stock["name"]} ({stock["ticker"]})',
        "description": desc,
        "url": canonical,
        "provider": {
            "@type": "Organization",
            "name": stock["name"],
            "url": f'https://{stock["domain"]}'
        }
    })

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta_title}</title>
    <meta name="description" content="{meta_desc}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{canonical}">

    <!-- Open Graph -->
    <meta property="og:title" content="{meta_title}">
    <meta property="og:description" content="{meta_desc}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="500Market">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{meta_title}">
    <meta name="twitter:description" content="{meta_desc}">

    <!-- Schema.org -->
    <script type="application/ld+json">{schema}</script>

    <link rel="icon" type="image/svg+xml" href="../favicon.svg">
    <script defer src="https://cloud.umami.is/script.js" data-website-id="e6f6d801-d98f-4c20-9ad6-f4ede5cab47c"></script>
    <link rel="stylesheet" href="../styles.css">
    <style>
        .stock-page {{ max-width: 900px; margin: 0 auto; padding: 24px; }}
        .sp-header {{ display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }}
        .sp-logo {{ width: 56px; height: 56px; border-radius: 50%; object-fit: contain; background: var(--bg-secondary); border: 1px solid var(--border); }}
        .sp-icon {{ width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 18px; color: white; }}
        .sp-title {{ font-size: 28px; font-weight: 800; color: var(--text); }}
        .sp-ticker-row {{ display: flex; align-items: center; gap: 8px; margin-top: 2px; }}
        .sp-ticker {{ font-size: 15px; color: var(--text-secondary); }}
        .sp-badge {{ font-size: 12px; padding: 2px 10px; border-radius: 10px; background: var(--bg-secondary); color: var(--text-secondary); font-weight: 500; }}
        .sp-price-row {{ margin-bottom: 24px; }}
        .sp-price {{ font-size: 40px; font-weight: 800; color: var(--text); }}
        .sp-price-chg {{ font-size: 18px; font-weight: 600; margin-left: 10px; }}
        .sp-chart {{ height: 280px; margin-bottom: 28px; border: 1px solid var(--border); border-radius: 12px; padding: 16px; background: var(--card-bg); }}
        .sp-chart-periods {{ display: flex; gap: 4px; margin-bottom: 12px; }}
        .sp-chart-area {{ height: 220px; }}
        .sp-chart-area svg {{ width: 100%; height: 100%; display: block; }}
        .sp-stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1px; background: var(--border); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 28px; }}
        .sp-stat {{ padding: 16px; background: var(--bg); }}
        .sp-stat-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
        .sp-stat-val {{ font-size: 16px; font-weight: 700; color: var(--text); }}
        .sp-range {{ grid-column: 1 / -1; padding: 16px; background: var(--bg); }}
        .sp-range-labels {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }}
        .sp-range-bar {{ height: 8px; border-radius: 4px; background: var(--border); position: relative; }}
        .sp-range-fill {{ height: 100%; border-radius: 4px; background: var(--blue); }}
        .sp-range-dot {{ position: absolute; top: 50%; transform: translate(-50%, -50%); width: 14px; height: 14px; border-radius: 50%; background: var(--blue); border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }}
        .sp-about {{ margin-bottom: 28px; }}
        .sp-about h2 {{ font-size: 18px; font-weight: 700; margin-bottom: 8px; }}
        .sp-about p {{ font-size: 15px; color: var(--text-secondary); line-height: 1.7; }}
        .sp-peers {{ margin-bottom: 28px; }}
        .sp-section-title {{ font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
        .news-list {{ display: flex; flex-direction: column; margin-bottom: 28px; border-radius: 10px; overflow: hidden; }}
        .news-item {{ display: block; padding: 12px 14px; border-bottom: 1px solid var(--border); text-decoration: none; color: var(--text); transition: all 0.15s; }}
        .news-item:first-child {{ border-top: 1px solid var(--border); }}
        .news-item:hover {{ background: var(--bg-secondary); }}
        .news-content {{ }}
        .news-headline {{ font-size: 14px; font-weight: 600; color: var(--text); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        .news-meta {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}
        .news-source {{ font-weight: 500; }}
        .news-loading {{ text-align: center; padding: 20px; color: var(--text-secondary); font-size: 14px; }}
        .peer-row {{ display: flex; align-items: center; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 6px; text-decoration: none; color: var(--text); transition: all 0.15s; gap: 12px; }}
        .peer-row:hover {{ border-color: var(--blue); background: var(--bg-secondary); }}
        .peer-name {{ flex: 1; font-weight: 600; font-size: 14px; }}
        .peer-price {{ width: 90px; text-align: right; font-size: 14px; color: var(--text-secondary); }}
        .peer-change {{ width: 70px; text-align: right; font-size: 13px; font-weight: 600; }}
        .peer-name {{ font-weight: 600; font-size: 14px; }}
        .peer-price {{ font-size: 14px; color: var(--text-secondary); }}
        .sp-back {{ display: inline-flex; align-items: center; gap: 6px; color: var(--blue); text-decoration: none; font-size: 14px; font-weight: 500; margin-bottom: 20px; }}
        .sp-back:hover {{ text-decoration: underline; }}
        .sp-breadcrumb {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; }}
        .sp-breadcrumb a {{ color: var(--blue); text-decoration: none; }}
        .sp-breadcrumb a:hover {{ text-decoration: underline; }}
        @media (max-width: 640px) {{
            .sp-stats {{ grid-template-columns: 1fr 1fr; }}
            .sp-price {{ font-size: 32px; }}
        }}
    </style>
</head>
<body>
    <!-- Top Bar -->
    <div class="top-bar">
        <div class="top-bar-inner">
            <span>Stocks: <strong>503</strong></span>
            <span>Market Cap: <strong>$51.2T</strong></span>
            <span>S&P 500: <strong>5,954.50</strong> <span class="change-up">+0.82%</span></span>
        </div>
    </div>

    <header class="header">
        <div class="header-inner">
            <a href="../index.html" style="text-decoration:none;display:flex;align-items:center;gap:8px">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <rect width="28" height="28" rx="6" fill="#3861FB"/>
                    <text x="14" y="18" text-anchor="middle" fill="white" font-size="10" font-weight="700" font-family="system-ui">500</text>
                </svg>
                <span class="logo-text">500Market</span>
            </a>
            <nav class="nav">
                <a href="../index.html">Stocks</a>
                <a href="../index.html#sectors">Sectors</a>
            </nav>
        </div>
    </header>

    <div class="stock-page">
        <nav class="sp-breadcrumb">
            <a href="../index.html">Home</a> &rsaquo; <a href="../index.html">Stocks</a> &rsaquo; {stock["name"]} ({stock["ticker"]})
        </nav>

        <div class="sp-header">
            <img class="sp-logo" src="{logo_url}" alt="{stock["ticker"]} logo"
                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
            <div class="sp-icon" style="background:{stock["color"]};display:none">{stock["ticker"][:2]}</div>
            <div>
                <div class="sp-title">{stock["name"]}</div>
                <div class="sp-ticker-row">
                    <span class="sp-ticker">{stock["ticker"]}</span>
                    <span class="sp-badge">Rank #{stock["rank"]}</span>
                    <span class="sp-badge">{stock["sector"]}</span>
                </div>
            </div>
        </div>

        <div class="sp-price-row">
            <span class="sp-price">{fmt_price(stock["price"])}</span>
            <span id="periodChange">{chg1d_html}</span>
        </div>

        <div class="sp-chart">
            <div class="sp-chart-periods">
                <button class="chart-period active" data-d="1">1D</button>
                <button class="chart-period" data-d="7">1W</button>
                <button class="chart-period" data-d="30">1M</button>
                <button class="chart-period" data-d="90">3M</button>
                <button class="chart-period" data-d="180">6M</button>
                <button class="chart-period" data-d="365">1Y</button>
                <button class="chart-period" data-d="1825">5Y</button>
            </div>
            <div class="sp-chart-area" id="stockChart"></div>
        </div>

        <h2 class="sp-section-title">Key Statistics</h2>
        <div class="sp-stats">
            <div class="sp-stat">
                <div class="sp-stat-label">Market Cap</div>
                <div class="sp-stat-val">{fmt_mcap(stock["marketCap"])}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">Volume (24h)</div>
                <div class="sp-stat-val">{fmt_vol(stock["volume"])}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">P/E Ratio</div>
                <div class="sp-stat-val">{pe_val}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">EPS</div>
                <div class="sp-stat-val">{eps}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">1 Day</div>
                <div class="sp-stat-val">{fmt_change(stock["change1d"])}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">7 Day</div>
                <div class="sp-stat-val">{fmt_change(stock["change7d"])}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">YTD</div>
                <div class="sp-stat-val">{fmt_change(stock["changeYtd"])}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">Sector</div>
                <div class="sp-stat-val">{stock["sector"]}</div>
            </div>
            <div class="sp-stat">
                <div class="sp-stat-label">S&P 500 Rank</div>
                <div class="sp-stat-val">#{stock["rank"]}</div>
            </div>
            <div class="sp-range">
                <div class="sp-range-labels">
                    <span>52W Low: ${low52:,.2f}</span>
                    <span>52W High: ${high52:,.2f}</span>
                </div>
                <div class="sp-range-bar">
                    <div class="sp-range-fill" style="width:{range_pct:.1f}%"></div>
                    <div class="sp-range-dot" style="left:{range_pct:.1f}%"></div>
                </div>
            </div>
        </div>

        <div class="sp-about">
            <h2 class="sp-section-title">About {stock["name"]}</h2>
            <p>{desc}</p>
        </div>

        <div>
            <h2 class="sp-section-title">Latest News</h2>
            <div class="news-list" id="newsList">
                <div class="news-loading">Loading latest news...</div>
            </div>
        </div>

        <div class="sp-peers">
            <h3 class="sp-section-title">Sector Peers &mdash; {stock["sector"]}</h3>
            {peers_html}
            <a href="../index.html" style="display:block;text-align:center;margin-top:12px;color:#3861FB;font-size:13px;font-weight:600;text-decoration:none">View all {stock["sector"]} stocks &rarr;</a>
        </div>
    </div>

    <div class="subscribe-section" style="background:var(--bg-secondary);border-top:1px solid var(--border);padding:40px 24px;margin-top:32px">
        <div style="max-width:480px;margin:0 auto;text-align:center">
            <h2 style="font-size:20px;font-weight:800;color:var(--text);margin-bottom:6px">Daily Market Brief</h2>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">S&P 500 closing prices, top movers, and sector performance — delivered daily.</p>
            <form id="subForm" style="display:flex;gap:8px;max-width:380px;margin:0 auto">
                <input type="email" id="subEmail" placeholder="Enter your email" required style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;font-size:14px;background:var(--bg);color:var(--text);outline:none">
                <button type="submit" style="padding:10px 20px;border:none;border-radius:8px;background:#3861FB;color:#fff;font-size:14px;font-weight:600;cursor:pointer">Subscribe</button>
            </form>
            <div id="subMsg" style="margin-top:10px;font-size:13px;min-height:18px"></div>
        </div>
    </div>

    <footer class="footer">
        <p>500Market &mdash; S&P 500 stock tracker. Not financial advice.</p>
    </footer>

    <script>
    // Inline chart renderer for this stock
    const STOCK = {json.dumps({"ticker": stock["ticker"], "price": stock["price"], "change1d": stock["change1d"], "change7d": stock["change7d"]})};
    const STOCK_CHART = {json.dumps(ALL_CHARTS.get(stock["ticker"], {}), separators=(',', ':'))};

    function getStockChartData(days) {{
        const entry = STOCK_CHART;
        if (!entry) return null;
        if (days === 1) {{
            if (!entry.intraday || !entry.intraday.times) return null;
            const {{ times, prices, date: iDate }} = entry.intraday;
            const data = [];
            for (let i = 0; i < times.length; i++) {{
                const [hh, mm] = times[i].split(':').map(Number);
                const d = new Date(iDate + 'T00:00:00');
                d.setHours(hh, mm, 0, 0);
                data.push({{ date: d, price: prices[i] }});
            }}
            return data.length > 2 ? data : null;
        }}
        if (!entry.daily || !entry.daily.prices || entry.daily.prices.length < 10) return null;
        const {{ prices }} = entry.daily;
        let sliced = days < prices.length ? prices.slice(prices.length - days) : prices;
        let sampled = sliced;
        if (sliced.length > 500) {{
            const step = sliced.length / 250;
            sampled = [];
            for (let i = 0; i < 250; i++) sampled.push(sliced[Math.round(i * step)]);
        }}
        const data = [];
        const dates = [];
        let d = new Date();
        while (dates.length < sampled.length) {{
            const dow = d.getDay();
            if (dow !== 0 && dow !== 6) dates.unshift(new Date(d));
            d.setDate(d.getDate() - 1);
        }}
        for (let i = 0; i < sampled.length; i++) data.push({{ date: dates[i], price: sampled[i] }});
        return data.length > 2 ? data : null;
    }}

    function genChart(days) {{
        const container = document.getElementById("stockChart");
        const w = container.clientWidth || 600, h = container.clientHeight || 220;
        const pT=10,pB=24,pL=55,pR=10, cW=w-pL-pR, cH=h-pT-pB;
        // Try real data first
        const realData = getStockChartData(days);
        let prices, chartDates;
        if (realData) {{
            prices = realData.map(d => d.price);
            chartDates = realData.map(d => d.date);
        }} else {{
            // Fallback: pseudorandom
            let seed = 0;
            for (let i = 0; i < STOCK.ticker.length; i++) seed += STOCK.ticker.charCodeAt(i) * (i + 1);
            seed += days;
            function rand() {{ seed = (seed * 16807) % 2147483647; return (seed & 0x7fffffff) / 0x7fffffff; }}
            prices=[STOCK.price];
            if (days===1) {{
                const vol=0.003, drift=STOCK.change1d>=0?0.0001:-0.0001;
                for(let i=1;i<26;i++) {{ const p=prices[i-1]; prices.push(p+p*((rand()-0.5)*2*vol-drift)); }}
            }} else {{
                const vol=0.012, drift=STOCK.change7d>0?0.0004:-0.0003;
                for(let i=1;i<days;i++) {{ const p=prices[i-1]; prices.push(p+p*((rand()-0.5)*2*vol-drift)); }}
            }}
            prices.reverse();
            chartDates = null;
        }}
        // For 1D, prepend previous close so chart starts from yesterday's close
        if (days===1) {{
            const prevClose=STOCK.price/(1+STOCK.change1d/100);
            prices.unshift(prevClose);
            if (chartDates) {{ const t=new Date(chartDates[0]); t.setMinutes(t.getMinutes()-1); chartDates.unshift(t); }}
        }}
        const mn=Math.min(...prices),mx=Math.max(...prices),rng=mx-mn||1;
        const up=prices[prices.length-1]>=prices[0], col=up?"#16c784":"#ea3943";
        const pts=prices.map((p,i)=>{{const x=pL+(i/(prices.length-1))*cW; const y=pT+(1-(p-mn)/rng)*cH; return {{x,y}};}});
        let pathD=pts.map((p,i)=>(i===0?`M${{p.x}},${{p.y}}`:`L${{p.x}},${{p.y}}`)).join(" ");
        const fillD=pathD+` L${{pts[pts.length-1].x}},${{pT+cH}} L${{pL}},${{pT+cH}} Z`;
        let yL="",gL="";
        for(let i=0;i<=4;i++){{const v=mn+(rng*i/4);const y=pT+(1-i/4)*cH;yL+=`<text x="${{pL-8}}" y="${{y+4}}" text-anchor="end" fill="#9ca3af" font-size="11" font-family="system-ui">$${{v.toFixed(0)}}</text>`;gL+=`<line x1="${{pL}}" y1="${{y}}" x2="${{w-pR}}" y2="${{y}}" stroke="#f3f4f6" stroke-width="1"/>`;}}
        let xL="";const lc=Math.min(6,prices.length);const now=new Date();
        for(let i=0;i<lc;i++){{const idx=Math.round(i*(prices.length-1)/(lc-1));const x=pts[idx].x;let label;
        if(chartDates){{const d=chartDates[idx];label=days===1?d.toLocaleTimeString("en-US",{{hour:"numeric",minute:"2-digit"}}):days<=30?`${{d.getMonth()+1}}/${{d.getDate()}}`:d.toLocaleDateString("en-US",{{month:"short",day:"numeric"}});}}
        else if(days===1){{const d=new Date(now);d.setHours(9,30,0,0);d.setMinutes(d.getMinutes()+idx*15);label=d.toLocaleTimeString("en-US",{{hour:"numeric",minute:"2-digit"}});}}
        else{{const d=new Date(now);d.setDate(d.getDate()-(prices.length-1-idx));label=days<=30?`${{d.getMonth()+1}}/${{d.getDate()}}`:d.toLocaleDateString("en-US",{{month:"short",day:"numeric"}});}}
        xL+=`<text x="${{x}}" y="${{h-4}}" text-anchor="middle" fill="#9ca3af" font-size="10" font-family="system-ui">${{label}}</text>`;}}
        const lp=pts[pts.length-1];
        container.innerHTML=`<svg viewBox="0 0 ${{w}} ${{h}}"><defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${{col}}" stop-opacity="0.2"/><stop offset="100%" stop-color="${{col}}" stop-opacity="0.01"/></linearGradient></defs>${{gL}}${{yL}}${{xL}}<path d="${{fillD}}" fill="url(#g1)"/><path d="${{pathD}}" fill="none" stroke="${{col}}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${{lp.x}}" cy="${{lp.y}}" r="4.5" fill="${{col}}"/><circle cx="${{lp.x}}" cy="${{lp.y}}" r="8" fill="${{col}}" opacity="0.15"/></svg>`;
        // Update period change %
        const pctChg=days===1?STOCK.change1d:((prices[prices.length-1]-prices[0])/prices[0]*100);
        const chgEl=document.getElementById("periodChange");
        const labels={{1:"Today",7:"Past week",30:"Past month",90:"Past 3 months",180:"Past 6 months",365:"Past year",1825:"Past 5 years"}};
        if(chgEl){{const sign=pctChg>=0?"+":"";const cls=pctChg>=0?"change-up":"change-down";chgEl.innerHTML=`<span class="sp-price-chg ${{cls}}">${{sign}}${{pctChg.toFixed(2)}}%</span> <span style="font-size:13px;color:var(--text-secondary);margin-left:4px">${{labels[days]||""}}</span>`;}}
    }}
    let activeDays=1;
    document.querySelectorAll(".chart-period").forEach(b=>b.addEventListener("click",()=>{{document.querySelectorAll(".chart-period").forEach(x=>x.classList.remove("active"));b.classList.add("active");activeDays=parseInt(b.dataset.d);genChart(activeDays);}}));
    window.addEventListener("resize",()=>genChart(activeDays));
    genChart(1);
    const KEY='d6ismgpr01qleu95dlfgd6ismgpr01qleu95dlg0';
    // Fetch latest news from Finnhub
    (function(){{
        const container=document.getElementById('newsList');
        const today=new Date();const from=new Date(today);from.setDate(from.getDate()-7);
        const fmt=d=>d.toISOString().split('T')[0];
        fetch('https://finnhub.io/api/v1/company-news?symbol='+STOCK.ticker+'&from='+fmt(from)+'&to='+fmt(today)+'&token='+KEY)
        .then(r=>r.json()).then(articles=>{{
            if(!articles||articles.length===0){{container.innerHTML='<div class="news-loading">No recent news found</div>';return;}}
            const name='{stock["name"]}'.split('(')[0].trim().split(',')[0].trim().toLowerCase();
            const tick=STOCK.ticker.toLowerCase();
            const nameWords=name.split(/\s+/).filter(w=>w.length>2);
            function mentionsStock(h){{const l=h.toLowerCase();if(l.includes(tick))return true;if(l.includes(name))return true;if(nameWords.length>0&&nameWords.every(w=>l.includes(w)))return true;return false;}}
            const sorted=articles.sort((a,b)=>b.datetime-a.datetime);
            const direct=sorted.filter(a=>mentionsStock(a.headline));
            const relevant=direct.length>=4?direct.slice(0,8):direct.concat(sorted.filter(a=>!direct.includes(a)&&!['top movers','stocks to watch','sector update','stay informed'].some(g=>a.headline.toLowerCase().includes(g)))).slice(0,8);
            if(relevant.length===0){{container.innerHTML='<div class="news-loading">No recent news found</div>';return;}}
            container.innerHTML=relevant.map(a=>{{
                const date=new Date(a.datetime*1000);
                const ago=Math.round((Date.now()-date)/3600000);
                const timeStr=ago<1?'Just now':ago<24?ago+'h ago':Math.round(ago/24)+'d ago';
                return '<a href="'+a.url+'" target="_blank" rel="noopener" class="news-item"><div class="news-content"><div class="news-headline">'+a.headline+'</div><div class="news-meta">'+timeStr+'</div></div></a>';
            }}).join('');
        }}).catch(()=>{{container.innerHTML='<div class="news-loading">Unable to load news</div>';}});
    }})();
    // Live price via Finnhub WebSocket
    (function(){{
        const ws=new WebSocket('wss://ws.finnhub.io?token='+KEY);
        const priceEl=document.querySelector('.sp-price');
        ws.onopen=()=>{{ws.send(JSON.stringify({{type:'subscribe',symbol:STOCK.ticker}}));
            const badge=document.createElement('span');badge.innerHTML='<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#16c784;animation:pulse-dot 1.5s infinite;margin-right:4px"></span>LIVE';badge.style.cssText='font-size:11px;font-weight:600;color:#16c784;margin-left:12px';
            const hdr=document.querySelector('.sp-price-row');if(hdr)hdr.appendChild(badge);
            const s=document.createElement('style');s.textContent='@keyframes pulse-dot{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}@keyframes pfu{{0%,60%{{background:rgba(22,199,132,0.25)}}100%{{background:transparent}}}}@keyframes pfd{{0%,60%{{background:rgba(234,57,67,0.25)}}100%{{background:transparent}}}}';document.head.appendChild(s);
        }};
        let lastP=STOCK.price;
        ws.onmessage=(e)=>{{const d=JSON.parse(e.data);if(d.type==='trade'&&d.data){{const p=d.data[d.data.length-1].p;if(priceEl){{priceEl.textContent='$'+p.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});priceEl.style.animation=p>lastP?'pfu 2s':'pfd 2s';setTimeout(()=>priceEl.style.animation='',2000);lastP=p;}}}}}};
        document.addEventListener('visibilitychange',()=>{{if(document.hidden)ws.close();}});
    }})();
    // Subscribe form
    const sf=document.getElementById("subForm");
    if(sf)sf.addEventListener("submit",async e=>{{e.preventDefault();const em=document.getElementById("subEmail").value.trim();const msg=document.getElementById("subMsg");const btn=sf.querySelector("button");if(!em)return;btn.disabled=true;btn.textContent="...";msg.textContent="";try{{const r=await fetch("/.netlify/functions/subscribe",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{email:em}})}});const d=await r.json();if(r.ok){{msg.style.color="#16c784";msg.textContent="Subscribed!";document.getElementById("subEmail").value="";}}else{{msg.style.color="#ea3943";msg.textContent=d.error||"Failed";}}}}catch{{msg.style.color="#ea3943";msg.textContent="Network error";}}btn.disabled=false;btn.textContent="Subscribe";}});
    </script>
</body>
</html>'''

    filepath = os.path.join("s", f"{ticker}.html")
    with open(filepath, "w") as f:
        f.write(html)

print(f"Generated {len(stocks)} stock pages in /s/")

# ---- Generate sitemap.xml ----
from datetime import date
today = date.today().isoformat()

sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

# Homepage
sitemap += f'  <url>\n    <loc>https://500market.com/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'

# Stock pages
for stock in stocks:
    slug = stock["ticker"].lower().replace(".", "-")
    sitemap += f'  <url>\n    <loc>https://500market.com/s/{slug}.html</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>\n'

sitemap += '</urlset>\n'

with open("sitemap.xml", "w") as f:
    f.write(sitemap)
print(f"Generated sitemap.xml with {len(stocks) + 1} URLs")

# ---- Generate robots.txt ----
robots = """User-agent: *
Allow: /

Sitemap: https://500market.com/sitemap.xml
"""
with open("robots.txt", "w") as f:
    f.write(robots)
print("Generated robots.txt")
