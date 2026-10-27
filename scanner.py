import ast
import base64
import json
import os
import re
import time
import urllib.request
import firebase_admin
from firebase_admin import credentials, messaging

# ==========================================
# 1. Resilient Firebase Credential Loader
# ==========================================
firebase_ready = False
raw_secret = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()


def sanitize_and_parse_credentials(secret_str: str):
  if not secret_str:
    return None

  # Strip outer wrapping quotes if added by shell or input field
  if (secret_str.startswith('"') and secret_str.endswith('"')) or (
      secret_str.startswith("'") and secret_str.endswith("'")
  ):
    secret_str = secret_str[1:-1].strip()

  # Attempt 1: Base64 decode
  try:
    decoded = base64.b64decode(secret_str).decode("utf-8").strip()
    try:
      return json.loads(decoded)
    except Exception:
      return ast.literal_eval(decoded)
  except Exception:
    pass

  # Attempt 2: Standard JSON
  try:
    return json.loads(secret_str)
  except Exception:
    pass

  # Attempt 3: Python AST (handles single-quoted dictionaries)
  try:
    parsed = ast.literal_eval(secret_str)
    if isinstance(parsed, dict):
      return parsed
  except Exception:
    pass

  # Attempt 4: Regex-clean unescaped single quotes
  try:
    # Replace single quotes surrounding keys and values with standard double quotes
    fixed_quotes = re.sub(r"\'", '"', secret_str)
    return json.loads(fixed_quotes)
  except Exception:
    pass

  return None


cred_dict = sanitize_and_parse_credentials(raw_secret)
if cred_dict:
  try:
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    firebase_ready = True
    print("[INIT] Firebase Admin initialized and authenticated successfully.")
  except Exception as e:
    print(
        f"[WARN] Firebase initialization failed: {e}. Running in dry-run mode."
    )
else:
  print(
      "[INFO] FIREBASE_SERVICE_ACCOUNT could not be parsed or is empty. Running"
      " dry-run."
  )

# ==========================================
# 2. PSE Blue-Chip Analytical Profiles
# ==========================================
PSE_WATCHLIST = {
    "ALI": {
        "name": "Ayala Land, Inc.",
        "support": 15.00,
        "resistance": 17.50,
        "ma20": 15.80,
        "ma50": 16.40,
        "pe": "4.8x",
        "pb": "0.6x",
        "sector": "Real Estate / Property Development",
        "catalysts": (
            "Commercial leasing foot-traffic recovery and premium residential"
            " sales."
        ),
        "risks": (
            "Interest rate sensitivity and elevated construction material"
            " costs."
        ),
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "support": 110.00,
        "resistance": 122.00,
        "ma20": 114.50,
        "ma50": 116.00,
        "pe": "7.0x",
        "pb": "0.9x",
        "sector": "Financials / Banking",
        "catalysts": (
            "Net interest margin resilience and sustained enterprise loan"
            " growth."
        ),
        "risks": (
            "Consumer borrower asset quality if monetary conditions remain"
            " tight."
        ),
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "support": 118.00,
        "resistance": 130.00,
        "ma20": 122.00,
        "ma50": 124.50,
        "pe": "8.5x",
        "pb": "1.2x",
        "sector": "Financials / Banking",
        "catalysts": (
            "Robinsons Bank post-merger synergies and digital customer"
            " acquisition."
        ),
        "risks": (
            "Competitive deposit repricing pressuring near-term spreads."
        ),
    },
    "ICT": {
        "name": "Intl Container Terminal Services",
        "support": 820.00,
        "resistance": 875.00,
        "ma20": 845.00,
        "ma50": 830.00,
        "pe": "19.0x",
        "pb": "3.5x",
        "sector": "Industrials / Port Logistics",
        "catalysts": (
            "Global container throughput normalization and USD-pegged tariff"
            " hedges."
        ),
        "risks": (
            "International geopolitical volatility and terminal capex financing."
        ),
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "support": 15.40,
        "resistance": 18.20,
        "ma20": 16.50,
        "ma50": 17.10,
        "pe": "10.2x",
        "pb": "1.1x",
        "sector": "Real Estate / Malls & Retail",
        "catalysts": (
            "Provincial shopping mall rollout and index-linked lease escalation"
            " clauses."
        ),
        "risks": (
            "Discretionary retail headwinds and borrowing costs on mall"
            " development."
        ),
    },
    "SM": {
        "name": "SM Investments Corp.",
        "support": 840.00,
        "resistance": 920.00,
        "ma20": 875.00,
        "ma50": 890.00,
        "pe": "12.0x",
        "pb": "1.3x",
        "sector": "Holding Firms / Conglomerates",
        "catalysts": (
            "Broad domestic economic consumption proxy via banking and retail."
        ),
        "risks": (
            "Consumer discretionary spending softening under lingering"
            " inflation."
        ),
    },
    "AC": {
        "name": "Ayala Corporation",
        "support": 560.00,
        "resistance": 630.00,
        "ma20": 585.00,
        "ma50": 605.00,
        "pe": "9.5x",
        "pb": "0.8x",
        "sector": "Holding Firms / Conglomerates",
        "catalysts": (
            "Renewable power capacity additions (ACEN) and capital recycling."
        ),
        "risks": (
            "Conglomerate net asset value discount and capital commitment"
            " costs."
        ),
    },
    "GLO": {
        "name": "Globe Telecom",
        "support": 1950.00,
        "resistance": 2150.00,
        "ma20": 2020.00,
        "ma50": 2060.00,
        "pe": "11.0x",
        "pb": "1.8x",
        "sector": "Telecommunications",
        "catalysts": (
            "GCash equity value realization and steady common dividend payout"
            " yields."
        ),
        "risks": (
            "Network infrastructure depreciation expenses and mobile prepaid"
            " churn."
        ),
    },
    "TEL": {
        "name": "PLDT Inc.",
        "support": 1280.00,
        "resistance": 1420.00,
        "ma20": 1330.00,
        "ma50": 1360.00,
        "pe": "10.5x",
        "pb": "1.4x",
        "sector": "Telecommunications",
        "catalysts": (
            "Enterprise cloud/data center expansion and disciplined capital"
            " tapering."
        ),
        "risks": (
            "Aggressive fiber pricing competition and balance sheet leverage."
        ),
    },
    "MBT": {
        "name": "Metropolitan Bank & Trust Co.",
        "support": 68.00,
        "resistance": 76.00,
        "ma20": 71.50,
        "ma50": 72.80,
        "pe": "6.8x",
        "pb": "0.7x",
        "sector": "Financials / Banking",
        "catalysts": (
            "Industry-leading Tier-1 capital adequacy and special dividend"
            " capacity."
        ),
        "risks": (
            "Slowing wholesale corporate loan demand during economic"
            " deceleration."
        ),
    },
    "MER": {
        "name": "Manila Electric Company",
        "support": 410.00,
        "resistance": 450.00,
        "ma20": 425.00,
        "ma50": 418.00,
        "pe": "8.8x",
        "pb": "1.9x",
        "sector": "Utilities / Power Distribution",
        "catalysts": (
            "Guaranteed rate base distribution cash flows and power demand"
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
        "ma20": 9.10,
        "ma50": 9.40,
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
        "support": 230.00,
        "resistance": 260.00,
        "ma20": 242.00,
        "ma50": 248.00,
        "pe": "24.0x",
        "pb": "3.1x",
        "sector": "Consumer Discretionary / Restaurants",
        "catalysts": (
            "International store footprint expansion and operating leverage"
            " overseas."
        ),
        "risks": (
            "Store integration overhead and food/labor operating cost"
            " pressures."
        ),
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "support": 25.00,
        "resistance": 29.00,
        "ma20": 26.80,
        "ma50": 27.50,
        "pe": "9.2x",
        "pb": "0.8x",
        "sector": "Consumer Staples / Retail",
        "catalysts": (
            "Resilient essential consumer grocery demand and store network"
            " clustering."
        ),
        "risks": (
            "Competitive encroachment from neighborhood convenience and hard"
            " discounters."
        ),
    },
}


# ==========================================
# 3. Resilient Multi-Source Price Fetcher
# ==========================================
def get_pse_price(ticker: str):
  """Fetches live/EOD price using Yahoo Chart v8 with browser headers, fallback to Google Finance."""
  # Source 1: Yahoo Finance Chart API (Uses .PS suffix)
  url_y = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.PS?interval=1d&range=5d"
  headers_y = {
      "User-Agent": (
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "application/json",
  }
  try:
    req = urllib.request.Request(url_y, headers=headers_y)
    with urllib.request.urlopen(req, timeout=8) as resp:
      if resp.status == 200:
        data = json.loads(resp.read().decode("utf-8"))
        res = data.get("chart", {}).get("result")
        if res:
          meta = res[0].get("meta", {})
          price = meta.get("regularMarketPrice")
          if price and float(price) > 0:
            return float(price)
  except Exception:
    pass

  # Source 2: Google Finance with EU/US consent bypass headers
  url_g = f"https://www.google.com/finance/quote/{ticker}:PSE"
  headers_g = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Cookie": "CONSENT=YES+; SOCS=CAESEwgDEgk2MTQ1NzU4MjQaAnpoIAEaBgiA_LyaBg",
  }
  try:
    req = urllib.request.Request(url_g, headers=headers_g)
    with urllib.request.urlopen(req, timeout=8) as resp:
      html = resp.read().decode("utf-8")
      m = re.search(r'data-last-price="([\d\.]+)"', html)
      if m:
        return float(m.group(1))
      m2 = re.search(r'class="YMlKec fxKbKc">[^\d]*([\d\.,]+)<', html)
      if m2:
        return float(m2.group(1).replace(",", ""))
  except Exception:
    pass

  return None


# ==========================================
# 4. Push Notification Dispatcher
# ==========================================
def dispatch_analyst_alert(
    ticker: str, zone_type: str, price: float, meta: dict
):
  name = meta["name"]
  support = meta["support"]
  resistance = meta["resistance"]
  pe = meta["pe"]

  if zone_type == "ACCUMULATION":
    title = f"🟢 Accumulation Zone: {ticker} (₱{price:.2f})"
    body = (
        f"{name} is trading near structural support (₱{support:.2f}). "
        f"Valuation: P/E {pe} vs historical range. "
        f"Analytical reference point only; not financial advice."
    )
  else:
    title = f"🔴 Profit-Taking Zone: {ticker} (₱{price:.2f})"
    body = (
        f"{name} is approaching overhead resistance (₱{resistance:.2f}). "
        f"Valuation: P/E {pe}. Momentum elevated near supply band. "
        f"Analytical reference point only; not financial advice."
    )

  print(f"[TRIGGER] {title}\n          {body}")

  if not firebase_ready:
    print(f"[DRY-RUN] Alert triggered for {ticker}. Push notification skipped.")
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
  print("=" * 75)
  print(
      f"[SCAN] Initializing market analysis for {len(PSE_WATCHLIST)} PSE"
      " blue-chips..."
  )
  print("=" * 75)

  evaluated = 0
  for sym, meta in PSE_WATCHLIST.items():
    price = get_pse_price(sym)
    time.sleep(0.4)

    if price is None:
      print(f"[-] {sym:<6} | Quote feed temporarily unavailable. Skipping.")
      continue

    evaluated += 1
    support = meta["support"]
    resistance = meta["resistance"]
    ma20 = meta["ma20"]
    ma50 = meta["ma50"]
    pe = meta["pe"]

    # gem.json Zone Logic: Within 2.5% of structural levels
    in_buy_zone = (support * 0.98) <= price <= (support * 1.025)
    in_sell_zone = (resistance * 0.975) <= price <= (resistance * 1.02)

    status_tag = "[NEUTRAL]"
    if in_buy_zone:
      status_tag = "[ACCUMULATION ZONE]"
    elif in_sell_zone:
      status_tag = "[PROFIT-TAKING ZONE]"

    trend = "Above MAs" if price > ma20 and price > ma50 else "Below MAs"

    print(
        f"{status_tag:<20} {sym:<5} | Price: ₱{price:>7.2f} | Supp:"
        f" ₱{support:>7.2f} | Res: ₱{resistance:>7.2f} | P/E: {pe:<5} | Trend:"
        f" {trend}"
    )

    if in_buy_zone:
      dispatch_analyst_alert(sym, "ACCUMULATION", price, meta)
    elif in_sell_zone:
      dispatch_analyst_alert(sym, "PROFIT_TAKING", price, meta)

  print("=" * 75)
  print(
      f"[COMPLETED] Successfully processed {evaluated}/{len(PSE_WATCHLIST)} PSE"
      " stocks."
  )
  print("=" * 75)


if __name__ == "__main__":
  run_scanner()
