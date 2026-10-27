import json
import os
import time
import firebase_admin
from firebase_admin import credentials, messaging
import pandas as pd
import yfinance as yf

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
      "[INFO] No FIREBASE_SERVICE_ACCOUNT secret detected. Running dry-run scan."
  )

# Correct Yahoo Finance suffix for Philippine Stock Exchange is .PM
PSE_TICKERS = [
    "ALI.PM",
    "BDO.PM",
    "BPI.PM",
    "ICT.PM",
    "SMPH.PM",
    "SM.PM",
    "AC.PM",
    "GLO.PM",
    "TEL.PM",
    "MBT.PM",
    "MER.PM",
    "MONDE.PM",
    "JFC.PM",
    "PGOLD.PM",
]


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
  """Computes Relative Strength Index (RSI) using pure pandas."""
  delta = series.diff()
  gain = delta.where(delta > 0, 0.0)
  loss = -delta.where(delta < 0, 0.0)
  avg_gain = gain.rolling(window=period, min_periods=period).mean()
  avg_loss = loss.rolling(window=period, min_periods=period).mean()
  rs = avg_gain / avg_loss
  return 100 - (100 / (1 + rs))


def dispatch_zone_alert(
    ticker: str, zone_type: str, price: float, level: float, rsi: float
):
  """Dispatches alert to Firebase topic if configured."""
  clean_sym = ticker.replace(".PM", "")
  zone_label = (
      "Accumulation Zone (Near Support)"
      if zone_type == "BUY"
      else "Profit-Taking Zone (Near Resistance)"
  )
  title = f"📊 PSE Alert: {clean_sym}"
  body = (
      f"{clean_sym} entered {zone_label} at ₱{price:.2f}. Ref Level: ₱{level:.2f}"
      f" | RSI: {rsi:.1f}. (Analytical reference only; not financial advice.)"
  )

  print(f"[TRIGGER] {title} -> {body}")

  if not firebase_ready:
    print(f"[DRY-RUN] Alert calculated for {clean_sym}, but push was skipped.")
    return

  try:
    msg = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        topic="pse_alerts",
    )
    msg_id = messaging.send(msg)
    print(f"[FCM SUCCESS] Message delivered with ID: {msg_id}")
  except Exception as err:
    print(f"[FCM ERROR] Failed sending notification for {clean_sym}: {err}")


def run_market_scan():
  print(f"[SCAN] Evaluating {len(PSE_TICKERS)} PSE issues...")

  for symbol in PSE_TICKERS:
    try:
      ticker_obj = yf.Ticker(symbol)
      df = ticker_obj.history(period="3mo")

      if df.empty or len(df) < 25:
        print(f"[-] {symbol}: Insufficient price data returned. Skipping.")
        continue

      close_series = df["Close"]
      df["MA20"] = close_series.rolling(window=20).mean()
      df["MA50"] = close_series.rolling(window=50).mean()
      df["RSI"] = calculate_rsi(close_series, period=14)

      curr_price = float(close_series.iloc[-1])
      curr_rsi = (
          float(df["RSI"].dropna().iloc[-1])
          if not df["RSI"].dropna().empty
          else 50.0
      )

      # 20-day Support (lowest price) & Resistance (highest price)
      support_level = float(df["Low"].tail(20).min())
      resist_level = float(df["High"].tail(20).max())

      clean_name = symbol.replace(".PM", "")
      print(
          f"[DATA] {clean_name:<6} Price: ₱{curr_price:>7.2f} | Supp:"
          f" ₱{support_level:>7.2f} | Res: ₱{resist_level:>7.2f} | RSI:"
          f" {curr_rsi:>5.1f}"
      )

      # Buy / Accumulation Zone: Near Support & RSI <= 45
      if (
          support_level * 0.98 <= curr_price <= support_level * 1.02
          and curr_rsi <= 45
      ):
        dispatch_zone_alert(symbol, "BUY", curr_price, support_level, curr_rsi)

      # Sell / Profit-Taking Zone: Near Resistance & RSI >= 65
      elif (
          resist_level * 0.98 <= curr_price <= resist_level * 1.02
          and curr_rsi >= 65
      ):
        dispatch_zone_alert(symbol, "SELL", curr_price, resist_level, curr_rsi)

    except Exception as stock_err:
      print(f"[WARN] Error calculating {symbol}: {stock_err}")

    time.sleep(0.3)

  print("[SCAN] Completed all ticker evaluations.")


if __name__ == "__main__":
  run_market_scan()
