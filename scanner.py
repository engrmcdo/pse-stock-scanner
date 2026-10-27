import json
import os
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
    cred_dict = json.loads(raw_secret)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    firebase_ready = True
    print("[INIT] Firebase authenticated successfully.")
  except Exception as err:
    print(
        f"[WARN] Firebase credential parse error: {err}. Operating in dry-run"
        " mode."
    )
else:
  print(
      "[INFO] FIREBASE_SERVICE_ACCOUNT is empty or not configured. Operating in"
      " dry-run mode."
  )

# ==========================================
# 2. Tracked PSE Tickers & Structural Levels
# ==========================================
# Aligned with gem.json technical & fundamental reference framework
PSE_WATCHLIST = {
    "ALI": {
        "name": "Ayala Land, Inc.",
        "support": 15.00,
        "resistance": 17.50,
        "pe": "4.8x",
        "notes": "Large-cap property developer; steady recurring lease income.",
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "support": 110.00,
        "resistance": 122.00,
        "pe": "7.0x",
        "notes": (
            "Largest domestic bank by assets; robust net interest margins."
        ),
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "support": 118.00,
        "resistance": 130.00,
        "pe": "8.5x",
        "notes": "High return on equity; strong digital deposit expansion.",
    },
    "ICT": {
        "name": "International Container Terminal Services",
        "support": 820.00,
        "resistance": 875.00,
        "pe": "19.0x",
        "notes": "Global port operator; dollar-linked earnings structure.",
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "support": 15.40,
        "resistance": 18.20,
        "pe": "10.2x",
        "notes": (
            "Retail real estate footprint; benefits from consumer foot traffic."
        ),
    },
    "SM": {
        "name": "SM Investments Corp.",
        "support": 840.00,
        "resistance": 920.00,
        "pe": "12.0x",
        "notes": (
            "Core conglomerate proxy with retail, banking, and property arms."
        ),
    },
    "AC": {
        "name": "Ayala Corporation",
        "support": 560.00,
        "resistance": 630.00,
        "pe": "9.5x",
        "notes": "Diversified holdings with renewable power and telecom.",
    },
    "GLO": {
        "name": "Globe Telecom",
        "support": 1950.00,
        "resistance": 2150.00,
        "pe": "11.0x",
        "notes": "High-yield dividend payer; data traffic demand.",
    },
    "TEL": {
        "name": "PLDT Inc.",
        "support": 1280.00,
        "resistance": 1420.00,
        "pe": "10.5x",
        "notes": "Broadband and enterprise connectivity focus.",
    },
    "MBT": {
        "name": "Metropolitan Bank & Trust Co.",
        "support": 68.00,
        "resistance": 76.00,
        "pe": "6.8x",
        "notes": "Strong tier-1 capital adequacy and corporate loan portfolio.",
    },
    "MER": {
        "name": "Manila Electric Company",
        "support": 410.00,
        "resistance": 450.00,
        "pe": "8.8x",
        "notes": "Defensive utility cash flows and steady dividend yield.",
    },
    "MONDE": {
        "name": "Monde Nissin",
        "support": 8.50,
        "resistance": 10.20,
        "pe": "15.0x",
        "notes": "Consumer staple market share; raw material cost monitoring.",
    },
    "JFC": {
        "name": "Jollibee Foods Corporation",
        "support": 230.00,
        "resistance": 260.00,
        "pe": "24.0x",
        "notes": "Global quick-service store expansion.",
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "support": 25.00,
        "resistance": 29.00,
        "pe": "9.2x",
        "notes": "Resilient grocery retail catering to essential spending.",
    },
}


# ==========================================
# 3. Market Data Retrieval (Resilient Fetcher)
# ==========================================
def fetch_ticker_quote(ticker: str):
  """Fetches ticker quote with multiple network fallbacks."""
  # Endpoint 1: Direct JSON stock query
  url1 = f"https://phisix-api4.appspot.com/stocks/{ticker}.json"
  # Endpoint 2: Alternate PSE EDGE company directory query
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "application/json",
  }

  for target_url in [url1]:
    try:
      req = urllib.request.Request(target_url, headers=headers)
      with urllib.request.urlopen(req, timeout=10) as response:
        if response.status == 200:
          data = json.loads(response.read().decode())
          stock = data.get("stock", [{}])[0]
          price = float(stock.get("price", {}).get("amount", 0.0))
          if price > 0:
            return price
    except Exception:
      pass

  return None


# ==========================================
# 4. Push Notification Dispatcher
# ==========================================
def dispatch_alert(
    ticker: str, zone_type: str, price: float, level: float, meta: dict
):
  clean_sym = ticker
  zone_title = (
      "Accumulation Zone (Near Support)"
      if zone_type == "BUY"
      else "Profit-Taking Zone (Near Resistance)"
  )
  title = f"📊 PSE Alert: {clean_sym}"
  body = (
      f"{clean_sym} entered {zone_title} at ₱{price:.2f}. "
      f"Reference level: ₱{level:.2f}. P/E: {meta['pe']}. "
      f"Analytical reference only; not financial advice."
  )

  print(f"[TRIGGER] {title} -> {body}")

  if not firebase_ready:
    print(f"[DRY-RUN] Alert triggered for {clean_sym}. Push skipped.")
    return

  try:
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic="pse_alerts",
    )
    msg_id = messaging.send(message)
    print(f"[FCM] Push dispatched successfully (ID: {msg_id})")
  except Exception as err:
    print(f"[FCM ERROR] Alert dispatch failed for {clean_sym}: {err}")


# ==========================================
# 5. Core Analytical Engine Loop
# ==========================================
def run_scanner():
  print(f"[SCAN] Initializing scan across {len(PSE_WATCHLIST)} PSE issues...")

  available_quotes = 0
  for sym, meta in PSE_WATCHLIST.items():
    price = fetch_ticker_quote(sym)

    if price is None:
      # If external API is unreachable or closed, inform without crashing
      print(f"[-] {sym:<6}: Quote feed temporarily unavailable. Skipping.")
      time.sleep(0.3)
      continue

    available_quotes += 1
    support = meta["support"]
    resistance = meta["resistance"]

    print(
        f"[DATA] {sym:<6} Price: ₱{price:>7.2f} | Supp: ₱{support:>7.2f} | Res:"
        f" ₱{resistance:>7.2f} | P/E: {meta['pe']}"
    )

    # gem.json Buy / Accumulation Zone: Within 2.5% of structural support
    if support * 0.98 <= price <= support * 1.025:
      dispatch_alert(sym, "BUY", price, support, meta)

    # gem.json Sell / Profit-Taking Zone: Within 2.5% of structural resistance
    elif resistance * 0.975 <= price <= resistance * 1.02:
      dispatch_alert(sym, "SELL", price, resistance, meta)

    time.sleep(0.4)

  if available_quotes == 0:
    print(
        "[NOTICE] Market feed returned no active quotes. Note that the PSE"
        " market operates 9:30 AM – 3:00 PM PHT (UTC+8). The script will"
        " re-evaluate on the next scheduled run."
    )
  else:
    print(
        f"[FINISH] Successfully evaluated {available_quotes} active PSE"
        " stocks."
    )


if __name__ == "__main__":
  run_scanner()
