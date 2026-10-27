import base64
import json
import os
import ssl
import sys
import urllib.request
import firebase_admin
from firebase_admin import credentials, messaging

# ==========================================
# 1. Firebase Authentication Setup
# ==========================================
firebase_ready = False
raw_secret = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()

if raw_secret:
  try:
    try:
      decoded = base64.b64decode(raw_secret).decode("utf-8").strip()
      cred_dict = json.loads(decoded)
    except Exception:
      cred_dict = json.loads(raw_secret)

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    firebase_ready = True
    print("[INIT] Firebase authenticated successfully.")
  except Exception as e:
    print(
        f"[WARN] Firebase credential parse error: {e}. Running in dry-run mode."
    )
else:
  print(
      "[INFO] FIREBASE_SERVICE_ACCOUNT is empty or unmapped. Running dry-run"
      " scan."
  )

# ==========================================
# 2. Watchlist & Analytical Profiles (gem.json)
# ==========================================
PSE_WATCHLIST = {
    "ALI": {
        "name": "Ayala Land, Inc.",
        "support": 14.80,
        "resistance": 17.50,
        "pe": "6.9x",
        "pb": "0.6x",
        "sector": "Real Estate / Property Development",
        "catalysts": (
            "Commercial leasing foot-traffic recovery and premium residential"
            " sales."
        ),
        "risks": (
            "Interest rate sensitivity and elevated construction input costs."
        ),
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "support": 110.00,
        "resistance": 125.00,
        "pe": "11.5x",
        "pb": "1.0x",
        "sector": "Financials / Banking",
        "catalysts": (
            "Net interest margin resilience and sustained enterprise loan"
            " growth."
        ),
        "risks": (
            "Consumer borrower asset quality if policy rates stay elevated."
        ),
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "support": 92.00,
        "resistance": 110.00,
        "pe": "14.7x",
        "pb": "1.2x",
        "sector": "Financials / Banking",
        "catalysts": (
            "Robinsons Bank merger synergies and digital retail deposit growth."
        ),
        "risks": "Deposit repricing competition pressuring near-term spreads.",
    },
    "ICT": {
        "name": "Intl Container Terminal Services",
        "support": 810.00,
        "resistance": 890.00,
        "pe": "19.5x",
        "pb": "3.5x",
        "sector": "Industrials / Port Logistics",
        "catalysts": (
            "Global trade volume expansion and USD-pegged terminal tariff"
            " contracts."
        ),
        "risks": (
            "Geopolitical trade route disruptions and concession capex costs."
        ),
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "support": 15.40,
        "resistance": 18.50,
        "pe": "13.0x",
        "pb": "1.1x",
        "sector": "Real Estate / Malls & Retail",
        "catalysts": (
            "Provincial shopping mall foot traffic and index-linked lease"
            " escalations."
        ),
        "risks": (
            "Consumer discretionary spending shifts and development debt"
            " service."
        ),
    },
    "SM": {
        "name": "SM Investments Corp.",
        "support": 510.00,
        "resistance": 580.00,
        "pe": "13.8x",
        "pb": "1.3x",
        "sector": "Holding Firms / Conglomerates",
        "catalysts": (
            "Conglomerate proxy across core retail, banking, and commercial"
            " property."
        ),
        "risks": (
            "Lingering inflation pressure on household shopping budgets."
        ),
    },
    "AC": {
        "name": "Ayala Corporation",
        "support": 520.00,
        "resistance": 590.00,
        "pe": "9.8x",
        "pb": "0.8x",
        "sector": "Holding Firms / Conglomerates",
        "catalysts": (
            "Renewable power capacity expansion (ACEN) and portfolio asset"
            " recycling."
        ),
        "risks": (
            "Holding company net asset value discount and capital commitment"
            " costs."
        ),
    },
    "GLO": {
        "name": "Globe Telecom",
        "support": 1450.00,
        "resistance": 1650.00,
        "pe": "9.3x",
        "pb": "1.8x",
        "sector": "Telecommunications",
        "catalysts": (
            "GCash equity monetization and defensive common dividend yields."
        ),
        "risks": (
            "Network infrastructure depreciation expenses and mobile prepaid"
            " churn."
        ),
    },
    "TEL": {
        "name": "PLDT Inc.",
        "support": 1150.00,
        "resistance": 1300.00,
        "pe": "11.4x",
        "pb": "1.4x",
        "sector": "Telecommunications",
        "catalysts": (
            "Enterprise data center expansion and disciplined capex tapering."
        ),
        "risks": (
            "Fiber broadband pricing competition and debt balance sheet"
            " servicing."
        ),
    },
    "MBT": {
        "name": "Metropolitan Bank & Trust Co.",
        "support": 58.00,
        "resistance": 66.00,
        "pe": "9.6x",
        "pb": "0.7x",
        "sector": "Financials / Banking",
        "catalysts": (
            "Industry-leading Tier-1 capital adequacy and special dividend"
            " upside."
        ),
        "risks": (
            "Wholesale corporate loan demand deceleration under macro"
            " headwinds."
        ),
    },
    "MER": {
        "name": "Manila Electric Company",
        "support": 410.00,
        "resistance": 450.00,
        "pe": "20.5x",
        "pb": "1.9x",
        "sector": "Utilities / Power Distribution",
        "catalysts": (
            "Guaranteed rate base distribution cash flows and energy demand"
            " resilience."
        ),
        "risks": (
            "Regulatory tariff review scrutiny and volatile global fuel"
            " pass-throughs."
        ),
    },
    "MONDE": {
        "name": "Monde Nissin",
        "support": 8.50,
        "resistance": 10.20,
        "pe": "15.0x",
        "pb": "2.2x",
        "sector": "Consumer Staples / Food",
        "catalysts": (
            "Dominant packaged noodle market share and volume consumption"
            " stability."
        ),
        "risks": (
            "Meat alternative restructuring charges and wheat/oil cost swings."
        ),
    },
    "JFC": {
        "name": "Jollibee Foods Corporation",
        "support": 135.00,
        "resistance": 160.00,
        "pe": "23.8x",
        "pb": "3.1x",
        "sector": "Consumer Discretionary / Restaurants",
        "catalysts": (
            "International store footprint rollout and overseas brand operating"
            " leverage."
        ),
        "risks": (
            "International store integration overhead and foreign wage"
            " pressures."
        ),
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "support": 36.00,
        "resistance": 42.00,
        "pe": "16.8x",
        "pb": "0.8x",
        "sector": "Consumer Staples / Retail",
        "catalysts": (
            "Resilient essential consumer grocery demand and store clustering."
        ),
        "risks": (
            "Neighborhood competition from hard discount grocery competitors."
        ),
    },
}

# ==========================================
# 3. Direct TradingView PSE Scanner API Feed
# ==========================================
ctx = ssl._create_unverified_context()


def fetch_pse_market_data():
  """Fetches live prices and indicators directly from TradingView's PSE scanner."""
  url = "https://scanner.tradingview.com/philippines/scan"
  tickers = [f"PSE:{t}" for t in PSE_WATCHLIST.keys()]

  payload = {
      "symbols": {"tickers": tickers},
      "columns": ["close", "change", "volume", "RSI", "SMA20", "SMA50"],
  }

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Origin": "https://www.tradingview.com",
      "Referer": "https://www.tradingview.com/",
      "Content-Type": "application/json",
      "Accept": "application/json",
  }

  results = {}
  try:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
      if resp.status == 200:
        data = json.loads(resp.read().decode("utf-8"))
        for item in data.get("data", []):
          sym = item.get("s", "").replace("PSE:", "")
          vals = item.get("d", [])
          if len(vals) >= 6 and vals[0] is not None:
            results[sym] = {
                "price": float(vals[0]),
                "change": float(vals[1]) if vals[1] is not None else 0.0,
                "volume": float(vals[2]) if vals[2] is not None else 0.0,
                "rsi": float(vals[3]) if vals[3] is not None else 50.0,
                "ma20": float(vals[4]) if vals[4] is not None else vals[0],
                "ma50": float(vals[5]) if vals[5] is not None else vals[0],
            }
  except Exception as e:
    print(f"[API ERROR] TradingView Scanner request failed: {e}")

  return results


# ==========================================
# 4. Push Notification Dispatcher
# ==========================================
def dispatch_analyst_alert(
    ticker: str, zone_type: str, price: float, rsi: float, meta: dict
):
  name = meta["name"]
  support = meta["support"]
  resistance = meta["resistance"]
  pe = meta["pe"]

  if zone_type == "ACCUMULATION":
    title = f"🟢 Accumulation Zone: {ticker} (₱{price:.2f})"
    body = (
        f"{name} is trading near structural support (₱{support:.2f}). RSI:"
        f" {rsi:.1f}. Valuation: P/E {pe}. Analytical reference point only;"
        " not financial advice."
    )
  else:
    title = f"🔴 Profit-Taking Zone: {ticker} (₱{price:.2f})"
    body = (
        f"{name} is approaching resistance (₱{resistance:.2f}). RSI:"
        f" {rsi:.1f}. Valuation: P/E {pe}. Analytical reference point only;"
        " not financial advice."
    )

  print(f"\n[ALERT GENERATED]\nTitle: {title}\nBody:  {body}\n")

  if not firebase_ready:
    print(f"[DRY-RUN] Push skipped for {ticker} (Firebase not initialized).")
    return

  try:
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic="pse_alerts",
    )
    msg_id = messaging.send(message)
    print(f"[FCM] Push dispatched successfully (ID: {msg_id})")
  except Exception as err:
    print(f"[FCM ERROR] Alert dispatch failed for {ticker}: {err}")


# ==========================================
# 5. Core Analytical Engine Loop
# ==========================================
def run_scanner():
  print("=" * 85)
  print(
      f"[SCAN] Initializing market analysis for {len(PSE_WATCHLIST)} PSE"
      " blue-chips..."
  )
  print("=" * 85)

  quotes = fetch_pse_market_data()
  evaluated = 0

  for sym, meta in PSE_WATCHLIST.items():
    stock_data = quotes.get(sym)

    if not stock_data or stock_data["price"] <= 0:
      print(f"[-] {sym:<6} | Data not returned by market feed. Skipping.")
      continue

    evaluated += 1
    price = stock_data["price"]
    rsi = stock_data["rsi"]
    ma20 = stock_data["ma20"]
    ma50 = stock_data["ma50"]
    support = meta["support"]
    resistance = meta["resistance"]
    pe = meta["pe"]

    # Zone calculation based on gem.json rules: within 2.5% of reference levels
    in_buy_zone = (support * 0.98) <= price <= (support * 1.025)
    in_sell_zone = (resistance * 0.975) <= price <= (resistance * 1.02)

    status_tag = "[NEUTRAL]"
    if in_buy_zone:
      status_tag = "[ACCUMULATION ZONE]"
    elif in_sell_zone:
      status_tag = "[PROFIT-TAKING ZONE]"

    trend = (
        "Above MA20/MA50"
        if price >= ma20 and price >= ma50
        else "Below MA20/MA50"
    )

    print(
        f"{status_tag:<21} {sym:<5} | Price: ₱{price:>7.2f} | Supp:"
        f" ₱{support:>7.2f} | Res: ₱{resistance:>7.2f} | RSI: {rsi:>4.1f} |"
        f" P/E: {pe:<5} | Trend: {trend}"
    )

    if in_buy_zone:
      dispatch_analyst_alert(sym, "ACCUMULATION", price, rsi, meta)
    elif in_sell_zone:
      dispatch_analyst_alert(sym, "PROFIT_TAKING", price, rsi, meta)

  print("=" * 85)
  print(
      f"[COMPLETED] Successfully processed {evaluated}/{len(PSE_WATCHLIST)} PSE"
      " stocks."
  )
  print("=" * 85)


if __name__ == "__main__":
  run_scanner()
