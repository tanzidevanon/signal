import yfinance as yf
import time
import json
import pytz
import requests
import os
from datetime import datetime
from strategy import get_trading_signal  # strategy.py থেকে রুলস ইমপোর্ট করা হয়েছে

# কনফিগ লোড
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()
TZ = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))

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
        # ডাটা ফেচ করা
        data = yf.download(tickers=symbol, period='2d', interval='1m', progress=False)
        if data.empty or len(data) < 201: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]

        # strategy.py থেকে সিগন্যাল নেওয়া
        return get_trading_signal(df)
    except:
        return None

def main():
    print(f"🚀 Bot Engine Started. Monitoring {len(config['assets'])} assets...")
    last_signal_time = {}

    while True:
        try:
            current_config = load_config()
            for asset in current_config['assets']:
                if asset not in last_signal_time: last_signal_time[asset] = ""
                
                res = process_asset(asset)
                time.sleep(1.5) # API Safety
                
                if res:
                    signal, quality = res
                    if signal:
                        now = datetime.now(TZ)
                        current_min = now.strftime('%H:%M')
                        
                        if last_signal_time[asset] != current_min:
                            display_name = asset.replace('=X', '').replace('-', '')
                            msg = (
                                f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"🚀 *DIRECTION:* {signal}\n"
                                f"🎯 *QUALITY:* {quality}\n"
                                f"⏰ *TF:* 1 MIN | *EXP:* 1 MIN\n"
                                f"🕒 *TIME (BD):* {current_min}\n\n"
                                f"⚠️ *Note:* Use 1st Step Martingale"
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
                            print(f"Signal Sent for {display_name}")
            
            time.sleep(20)
        except Exception as e:
            print(f"Engine Loop Error: {e}")
            time.sleep(20)

import pandas as pd # process_asset এর প্রয়োজনে
if __name__ == "__main__":
    main()
