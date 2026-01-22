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

def check_result(asset, entry_price, direction):
    # ৮৫ সেকেন্ড অপেক্ষা (ডাটা সেটেল হওয়ার জন্য)
    print(f"⌛ Waiting for result: {asset}...")
    time.sleep(85) 
    
    try:
        # লেটেস্ট ১ মিনিটের ডাটা ফেচ করা
        data = yf.download(tickers=asset, period='1d', interval='1m', progress=False)
        
        if data is not None and not data.empty:
            df = data.copy()
            
            # ১. মাল্টি-ইনডেক্স কলাম ফিক্স (আপনার এররটির মূল কারণ এখানে)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # ২. কলামের নাম ছোট হাতের করা (Consistency)
            df.columns = [str(col).lower() for col in df.columns]
            
            # ৩. সর্বশেষ ক্লোজিং প্রাইস নেওয়া এবং নিশ্চিত করা এটি একটি সিঙ্গেল ফ্লোট নাম্বার
            last_close = df['close'].iloc[-1]
            
            # যদি এরপরেও এটি সিরিজ থাকে (বিরল ক্ষেত্রে), তবে প্রথম ভ্যালু নেওয়া
            if isinstance(last_close, pd.Series):
                current_price = float(last_close.iloc[0])
            else:
                current_price = float(last_close)
                
            display_name = asset.replace('=X', '').replace('-', '')
            
            # ৪. উইন-লস ক্যালকুলেশন
            if "CALL" in direction:
                win = current_price > entry_price
            else:
                win = current_price < entry_price
                
            status = "✅ WIN" if win else "❌ LOSS"
            
            res_msg = (
                f"📝 *SIGNAL RESULT: {display_name}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Status: *{status}*\n"
                f"Entry Price: {entry_price:.5f}\n"
                f"Closing Price: {current_price:.5f}\n"
                f"{'Target Hit!' if win else 'Try 1st Step Martingale'}"
            )
            send_telegram_msg(res_msg)
            print(f"🎯 Result Sent: {display_name} -> {status}")
            
        else:
            print(f"⚠️ No data found for {asset} results.")
            
    except Exception as e:
        print(f"❌ Result Tracker Error for {asset}: {str(e)}")

def process_asset(symbol):
    try:
        tf = config.get('timeframe', '1m')
        data = yf.download(tickers=symbol, period='2d', interval=tf, progress=False)
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
    print(f"🚀 Bot Started | Result Tracker Fixed")
    
    last_signal_time = {}
    result_executor = ThreadPoolExecutor(max_workers=20)

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
                        msg = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {display_name}\n"
                            f"🚀 *DIRECTION:* {signal}\n"
                            f"🎯 *QUALITY:* {quality_pct}\n"
                            f"⏰ *TIMEFRAME:* {tf_label}\n"
                            f"⏳ *EXPIRY:* {exp_label}\n"
                            f"🕒 *TIME (BD):* {now.strftime('%H:%M:%S')}\n\n"
                            f"⚠️ *Note:* Use 1st Step Martingale"
                        )
                        send_telegram_msg(msg)
                        last_signal_time[asset] = current_min
                        
                        # রেজাল্ট চেক করার জন্য থ্রেড পাঠানো
                        result_executor.submit(check_result, float(entry_price), direction=signal, asset=asset)

            time.sleep(5) 
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
