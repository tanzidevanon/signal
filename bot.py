import yfinance as yf
import time
import json
import pytz
import requests
import os
import pandas as pd
from datetime import datetime
from strategy import get_trading_signal

# কনফিগ লোড
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()

def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url, timeout=10)
    except:
        pass

def process_asset(symbol):
    try:
        tf = config.get('timeframe', '1m')
        data = yf.download(tickers=symbol, period='2d', interval=tf, progress=False)
        if data.empty or len(data) < 201: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except:
        return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Alert System Started | TZ: {user_tz}")
    
    # কোন মিনিটের সিগন্যাল পাঠানো হয়েছে তা ট্র্যাক করার জন্য
    last_alert_min = -1
    last_signal_min = -1

    while True:
        try:
            now = datetime.now(user_tz)
            
            # --- স্টেজ ১: সতর্কবার্তা (৪৫ সেকেন্ডে) ---
            if now.second == 45 and now.minute != last_alert_min:
                current_config = load_config()
                for asset in current_config['assets']:
                    res = process_asset(asset)
                    if res and res[0]: # সিগন্যাল থাকলে
                        display_name = asset.replace('=X', '')
                        msg = (
                            f"⚠️ *PRE-SIGNAL ALERT* ⚠️\n"
                            f"📊 Asset: {display_name}\n"
                            f"⏳ Status: Preparing for {res[0]}\n"
                            f"🕒 Action in: 15 Seconds\n\n"
                            f"👉 Open Quotex and find this asset now!"
                        )
                        send_telegram_msg(msg)
                last_alert_min = now.minute

            # --- স্টেজ ২: চূড়ান্ত সিগন্যাল (০০ সেকেন্ডে) ---
            if now.second == 0 and now.minute != last_signal_min:
                current_config = load_config()
                for asset in current_config['assets']:
                    res = process_asset(asset)
                    if res and res[0]:
                        display_name = asset.replace('=X', '')
                        msg = (
                            f"🔥 *TRADE NOW - ENTRY* 🔥\n"
                            f"📊 Asset: {display_name}\n"
                            f"🚀 Direction: {res[0]}\n"
                            f"🎯 Quality: {res[1]}\n"
                            f"⏳ Duration: {current_config['expiry']}\n"
                            f"🕒 Time: {now.strftime('%H:%M:%S')}\n\n"
                            f"✅ Go Go Go! Enter Trade Now!"
                        )
                        send_telegram_msg(msg)
                last_signal_min = now.minute

            time.sleep(1) # প্রতি ১ সেকেন্ড পর পর সময় চেক করবে
            
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
