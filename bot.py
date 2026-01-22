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
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, data={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
        return r.json().get('result', {}).get('message_id')
    except: return None

def edit_telegram_msg(message_id, message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    try:
        requests.post(url, data={'chat_id': chat_id, 'message_id': message_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def process_asset(symbol):
    try:
        tf = config.get('timeframe', '1m')
        data = yf.download(tickers=symbol, period='2d', interval=tf, progress=False)
        if data.empty or len(data) < 201: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except: return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Live Signal Engine Started")
    
    last_signal_time = {}

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            tf_label = current_config.get('timeframe', '1m')
            exp_label = current_config.get('expiry', '1 min')
            
            for asset in assets:
                res = process_asset(asset)
                if res and res[0]:
                    signal, quality = res
                    now = datetime.now(user_tz)
                    current_min = now.strftime('%H:%M')
                    
                    # যদি নতুন সিগন্যাল হয়
                    if last_signal_time.get(asset) != current_min:
                        display_name = asset.replace('=X', '').replace('-', '')
                        time_str = now.strftime('%H:%M:%S')
                        
                        # প্রাথমিক মেসেজ পাঠানো
                        msg_template = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {display_name}\n"
                            f"🚀 *DIRECTION:* {signal}\n"
                            f"🎯 *QUALITY:* {quality}\n"
                            f"⏰ *TIMEFRAME:* {tf_label}\n"
                            f"⏳ *EXPIRY:* {exp_label}\n"
                            f"🕒 *TIME (BD):* {time_str}\n\n"
                        )
                        
                        msg_id = send_telegram_msg(msg_template + "⏳ *ENTRY WINDOW:* 15s\n✅ *STATUS:* Safe to Entry")
                        last_signal_time[asset] = current_min
                        
                        # --- ১৫ সেকেন্ডের লাইভ কাউন্টডাউন লুপ ---
                        start_time = time.time()
                        while True:
                            elapsed = int(time.time() - start_time)
                            remaining = 15 - elapsed
                            
                            if remaining <= 0:
                                edit_telegram_msg(msg_id, msg_template + "⌛ *ENTRY EXPIRED*\n⚠️ Do not take trade now.")
                                break
                            
                            # প্রতি ২ সেকেন্ডে মার্কেট চেক করা
                            current_res = process_asset(asset)
                            status_text = "✅ *STATUS:* Safe to Entry"
                            if not current_res or current_res[0] != signal:
                                status_text = "❌ *STATUS:* Entry Closed (Volatile)"
                                edit_telegram_msg(msg_id, msg_template + f"⏳ *ENTRY WINDOW:* {remaining}s\n{status_text}")
                                break # কন্ডিশন নষ্ট হলে কাউন্টডাউন বন্ধ
                                
                            edit_telegram_msg(msg_id, msg_template + f"⏳ *ENTRY WINDOW:* {remaining}s\n{status_text}")
                            time.sleep(2) # ২ সেকেন্ড পর পর আপডেট

            time.sleep(2) # পরবর্তী এসেট চেক করার আগে বিরতি
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
