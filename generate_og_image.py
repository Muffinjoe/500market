#!/usr/bin/env python3
"""Generate OG image for social sharing."""
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    with open("market_summary.json") as f:
        ms = json.load(f)
    idx = ms["index"]
    price = f'{idx["price"]:,.2f}'
    sign = "+" if idx["changePct"] >= 0 else ""
    change = f'{sign}{idx["changePct"]:.2f}%'
    color = "#16c784" if idx["changePct"] >= 0 else "#ea3943"
except:
    price = "—"
    change = "—"
    color = "#8b949e"

svg = f'''<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <rect width="1200" height="630" fill="#1a1a2e"/>
  <rect width="1200" height="80" fill="#3861FB"/>
  <text x="40" y="52" fill="white" font-size="32" font-weight="700" font-family="system-ui,sans-serif">500Market</text>
  <text x="1160" y="52" fill="rgba(255,255,255,0.6)" font-size="20" font-weight="400" font-family="system-ui,sans-serif" text-anchor="end">S&amp;P 500 Stock Tracker</text>

  <text x="40" y="180" fill="#8b949e" font-size="22" font-family="system-ui,sans-serif">S&amp;P 500 Index</text>
  <text x="40" y="250" fill="white" font-size="72" font-weight="800" font-family="system-ui,sans-serif">{price}</text>
  <text x="40" y="300" fill="{color}" font-size="36" font-weight="700" font-family="system-ui,sans-serif">{change}</text>

  <text x="40" y="390" fill="#8b949e" font-size="20" font-family="system-ui,sans-serif">503 stocks · 11 sectors · Live prices · Daily market brief</text>

  <rect x="40" y="440" width="280" height="50" rx="8" fill="#3861FB"/>
  <text x="180" y="472" fill="white" font-size="18" font-weight="600" font-family="system-ui,sans-serif" text-anchor="middle">Track S&amp;P 500 Free</text>

  <rect y="600" width="1200" height="30" fill="#16213e"/>
  <text x="600" y="622" fill="#8b949e" font-size="14" font-family="system-ui,sans-serif" text-anchor="middle">500market.com · Free real-time S&amp;P 500 data</text>
</svg>'''

with open("og-image.svg", "w") as f:
    f.write(svg)
print("Generated og-image.svg")

# Try to convert to PNG if possible
try:
    import subprocess
    # Use rsvg-convert if available, otherwise try ImageMagick
    result = subprocess.run(["which", "rsvg-convert"], capture_output=True)
    if result.returncode == 0:
        subprocess.run(["rsvg-convert", "og-image.svg", "-o", "og-image.png", "-w", "1200", "-h", "630"])
        print("Generated og-image.png")
    else:
        result = subprocess.run(["which", "convert"], capture_output=True)
        if result.returncode == 0:
            subprocess.run(["convert", "og-image.svg", "-resize", "1200x630", "og-image.png"])
            print("Generated og-image.png")
        else:
            print("  Note: Install rsvg-convert or ImageMagick to generate PNG. Using SVG for now.")
except:
    pass
