#!/usr/bin/env python3
"""
Send daily S&P 500 market brief email via Resend.
Run: python3 send_daily_email.py

Reads market_summary.json and data.json to build the email.
"""

import json, os, sys, subprocess
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
if not RESEND_API_KEY:
    print("Warning: RESEND_API_KEY not set. Skipping email.")
    sys.exit(0)
FROM_EMAIL = "500Market <updates@500market.com>"
AUDIENCE_ID = "14fe5f34-8795-40c8-8abe-7e32c084b211"

# Load data
with open("market_summary.json", "r") as f:
    summary = json.load(f)

with open("data.json", "r") as f:
    stocks = json.load(f)

idx = summary["index"]
today = datetime.now().strftime("%A, %B %d, %Y")

# Top movers
sorted_by_change = sorted(stocks, key=lambda s: s["change1d"], reverse=True)
top_gainers = sorted_by_change[:5]
top_losers = sorted_by_change[-5:][::-1]

# Sector performance
sectors = {}
for s in stocks:
    sec = s["sector"]
    if sec not in sectors:
        sectors[sec] = []
    sectors[sec].append(s["change1d"])

sector_perf = []
for name, changes in sectors.items():
    avg = sum(changes) / len(changes)
    sector_perf.append({"name": name, "avg": avg, "count": len(changes)})
sector_perf.sort(key=lambda x: x["avg"], reverse=True)

# 52-week high names (top 5 by market cap)
high_stocks = []
for s in stocks:
    if s["change1d"] > 0 and s.get("changeYtd", 0) > 10:
        high_stocks.append(s)
high_stocks.sort(key=lambda x: x["marketCap"], reverse=True)
high_names = high_stocks[:5]

def fmt_mcap(n):
    if n >= 1e12: return f"${n/1e12:.1f}T"
    if n >= 1e9: return f"${n/1e9:.1f}B"
    return f"${n/1e6:.0f}M"

def fmt_price(n):
    return f"${n:,.2f}"

def chg_color(v):
    return "#16c784" if v >= 0 else "#ea3943"

def chg_arrow(v):
    return "▲" if v >= 0 else "▼"

def chg_str(v):
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"

# Fear & Greed color
fg = summary["fearGreed"]
if fg >= 75: fg_color = "#16c784"
elif fg >= 55: fg_color = "#16c784"
elif fg >= 45: fg_color = "#f7931a"
elif fg >= 25: fg_color = "#ea3943"
else: fg_color = "#ea3943"

# Build mover rows with logos and visual bars
def mover_rows(movers):
    rows = ""
    for i, s in enumerate(movers):
        color = chg_color(s["change1d"])
        bg_color = "#f0fdf4" if s["change1d"] >= 0 else "#fef2f2"
        bar_width = min(80, abs(s["change1d"]) * 6)
        logo = f'https://www.google.com/s2/favicons?domain={s.get("domain", "")}&sz=64'
        mcap = fmt_mcap(s["marketCap"])
        rows += f'''
        <tr>
            <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#999;text-align:center;width:28px">{i+1}</td>
            <td style="padding:10px 0;border-bottom:1px solid #f0f0f0;width:32px">
                <img src="{logo}" alt="{s["ticker"]}" width="24" height="24" style="border-radius:50%;vertical-align:middle;border:1px solid #eee">
            </td>
            <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0">
                <strong style="color:#222;font-size:14px">{s["ticker"]}</strong>
                <span style="color:#999;font-size:12px;margin-left:4px">{s["name"]}</span><br>
                <span style="color:#bbb;font-size:11px">{mcap}</span>
            </td>
            <td style="padding:10px 8px;border-bottom:1px solid #f0f0f0;text-align:right;font-weight:600;color:#222;font-size:14px">{fmt_price(s["price"])}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:right;width:120px">
                <div style="font-weight:700;color:{color};font-size:14px">{chg_arrow(s["change1d"])} {chg_str(s["change1d"])}</div>
                <div style="margin-top:4px;height:4px;background:#f0f0f0;border-radius:2px;overflow:hidden">
                    <div style="width:{bar_width}%;height:100%;background:{color};border-radius:2px"></div>
                </div>
            </td>
        </tr>'''
    return rows

# Build sector rows with visual bars
SECTOR_ICONS = {
    "Information Technology": "💻", "Health Care": "🏥", "Financials": "🏦",
    "Consumer Discretionary": "🛍️", "Communication Services": "📡",
    "Industrials": "🏭", "Consumer Staples": "🛒", "Energy": "⛽",
    "Utilities": "💡", "Real Estate": "🏠", "Materials": "⛏️",
}

def sector_rows():
    rows = ""
    for sp in sector_perf:
        color = chg_color(sp["avg"])
        bar_width = min(80, abs(sp["avg"]) * 15)
        icon = SECTOR_ICONS.get(sp["name"], "📊")
        rows += f'''
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:14px;color:#222;font-weight:500">
                {icon} {sp["name"]}
            </td>
            <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:12px;color:#999">{sp["count"]}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right;width:100px">
                <div style="font-weight:700;color:{color};font-size:13px">{chg_str(sp["avg"])}</div>
                <div style="margin-top:3px;height:3px;background:#f0f0f0;border-radius:2px;overflow:hidden">
                    <div style="width:{bar_width}%;height:100%;background:{color};border-radius:2px;float:{"left" if sp["avg"] >= 0 else "right"}"></div>
                </div>
            </td>
        </tr>'''
    return rows

idx_color = chg_color(idx["changePct"])
idx_sign = "+" if idx["changePct"] >= 0 else ""
ytd_color = chg_color(idx["ytd"])
ytd_sign = "+" if idx["ytd"] >= 0 else ""

html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<div style="max-width:600px;margin:0 auto;background:#ffffff">

    <!-- Header -->
    <div style="background:#3861FB;padding:24px 32px;text-align:center">
        <div style="font-size:24px;font-weight:800;color:#fff;letter-spacing:-0.5px">500Market</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.7);margin-top:4px">Daily Market Brief</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-top:2px">{today}</div>
    </div>

    <!-- S&P 500 Index -->
    <div style="padding:24px 32px;text-align:center;border-bottom:1px solid #f0f0f0">
        <div style="font-size:12px;color:#999;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">S&P 500 Index</div>
        <div style="font-size:36px;font-weight:800;color:#222;line-height:1">{idx["price"]:,.2f}</div>
        <div style="font-size:18px;font-weight:600;color:{idx_color};margin-top:6px">
            {idx_sign}{idx["change"]:.2f} ({idx_sign}{idx["changePct"]:.2f}%)
        </div>
        <div style="display:inline-block;margin-top:12px">
            <table style="border-collapse:collapse;margin:0 auto">
                <tr>
                    <td style="padding:4px 16px;text-align:center">
                        <div style="font-size:11px;color:#999">OPEN</div>
                        <div style="font-size:13px;font-weight:600;color:#222">{idx["open"]:,.2f}</div>
                    </td>
                    <td style="padding:4px 16px;text-align:center;border-left:1px solid #eee;border-right:1px solid #eee">
                        <div style="font-size:11px;color:#999">HIGH</div>
                        <div style="font-size:13px;font-weight:600;color:#222">{idx["high"]:,.2f}</div>
                    </td>
                    <td style="padding:4px 16px;text-align:center;border-right:1px solid #eee">
                        <div style="font-size:11px;color:#999">LOW</div>
                        <div style="font-size:13px;font-weight:600;color:#222">{idx["low"]:,.2f}</div>
                    </td>
                    <td style="padding:4px 16px;text-align:center">
                        <div style="font-size:11px;color:#999">YTD</div>
                        <div style="font-size:13px;font-weight:600;color:{ytd_color}">{ytd_sign}{idx["ytd"]:.2f}%</div>
                    </td>
                </tr>
            </table>
        </div>
    </div>

    <!-- Market Snapshot -->
    <div style="padding:20px 32px;border-bottom:1px solid #f0f0f0">
        <table style="width:100%;border-collapse:collapse">
            <tr>
                <td style="text-align:center;padding:12px">
                    <div style="font-size:28px;font-weight:800;color:{fg_color}">{fg}</div>
                    <div style="font-size:11px;color:#999;margin-top:2px">Fear & Greed</div>
                    <div style="font-size:12px;font-weight:600;color:{fg_color}">{summary["fearGreedLabel"]}</div>
                </td>
                <td style="text-align:center;padding:12px;border-left:1px solid #f0f0f0;border-right:1px solid #f0f0f0">
                    <div style="font-size:28px;font-weight:800;color:#16c784">{summary["advancing"]}</div>
                    <div style="font-size:11px;color:#999;margin-top:2px">Advancing</div>
                    <div style="font-size:12px;color:#999">{round(summary["advancing"]/len(stocks)*100)}%</div>
                </td>
                <td style="text-align:center;padding:12px;border-right:1px solid #f0f0f0">
                    <div style="font-size:28px;font-weight:800;color:#ea3943">{summary["declining"]}</div>
                    <div style="font-size:11px;color:#999;margin-top:2px">Declining</div>
                    <div style="font-size:12px;color:#999">{round(summary["declining"]/len(stocks)*100)}%</div>
                </td>
                <td style="text-align:center;padding:12px">
                    <div style="font-size:28px;font-weight:800;color:#222">{summary["high52Count"]}</div>
                    <div style="font-size:11px;color:#999;margin-top:2px">52W Highs</div>
                    <div style="font-size:12px;color:#999">Today</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Top Gainers -->
    <div style="padding:20px 32px 8px">
        <div style="font-size:14px;font-weight:700;color:#222;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px">Top Gainers</div>
        <table style="width:100%;border-collapse:collapse">
            {mover_rows(top_gainers)}
        </table>
    </div>

    <!-- Top Losers -->
    <div style="padding:16px 32px 8px">
        <div style="font-size:14px;font-weight:700;color:#222;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px">Top Losers</div>
        <table style="width:100%;border-collapse:collapse">
            {mover_rows(top_losers)}
        </table>
    </div>

    <!-- Sector Performance -->
    <div style="padding:16px 32px 8px">
        <div style="font-size:14px;font-weight:700;color:#222;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px">Sector Performance</div>
        <table style="width:100%;border-collapse:collapse">
            <tr style="background:#f8f9fa">
                <th style="padding:6px 12px;text-align:left;font-size:11px;color:#999;font-weight:600">SECTOR</th>
                <th style="padding:6px 12px;text-align:center;font-size:11px;color:#999;font-weight:600">STOCKS</th>
                <th style="padding:6px 12px;text-align:right;font-size:11px;color:#999;font-weight:600">AVG CHG</th>
            </tr>
            {sector_rows()}
        </table>
    </div>

    <!-- CTA -->
    <div style="padding:24px 32px;text-align:center">
        <a href="https://500market.com" style="display:inline-block;background:#3861FB;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">View Full Dashboard</a>
    </div>

    <!-- Notable Movers Links -->
    <div style="padding:0 32px 24px;text-align:center">
        <div style="font-size:12px;color:#999;margin-bottom:8px">Today's notable movers:</div>
        <div>
            {'  '.join([f'<a href="https://500market.com/s/{s["ticker"].lower()}.html" style="color:#3861FB;text-decoration:none;font-size:13px;font-weight:500;margin:0 6px">{s["ticker"]}</a>' for s in (top_gainers[:3] + top_losers[:2])])}
        </div>
    </div>

    <!-- Footer -->
    <div style="background:#f8f9fa;padding:20px 32px;text-align:center;border-top:1px solid #f0f0f0">
        <div style="font-size:12px;color:#999;line-height:1.6">
            500Market &mdash; S&P 500 stock tracker<br>
            Market data refreshed daily at market close<br>
            <a href="https://500market.com" style="color:#3861FB;text-decoration:none">500market.com</a>
        </div>
        <div style="font-size:11px;color:#ccc;margin-top:8px">
            Total Market Cap: {fmt_mcap(summary["totalMarketCap"])}
        </div>
    </div>

</div>
</body>
</html>'''

# Build plain text version
plain = f"""500Market — Daily Market Brief
{today}

S&P 500: {idx["price"]:,.2f} ({idx_sign}{idx["changePct"]:.2f}%)
Open: {idx["open"]:,.2f} | High: {idx["high"]:,.2f} | Low: {idx["low"]:,.2f} | YTD: {ytd_sign}{idx["ytd"]:.2f}%

Fear & Greed: {fg} ({summary["fearGreedLabel"]})
Advancing: {summary["advancing"]} | Declining: {summary["declining"]} | 52W Highs: {summary["high52Count"]}

TOP GAINERS
{chr(10).join([f"  {i+1}. {s['ticker']} ({s['name']}) — {fmt_price(s['price'])} {chg_str(s['change1d'])}" for i, s in enumerate(top_gainers)])}

TOP LOSERS
{chr(10).join([f"  {i+1}. {s['ticker']} ({s['name']}) — {fmt_price(s['price'])} {chg_str(s['change1d'])}" for i, s in enumerate(top_losers)])}

SECTOR PERFORMANCE
{chr(10).join([f"  {sp['name']}: {chg_str(sp['avg'])}" for sp in sector_perf])}

View the full dashboard: https://500market.com
"""

# Send via Resend
subject = f"{datetime.now().strftime('%b %d')} — 500Market Daily Update | S&P 500 {idx_sign}{idx['changePct']:.2f}%"

# Check for --test flag to send directly instead of broadcast
import sys as _sys
test_mode = '--test' in _sys.argv
FALLBACK_EMAIL = "joemurfin@gmail.com"

if test_mode:
    # Direct send for testing
    print(f"Sending TEST email to {FALLBACK_EMAIL}...")
    print(f"  Subject: {subject}")
    payload = json.dumps({
        "from": FROM_EMAIL,
        "to": [FALLBACK_EMAIL],
        "subject": subject,
        "html": html,
        "text": plain,
    })
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        "https://api.resend.com/emails",
        "-H", f"Authorization: Bearer {RESEND_API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", payload
    ], capture_output=True, text=True, timeout=30)
    try:
        resp = json.loads(result.stdout)
        if "id" in resp:
            print(f"  Sent! Email ID: {resp['id']}")
        else:
            print(f"  Error: {resp}")
    except:
        print(f"  Response: {result.stdout}")
else:
    # Broadcast to audience list
    print(f"Creating broadcast to audience {AUDIENCE_ID}...")
    print(f"  Subject: {subject}")

    create_payload = json.dumps({
        "from": FROM_EMAIL,
        "audience_id": AUDIENCE_ID,
        "subject": subject,
        "html": html,
        "text": plain,
        "name": f"Daily Brief — {datetime.now().strftime('%Y-%m-%d')}",
    })

    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        "https://api.resend.com/broadcasts",
        "-H", f"Authorization: Bearer {RESEND_API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", create_payload
    ], capture_output=True, text=True, timeout=30)

    broadcast_id = None
    try:
        resp = json.loads(result.stdout)
        if "id" in resp:
            broadcast_id = resp["id"]
            print(f"  Broadcast created: {broadcast_id}")
        else:
            print(f"  Error creating broadcast: {resp}")
    except:
        print(f"  Response: {result.stdout}")

    # Send the broadcast
    if broadcast_id:
        print(f"  Sending broadcast...")
        send_result = subprocess.run([
            "curl", "-s", "-X", "POST",
            f"https://api.resend.com/broadcasts/{broadcast_id}/send",
            "-H", f"Authorization: Bearer {RESEND_API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", "{}"
        ], capture_output=True, text=True, timeout=30)

        try:
            send_resp = json.loads(send_result.stdout)
            if "id" in send_resp:
                print(f"  Sent! Broadcast ID: {send_resp['id']}")
            else:
                print(f"  Send response: {send_resp}")
        except:
            print(f"  Send response: {send_result.stdout}")
