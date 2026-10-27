import json
import os
import time
import firebase_admin
from firebase_admin import credentials, messaging
import pandas_ta as ta
import yfinance as yf

# 1. Gracefully initialize Firebase
firebase_ready = False
firebase_creds_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")

if firebase_creds_json:
  try:
    cred_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    firebase_ready = True
    print("[INIT] Firebase Admin initialized successfully.")
  except Exception as e:
    print(f"[WARN] Failed to initialize Firebase: {e}")
    print(
        "[WARN] Continuing execution in dry-run mode (analysis only,"
        " notifications skipped)."
    )
else:
  print(
      "[WARN] FIREBASE_SERVICE_ACCOUNT secret is missing or empty. Running in"
      " dry-run mode."
  )

# Core liquid PSE issues
PSE_TICKERS = [
    "ALI.PS",
    "BDO.PS",
    "BPI.PS",
    "ICT.PS",
    "SMPH.PS",
    "SM.PS",
    "AC.PS",
    "GLO.PS",
    "TEL.PS",
    "MBT.PS",
    "MER.PS",
    "MONDE.PS",
    "JFC.PS",
    "PGOLD.PS",
]


def send_alert(ticker, zone, price, level, rsi):
  clean_ticker = ticker.replace(".PS", "")
  action_text = (
      "Accumulation Zone (Support)"
      if zone == "BUY"
      else "Profit-Taking Zone (Resistance)"
  )
  title = f"📊 PSE Alert: {clean_ticker}"
  body = f"{clean_ticker} entered {action_text} at ₱{price:.2f}. Ref Level: ₱{level:.2f}, RSI: {rsi:.1f}."

  print(f"[TRIGGER] {title} - {body}")

  if not firebase_ready:
    print(
        f"[SKIP] Firebase not configured. Did not dispatch alert for"
        f" {clean_ticker}."
    )
    return

  try:
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic="pse_alerts",
    )
    response = messaging.send(message)
    print(f"[DISPATCH] Successfully sent FCM message ID: {response}")
  except Exception as e:
    print(f"[ERROR] Failed to send push notification: {e}")


def run_scan():
  print(f"[START] Beginning analysis across {len(PSE_TICKERS)} PSE tickers...")

  for symbol in PSE_TICKERS:
    try:
      stock = yf.Ticker(symbol)
      df = stock.history(period="3mo")

      if df.empty or len(df) < 30:
        print(f"[DATA] Insufficient data returned for {symbol}. Skipping.")
        continue

      df["RSI"] = ta.rsi(df["Close"], length=14)
      df["MA20"] = ta.sma(df["Close"], length=20)
      df["MA50"] = ta.sma(df["Close"], length=50)

      price = float(df["Close"].iloc[-1])
      rsi = float(df["RSI"].iloc[-1])

      support = float(df["Low"].tail(20).min())
      resistance = float(df["High"].tail(20).max())

      print(
          f"[{symbol.replace('.PS', '')}] Price: ₱{price:.2f} | Support:"
          f" ₱{support:.2f} | Resistance: ₱{resistance:.2f} | RSI: {rsi:.1f}"
      )

      # Analytical Buy / Accumulation Zone: Near support & non-overbought momentum
      if support * 0.98 <= price <= support * 1.02 and rsi <= 50:
        send_alert(symbol, "BUY", price, support, rsi)

      # Analytical Sell / Profit-Taking Zone: Near resistance & elevated momentum
      elif resistance * 0.98 <= price <= resistance * 1.02 and rsi >= 60:
        send_alert(symbol, "SELL", price, resistance, rsi)

    except Exception as e:
      print(f"[ERROR] Exception processing {symbol}: {e}")

    time.sleep(0.5)

  print("[FINISH] PSE stock scan complete.")


if __name__ == "__main__":
  run_scan()
