import yfinance as yf
import time
import json
import pytz
import requests
import os
import pandas as pd
from datetime import datetime
from strategy import get_trading_signal

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
        period_val = '2d' if tf == '1m' else '5d'
        data = yf.download(tickers=symbol, period=period_val, interval=tf, progress=False)
        if data.empty or len(data) < 201: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]

        return get_trading_signal(df)
    except Exception as e:
        return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Engine Started | Pre-Alert System Active")
    
    last_signal_time = {}
    last_alert_time = {} # অ্যালার্ট ট্র্যাক করার জন্য

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            
            for asset in assets:
                if asset not in last_signal_time: last_signal_time[asset] = ""
                if asset not in last_alert_time: last_alert_time[asset] = ""
                
                res = process_asset(asset)
                time.sleep(0.5) # স্পিড বাড়ানোর জন্য টাইম কমানো হয়েছে
                
                if res:
                    signal, quality = res
                    display_name = asset.replace('=X', '').replace('-', '')
                    now = datetime.now(user_tz)
                    current_min = now.strftime('%H:%M')

                    # ১. ফাইনাল সিগন্যাল হ্যান্ডলিং
                    if signal and "🟢" in signal or "🔴" in signal:
                        if last_signal_time[asset] != current_min:
                            msg = (
                                f"🔔 *CONFIRMED SIGNAL*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"🚀 *DIRECTION:* {signal}\n"
                                f"🎯 *QUALITY:* {quality}\n"
                                f"🕒 *TIME:* {now.strftime('%H:%M:%S')}\n\n"
                                f"✅ *TAKE TRADE NOW!*"
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
                            print(f"[{now.strftime('%H:%M:%S')}] Signal: {display_name}")

                    # ২. প্রি-অ্যালার্ট হ্যান্ডলিং
                    elif signal and "PREPARE" in signal:
                        if last_alert_time[asset] != current_min and last_signal_time[asset] != current_min:
                            direction = "UP" if "CALL" in signal else "DOWN"
                            emoji = "🔵" if direction == "UP" else "🟠"
                            msg = (
                                f"⚠️ *PRE-ALERT (Get Ready)*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"👉 *DIRECTION:* {direction}\n"
                                f"⏳ *Action:* Open asset & be ready!"
                            )
                            send_telegram_msg(msg)
                            last_alert_time[asset] = current_min
                            print(f"[{now.strftime('%H:%M:%S')}] Alert: {display_name}")

            time.sleep(5) # দ্রুত চেক করার জন্য সময় কমানো হয়েছে
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    main()
