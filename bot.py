import yfinance as yf
import time
import json
import pytz
import requests
import os
import pandas as pd
from datetime import datetime
from strategy import get_trading_signal
from concurrent.futures import ThreadPoolExecutor

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
        requests.get(url, timeout=5)
    except: pass

def process_asset(asset):
    try:
        tf = config.get('timeframe', '1m')
        # ডাটা ফেচিং (দ্রুত করার জন্য অল্প ডাটা নেওয়া হচ্ছে)
        data = yf.download(tickers=asset, period='1d', interval=tf, progress=False)
        if data.empty or len(data) < 50: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]

        res = get_trading_signal(df)
        if res and res[0]:
            return asset, res
    except:
        return None
    return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 High-Speed Engine Started | Multithreading Active")
    
    last_signal_time = {}

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            tf_label = current_config.get('timeframe', '1m')
            exp_label = current_config.get('expiry', '1 min')
            
            # সব এসেট একসাথে স্ক্যান করার জন্য থ্রেডিং
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(process_asset, assets))
            
            for res in results:
                if res:
                    asset, (signal, quality) = res
                    now = datetime.now(user_tz)
                    current_min = now.strftime('%H:%M')
                    
                    if last_signal_time.get(asset) != current_min:
                        display_name = asset.replace('=X', '').replace('-', '')
                        time_str = now.strftime('%H:%M:%S')
                        
                        msg = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {display_name}\n"
                            f"🚀 *DIRECTION:* {signal}\n"
                            f"🎯 *QUALITY:* {quality}\n"
                            f"⏰ *TIMEFRAME:* {tf_label}\n"
                            f"⏳ *EXPIRY:* {exp_label}\n"
                            f"🕒 *TIME (BD):* {time_str}\n\n"
                            f"⚠️ *Note:* Entry for the next candle!"
                        )
                        send_telegram_msg(msg)
                        last_signal_time[asset] = current_min
                        print(f"[{time_str}] Signal: {display_name}")

            # স্ক্যানিং স্পিড নিয়ন্ত্রণ
            time.sleep(2) 
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
