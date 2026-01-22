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

# টেলিগ্রাম মেসেজ ফাংশন (মেসেজ আইডি রিটার্ন করবে)
def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.json().get('result', {}).get('message_id')
    except:
        return None

# মেসেজ এডিট করার ফাংশন
def edit_telegram_msg(message_id, message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

# রেজাল্ট চেক এবং মেসেজ আপডেট ফাংশন
def check_and_update_result(asset, entry_price, direction, signal_time, message_id, msg_template):
    display_name = asset.replace('=X', '').replace('-', '')
    print(f"⌛ Result processing for {display_name}...")
    
    # ট্রেড শেষ হওয়া এবং ডাটা আপলোডের জন্য অপেক্ষা
    time.sleep(100) 
    
    for attempt in range(4): # কয়েকবার চেষ্টা করবে ডাটা সিঙ্ক হতে দেরি হলে
        try:
            data = yf.download(tickers=asset, period='1d', interval='1m', progress=False)
            if data is not None and not data.empty:
                df = data.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [str(col).lower() for col in df.columns]
                
                # টাইমজোন ম্যাচিং
                df.index = df.index.tz_convert('Asia/Dhaka')
                target_time = signal_time.replace(second=0, microsecond=0)
                
                if target_time in df.index:
                    current_price = float(df.loc[target_time, 'close'])
                    
                    if "CALL" in direction:
                        win = current_price > entry_price
                    else:
                        win = current_price < entry_price
                        
                    status = "✅ WIN" if win else "❌ LOSS"
                    
                    # আগের মেসেজ টেমপ্লেটের সাথে রেজাল্ট যোগ করা
                    final_msg = msg_template.replace("🔄 Checking...", f"{status} (Entry: {entry_price:.5f}, Close: {current_price:.5f})")
                    
                    edit_telegram_msg(message_id, final_msg)
                    print(f"🎯 Result Updated: {display_name} -> {status}")
                    return
            
        except Exception as e:
            print(f"❌ Error updating {asset}: {e}")
        
        time.sleep(20)

def process_asset(symbol):
    try:
        data = yf.download(tickers=symbol, period='2d', interval=config.get('timeframe', '1m'), progress=False)
        if data.empty or len(data) < 100: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except:
        return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Smart Result Editor Bot Active")
    
    last_signal_time = {}
    result_executor = ThreadPoolExecutor(max_workers=25)

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            tf_label = current_config.get('timeframe', '1m')
            exp_label = current_config.get('expiry', '1 min')
            
            with ThreadPoolExecutor(max_workers=15) as executor:
                results = list(executor.map(process_asset, assets))
            
            for i, res in enumerate(results):
                asset = assets[i]
                if res and res[0]:
                    signal, quality_pct, entry_price = res
                    now = datetime.now(user_tz)
                    current_min = now.strftime('%H:%M')
                    
                    if last_signal_time.get(asset) != current_min:
                        display_name = asset.replace('=X', '').replace('-', '')
                        time_str = now.strftime('%H:%M:%S')
                        
                        # মেসেজ টেমপ্লেট তৈরি (Trade Results: 🔄 Checking... সহ)
                        msg = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {display_name}\n"
                            f"🚀 *DIRECTION:* {signal}\n"
                            f"🎯 *QUALITY:* {quality_pct}\n"
                            f"⏰ *TIMEFRAME:* {tf_label}\n"
                            f"⏳ *EXPIRY:* {exp_label}\n"
                            f"🕒 *TIME (BD):* {time_str}\n"
                            f"📈 *TRADE RESULTS:* 🔄 Checking...\n\n"
                            f"⚠️ *Note:* Use 1st Step Martingale"
                        )
                        
                        # মেসেজ পাঠানো এবং আইডি সেভ করা
                        msg_id = send_telegram_msg(msg)
                        last_signal_time[asset] = current_min
                        
                        if msg_id:
                            # রেজাল্ট আপডেট করার জন্য ব্যাকগ্রাউন্ড থ্রেড
                            result_executor.submit(check_and_update_result, asset, float(entry_price), signal, now, msg_id, msg)

            time.sleep(5) 
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
