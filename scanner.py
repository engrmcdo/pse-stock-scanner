import base64
import json
import os
import ssl
import time
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
    print(f"[WARN] Firebase credential parse error: {e}. Running in dry-run mode.")
else:
  print("[INFO] FIREBASE_SERVICE_ACCOUNT is empty or unmapped. Running dry-run scan.")

# ==========================================
# 2. Watchlist & Analytical Profiles (gem.json)
# ==========================================
PSE_WATCHLIST = {
    "ALI": {
        "name": "Ayala Land, Inc.",
        "support": 14.80,
        "resistance": 17.50,
        "ma20": 15.60,
        "ma50": 16.20,
        "pe": "6.9x",
        "pb": "0.6x",
        "catalysts": "Commercial leasing revenue recovery and resilient residential reservations.",
        "risks": "Interest rate sensitivity and elevated construction input costs.",
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "support": 110.00,
        "resistance": 125.00,
        "ma20": 114.50,
        "ma50": 116.00,
        "pe": "11.5x",
        "pb": "1.0x",
        "catalysts": "Net interest margin resilience and sustained enterprise loan growth.",
        "risks": "Consumer borrower credit risk if policy rates remain elevated.",
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "support": 92.00,
        "resistance": 110.00,
        "ma20": 101.00,
        "ma50": 104.50,
        "pe": "14.7x",
        "pb": "1.2x",
        "catalysts": "Robinsons Bank merger synergies and digital customer expansion.",
        "risks": "Deposit repricing competition pressuring near-term spreads.",
    },
    "ICT": {
        "name": "Intl Container Terminal Services",
        "support": 810.00,
        "resistance": 890.00,
        "ma20": 845.00,
        "ma50": 830.00,
        "pe": "19.5x",
        "pb": "3.5x",
        "catalysts": "Global trade volume expansion and USD-pegged terminal tariff contracts.",
        "risks": "Geopolitical disruptions and international capex financing costs.",
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "support": 15.40,
        "resistance": 18.50,
        "ma20": 16.40,
        "ma50": 17.10,
        "pe": "13.0x",
        "pb": "1.1x",
        "catalysts": "Provincial shopping mall foot traffic and index-linked lease escalations.",
        "risks": "Consumer discretionary spending shifts and development debt service.",
    },
    "SM": {
        "name": "SM Investments Corp.",
        "support": 510.00,
        "resistance": 580.00,
        "ma20": 535.00,
        "ma50": 550.00,
        "pe": "13.8x",
        "pb": "1.3x",
        "catalysts": "Conglomerate proxy across core retail, banking, and commercial property.",
        "risks": "Lingering inflation pressure on household discretionary spending.",
    },
    "AC": {
        "name": "Ayala Corporation",
        "support": 520.00,
        "resistance": 590.00,
        "ma20": 545.00,
        "ma50": 565.00,
        "pe": "9.8x",
        "pb": "0.8x",
        "catalysts": "Renewable power capacity expansion (ACEN) and portfolio asset recycling.",
        "risks": "Holding company net asset value discount and capital commitment costs.",
    },
    "GLO": {
        "name": "Globe Telecom",
        "support": 1450.00,
        "resistance": 1650.00,
        "ma20": 1520.00,
        "ma50": 1570.00,
        "pe": "9.3x",
        "pb": "1.8x",
        "catalysts": "GCash equity monetization and defensive common dividend yields.",
        "risks": "Network infrastructure depreciation expenses and mobile prepaid churn.",
    },
    "TEL": {
        "name": "PLDT Inc.",
        "support": 1150.00,
        "resistance": 1300.00,
        "ma20": 1210.00,
        "ma50": 1240.00,
        "pe": "11.4x",
        "pb": "1.4x",
        "catalysts": "Enterprise data center expansion and disciplined capex tapering.",
        "risks": "Fiber broadband pricing competition and debt balance sheet servicing.",
    },
    "MBT": {
        "name": "Metropolitan Bank & Trust Co.",
        "support": 58.00,
        "resistance": 66.00,
        "ma20": 61.00,
        "ma50": 62.50,
        "pe": "9.6x",
        "pb": "0.7x",
        "catalysts": "Industry-leading Tier-1 capital adequacy and special dividend upside.",
        "risks": "Wholesale corporate loan demand deceleration under macro headwinds.",
    },
    "MER": {
        "name": "Manila Electric Company",
        "support": 410.00,
        "resistance": 450.00,
        "ma20": 425.00,
        "ma50": 418.00,
        "pe": "20.5x",
        "pb": "1.9x",
        "catalysts": "Guaranteed rate base distribution cash flows and energy demand resilience.",
        "risks": "Regulatory tariff review scrutiny and volatile global fuel pass-throughs.",
    },
    "MONDE": {
        "name": "Monde Nissin",
        "support": 8.50,
        "resistance": 10.20,
        "ma20": 9.10,
        "ma50": 9.40,
        "pe": "15.0x",
        "pb": "2.2x",
        "catalysts": "Dominant packaged noodle market share and volume consumption stability.",
        "risks": "Meat alternative restructuring charges and wheat/oil cost swings.",
    },
    "JFC": {
        "name": "Jollibee Foods Corporation",
        "support": 135.00,
        "resistance": 160.00,
        "ma20": 144.00,
        "ma50": 150.00,
        "pe": "23.8x",
        "pb": "3.1x",
        "catalysts": "International store footprint rollout and overseas brand operating leverage.",
        "risks": "International store integration overhead and foreign wage pressures.",
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "support": 36.00,
        "resistance": 42.00,
        "ma20": 38.00,
        "ma50": 39.20,
        "pe": "16.8x",
        "pb": "0.8x",
        "catalysts": "Resilient essential consumer grocery demand and store clustering.",
        "risks": "Neighborhood competition from hard discount grocery competitors.",
    },
}

# ==========================================
# 3. Cloud-Friendly Quote Retrieval Engine
# ==========================================
ctx = ssl._create_unverified_context()

def get_live_pse_quote(ticker: str):
  """Fetches quote using WallStreetZen search endpoint with a fallback to AlphaVantage/Yahoo API."""
  # Source 1: Direct JSON quote endpoint
  url = f"https://api.wallstreetzen.com/api/v1/search?query=PSE:{ticker}"
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      "Accept": "application/json",
  }
  try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
      if resp.status == 200:
        data = json.loads(resp.read().decode("utf-8"))
        for entry in data.get("data", []):
          if entry.get("ticker") == ticker or entry.get("symbol") == f"PSE:{ticker}":
            price = entry.get("price") or entry.get("close")
            if price and float(price) > 0:
              return float(price)
  except Exception:
    pass

  # Source 2: Direct Yahoo Finance Query API with randomized user context
  url_yf = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.PS"
  headers_yf = {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
      "Accept": "*/*",
  }
  try:
    req = urllib.request.Request(url_yf, headers=headers_yf)
    with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
      if resp.status == 200:
        data = json.loads(resp.read().decode("utf-8"))
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        if price and float(price) > 0:
          return float(price)
  except Exception:
    pass

  return None

# ==========================================
# 4. Push Notification Dispatcher
# ==========================================
def dispatch_analyst_alert(ticker: str, zone_type: str, price: float, meta: dict):
  name = meta["name"]
  support = meta["support"]
  resistance = meta["resistance"]
  pe = meta["pe"]

  if zone_type == "ACCUMULATION":
    title = f"🟢 Accumulation Zone: {ticker} (₱{price:.2f})"
    body = (
        f"{name} is trading near structural support (₱{support:.2f}). "
        f"Valuation: P/E {pe}. "
        f"Analytical reference point only; not financial advice."
    )
  else:
    title = f"🔴 Profit-Taking Zone: {ticker} (₱{price:.2f})"
    body = (
        f"{name} is approaching resistance (₱{resistance:.2f}). "
        f"Valuation: P/E {pe}. "
        f"Analytical reference point only; not financial advice."
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
  print("=" * 80)
  print(f"[SCAN] Initializing market analysis for {len(PSE_WATCHLIST)} PSE blue-chips...")
  print("=" * 80)

  evaluated = 0

  for sym, meta in PSE_WATCHLIST.items():
    price = get_live_pse_quote(sym)
    time.sleep(0.3)

    if price is None or price <= 0:
      print(f"[-] {sym:<6} | Quote feed temporarily unavailable. Skipping.")
      continue

    evaluated += 1
    support = meta["support"]
    resistance = meta["resistance"]
    ma20 = meta["ma20"]
    ma50 = meta["ma50"]
    pe = meta["pe"]

    # Zone calculation based on gem.json rules: within 2.5% of structural levels
    in_buy_zone = (support * 0.98) <= price <= (support * 1.025)
    in_sell_zone = (resistance * 0.975) <= price <= (resistance * 1.02)

    status_tag = "[NEUTRAL]"
    if in_buy_zone:
      status_tag = "[ACCUMULATION ZONE]"
    elif in_sell_zone:
      status_tag = "[PROFIT-TAKING ZONE]"

    trend = "Above MAs" if price > ma20 and price > ma50 else "Below MAs"

    print(
        f"{status_tag:<21} {sym:<5} | Price: ₱{price:>7.2f} | "
        f"Supp: ₱{support:>7.2f} | Res: ₱{resistance:>7.2f} | "
        f"P/E: {pe:<5} | Trend: {trend}"
    )

    if in_buy_zone:
      dispatch_analyst_alert(sym, "ACCUMULATION", price, meta)
    elif in_sell_zone:
      dispatch_analyst_alert(sym, "PROFIT_TAKING", price, meta)

  print("=" * 80)
  print(f"[COMPLETED] Successfully processed {evaluated}/{len(PSE_WATCHLIST)} PSE stocks.")
  print("=" * 80)

if __name__ == "__main__":
  run_scanner()
