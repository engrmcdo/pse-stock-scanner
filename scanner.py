import json
import os
import time
import firebase_admin
from firebase_admin import credentials, messaging
import pandas_ta as ta
import yfinance as yf

# Authenticate Firebase using GitHub Action Secret
firebase_creds_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
if firebase_creds_json:
  cred_dict = json.loads(firebase_creds_json)
  cred = credentials.Certificate(cred_dict)
  firebase_admin.initialize_app(cred)

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

  message = messaging.Message(
      notification=messaging.Notification(title=title, body=body),
      topic="pse_alerts",
  )
  messaging.send(message)


def run_scan():
  for symbol in PSE_TICKERS:
    try:
      stock = yf.Ticker(symbol)
      df = stock.history(period="3mo")
      if df.empty or len(df) < 30:
        continue

      df["RSI"] = ta.rsi(df["Close"], length=14)
      price = df["Close"].iloc[-1]
      rsi = df["RSI"].iloc[-1]

      support = df["Low"].tail(20).min()
      resistance = df["High"].tail(20).max()

      # gem.json Reference Trigger Conditions
      if support * 0.98 <= price <= support * 1.02 and rsi <= 45:
        send_alert(symbol, "BUY", price, support, rsi)
      elif resistance * 0.98 <= price <= resistance * 1.02 and rsi >= 65:
        send_alert(symbol, "SELL", price, resistance, rsi)

    except Exception as e:
      print(f"Error analyzing {symbol}: {e}")
    time.sleep(0.5)


if __name__ == "__main__":
  run_scan()
