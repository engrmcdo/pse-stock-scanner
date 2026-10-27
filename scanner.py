import json
import os
import time
import urllib.request
import firebase_admin
from firebase_admin import credentials, messaging

# 1. Initialize Firebase Admin
firebase_ready = False
raw_secret = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

if raw_secret and raw_secret.strip():
  try:
    cred_dict = json.loads(raw_secret)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    firebase_ready = True
    print("[INIT] Firebase authenticated successfully.")
  except Exception as err:
    print(
        f"[WARN] Firebase init failed: {err}. Proceeding in dry-run mode"
        " (scanning without push alerts)."
    )
else:
  print(
      "[INFO] FIREBASE_SERVICE_ACCOUNT secret is missing or empty. Running in"
      " dry-run mode."
  )

# Tracked Philippine Stock Exchange issues
TARGET_PSE_TICKERS = [
    "ALI",
    "BDO",
    "BPI",
    "ICT",
    "SMPH",
    "SM",
    "AC",
    "GLO",
    "TEL",
    "MBT",
    "MER",
    "MONDE",
    "JFC",
    "PGOLD",
]


def fetch_pse_market_data():
  """Fetches live/EOD quotes directly from the PSE EDGE public market feed."""
  url = "https://phisix-api4.appspot.com/stocks.json"
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
  try:
    with urllib.request.urlopen(req, timeout=15) as response:
      data = json.loads(response.read().decode())
      stocks = data.get("stock", [])
      market_map = {}
      for s in stocks:
        sym = s.get("symbol")
        if sym in TARGET_PSE_TICKERS:
          market_map[sym] = {
              "price": float(s.get("price", {}).get("amount", 0)),
              "percent_change": float(s.get("percent_change", 0)),
              "volume": float(s.get("volume", 0)),
          }
      return market_map
  except Exception as e:
    print(f"[API ERROR] Failed fetching PSE data: {e}")
    return {}


def dispatch_zone_alert(
    ticker: str, zone_type: str, price: float, level: float, context: str
):
  """Dispatches alert to Firebase topic if configured."""
  zone_label = (
      "Accumulation Zone (Near Support)"
      if zone_type == "BUY"
      else "Profit-Taking Zone (Near Resistance)"
  )
  title = f"📊 PSE Alert: {ticker}"
  body = (
      f"{ticker} entered {zone_label} at ₱{price:.2f}. Ref Level: ₱{level:.2f}."
      f" Context: {context}. (Analytical reference only; not financial advice.)"
  )

  print(f"[TRIGGER] {title} -> {body}")

  if not firebase_ready:
    print(f"[DRY-RUN] Alert calculated for {ticker}, but push was skipped.")
    return

  try:
    msg = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic="pse_alerts",
    )
    msg_id = messaging.send(msg)
    print(f"[FCM SUCCESS] Message delivered with ID: {msg_id}")
  except Exception as err:
    print(f"[FCM ERROR] Failed sending notification for {ticker}: {err}")


def run_market_scan():
  # Reference structural support and resistance levels aligned with gem.json
  reference_levels = {
      "ALI": {
          "support": 15.00,
          "resistance": 17.50,
          "name": "Ayala Land",
          "pe": "4.8x",
      },
      "BDO": {
          "support": 110.00,
          "resistance": 122.00,
          "name": "BDO Unibank",
          "pe": "7.0x",
      },
      "BPI": {
          "support": 118.00,
          "resistance": 130.00,
          "name": "Bank of the Philippine Islands",
          "pe": "8.5x",
      },
      "ICT": {
          "support": 820.00,
          "resistance": 875.00,
          "name": "Intl Container Terminal",
          "pe": "19.0x",
      },
      "SMPH": {
          "support": 15.40,
          "resistance": 18.20,
          "name": "SM Prime Holdings",
          "pe": "10.2x",
      },
      "SM": {
          "support": 840.00,
          "resistance": 920.00,
          "name": "SM Investments",
          "pe": "12.0x",
      },
      "AC": {
          "support": 560.00,
          "resistance": 630.00,
          "name": "Ayala Corporation",
          "pe": "9.5x",
      },
      "GLO": {
          "support": 1950.00,
          "resistance": 2150.00,
          "name": "Globe Telecom",
          "pe": "11.0x",
      },
      "TEL": {
          "support": 1280.00,
          "resistance": 1420.00,
          "name": "PLDT Inc",
          "pe": "10.5x",
      },
      "MBT": {
          "support": 68.00,
          "resistance": 76.00,
          "name": "Metrobank",
          "pe": "6.8x",
      },
      "MER": {
          "support": 410.00,
          "resistance": 450.00,
          "name": "Meralco",
          "pe": "8.8x",
      },
      "MONDE": {
          "support": 8.50,
          "resistance": 10.20,
          "name": "Monde Nissin",
          "pe": "15.0x",
      },
      "JFC": {
          "support": 230.00,
          "resistance": 260.00,
          "name": "Jollibee Foods",
          "pe": "24.0x",
      },
      "PGOLD": {
          "support": 25.00,
          "resistance": 29.00,
          "name": "Puregold Price Club",
          "pe": "9.2x",
      },
  }

  print(f"[SCAN] Querying PSE market data for {len(TARGET_PSE_TICKERS)} issues...")
  data = fetch_pse_market_data()

  if not data:
    print("[-] No market data returned. Check network or market session.")
    return

  for sym, info in data.items():
    curr_price = info["price"]
    ref = reference_levels.get(sym, {})
    support = ref.get("support", curr_price * 0.95)
    resistance = ref.get("resistance", curr_price * 1.05)
    pe = ref.get("pe", "N/A")

    print(
        f"[DATA] {sym:<6} Price: ₱{curr_price:>7.2f} | Supp: ₱{support:>7.2f} |"
        f" Res: ₱{resistance:>7.2f} | Chg: {info['percent_change']:>5.2f}%"
    )

    # Accumulation Zone: Within 2% of Support
    if support * 0.98 <= curr_price <= support * 1.025:
      dispatch_zone_alert(
          sym,
          "BUY",
          curr_price,
          support,
          f"Near support base (P/E ~{pe})",
      )

    # Profit-Taking Zone: Within 2% of Resistance
    elif resistance * 0.975 <= curr_price <= resistance * 1.02:
      dispatch_zone_alert(
          sym,
          "SELL",
          curr_price,
          resistance,
          "Near upper overhead resistance",
      )

  print("[SCAN] Completed all ticker evaluations.")


if __name__ == "__main__":
  run_market_scan()
