import base64
import json
import os
import ssl
import time
import urllib.request
import firebase_admin
from firebase_admin import credentials, db, messaging

# 1. Initialize Firebase with Database URL
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
    # Enable Realtime Database connection for your project
    firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": (
                f"https://{cred_dict.get('project_id', 'pse-stock-alerts')}-default-rtdb.firebaseio.com"
            )
        },
    )
    firebase_ready = True
    print("[INIT] Firebase & Realtime DB initialized.")
  except Exception as e:
    print(f"[WARN] Firebase initialization error: {e}")

# ... [Keep PSE_WATCHLIST & market fetch functions unchanged] ...


def sync_market_data_to_firebase(results_dict):
  """Pushes real-time scan metrics directly to Firebase Realtime Database."""
  if not firebase_ready:
    return
  try:
    ref = db.reference("pse_market_data")
    ref.set({
        "last_updated": int(time.time()),
        "stocks": results_dict,
    })
    print("[DB SYNC] Live market analysis written to Firebase.")
  except Exception as err:
    print(f"[DB SYNC ERROR] Failed to write database: {err}")
