#!/usr/bin/env python3
"""
Generate company descriptions for all S&P 500 stocks using Groq API via curl.
Saves to descriptions.json.
"""

import json, time, subprocess, os, sys

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not set. Skipping description generation.")
    print("Set it with: export GROQ_API_KEY=your_key_here")
    sys.exit(0)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("data.json", "r") as f:
    stocks = json.load(f)

# Load existing descriptions if any
try:
    with open("descriptions.json", "r") as f:
        descriptions = json.load(f)
except FileNotFoundError:
    descriptions = {}

def generate_description(stock):
    prompt = f"Write a 2-3 sentence company description for {stock['name']} (ticker: {stock['ticker']}), a {stock['sector']} company in the S&P 500. Include what the company does, its key products/services, and why it matters. Factual tone like Yahoo Finance. Return ONLY the description, no quotes."

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a financial writer. Write concise, factual company descriptions. Return ONLY the description text."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 200
    })

    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        "https://api.groq.com/openai/v1/chat/completions",
        "-H", f"Authorization: Bearer {GROQ_API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", payload
    ], capture_output=True, text=True, timeout=30)

    try:
        data = json.loads(result.stdout)
        return data["choices"][0]["message"]["content"].strip().strip('"')
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"  Error: {e} - {result.stdout[:200]}")
        return None

# Generate missing descriptions
remaining = [s for s in stocks if s["ticker"] not in descriptions]
print(f"Have {len(descriptions)} descriptions, need {len(remaining)} more")

for i, stock in enumerate(remaining):
    print(f"  [{i+1}/{len(remaining)}] {stock['ticker']} - {stock['name']}...", end=" ", flush=True)
    desc = generate_description(stock)
    if desc:
        descriptions[stock["ticker"]] = desc
        print(f"OK ({len(desc)} chars)")
    else:
        print("FAILED")

    # Save after each
    with open("descriptions.json", "w") as f:
        json.dump(descriptions, f, indent=2)

    time.sleep(2)

print(f"\nDone! {len(descriptions)} total descriptions saved to descriptions.json")
