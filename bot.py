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

# টেলিগ্রাম মেসেজ ফাংশন (আইডি রিটার্ন করবে)
def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.json().get('result', {}).get('message_id')
    except: return None

# মেসেজ এডিট করার ফাংশন
def edit_telegram_msg(message_id, message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': message, 'parse_mode': 'Markdown'}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

# মেসেজ ডিলিট করার ফাংশন
def delete_telegram_msg(message_id):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    payload = {'chat_id': chat_id, 'message_id': message_id}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def process_asset(symbol):
    try:
        tf = config.get('timeframe', '1m')
        period_val = '2d' if tf == '1m' else '5d'
        data = yf.download(tickers=symbol, period=period_val, interval=tf, progress=False)
        if data.empty or len(data) < 201: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except: return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Engine Started | Smart Alert System Active")
    
    active_alerts = {} # {asset: {'msg_id': 123, 'type': 'PREPARE', 'time': timestamp}}

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            tf_label = current_config.get('timeframe', '1m')
            exp_label = current_config.get('expiry', '1 min')
            
            for asset in assets:
                res = process_asset(asset)
                time.sleep(0.5) 
                
                display_name = asset.replace('=X', '').replace('-', '')
                now = datetime.now(user_tz)
                time_str = now.strftime('%H:%M:%S')
                
                if res:
                    signal, quality = res
                    
                    # কন্ডিশন ১: এটি একটি কনফার্মড সিগন্যাল
                    if "🟢" in str(signal) or "🔴" in str(signal):
                        msg = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {display_name}\n"
                            f"🚀 *DIRECTION:* {signal}\n"
                            f"🎯 *QUALITY:* {quality}\n"
                            f"⏰ *TIMEFRAME:* {tf_label}\n"
                            f"⏳ *EXPIRY:* {exp_label}\n"
                            f"🕒 *TIME (BD):* {time_str}\n\n"
                            f"⚠️ *Note:* Use 1st Step Martingale"
                        )
                        
                        if asset in active_alerts:
                            edit_telegram_msg(active_alerts[asset]['msg_id'], msg)
                            del active_alerts[asset] # কাজ শেষ
                        else:
                            send_telegram_msg(msg)
                            
                    # কন্ডিশন ২: এটি একটি প্রি-অ্যালার্ট
                    elif "PREPARE" in str(signal):
                        if asset not in active_alerts:
                            direction = "UP" if "CALL" in signal else "DOWN"
                            alert_msg = (
                                f"⚠️ *PRE-ALERT: GET READY*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"👉 *DIRECTION:* {direction}\n"
                                f"⏳ *STATUS:* Waiting for confirmation...\n"
                                f"🕒 *TIME:* {time_str}"
                            )
                            msg_id = send_telegram_msg(alert_msg)
                            if msg_id:
                                active_alerts[asset] = {'msg_id': msg_id, 'time': time.time()}

                else:
                    # যদি সিগন্যাল বা অ্যালার্ট না থাকে কিন্তু আগে অ্যালার্ট দেওয়া ছিল
                    if asset in active_alerts:
                        # ২ মিনিট পার হয়ে গেলে বা মার্কেট দূরে সরে গেলে ডিলিট
                        if time.time() - active_alerts[asset]['time'] > 60:
                            edit_telegram_msg(active_alerts[asset]['msg_id'], f"❌ *SIGNAL CANCELLED:* {display_name}")
                            time.sleep(2)
                            delete_telegram_msg(active_alerts[asset]['msg_id'])
                            del active_alerts[asset]

            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
