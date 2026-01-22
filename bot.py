import yfinance as yf
import time
import json
import pytz
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
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
    try: requests.get(url, timeout=10)
    except: pass

def check_result(asset, entry_price, direction, signal_time):
    """
    signal_time: সিগন্যাল দেওয়ার সময় (datetime object)
    """
    display_name = asset.replace('=X', '').replace('-', '')
    print(f"⌛ Result checking started for {display_name}...")
    
    # ১ মিনিট ট্রেড শেষ হওয়ার জন্য এবং Yahoo ডাটা আপলোড হওয়ার জন্য ১০০ সেকেন্ড অপেক্ষা
    time.sleep(100) 
    
    for attempt in range(3): # ৩ বার চেষ্টা করবে ডাটা না পেলে
        try:
            # গত ৫ মিনিটের ডাটা ফেচ করা যাতে সিগন্যাল টাইমটি খুঁজে পাওয়া যায়
            data = yf.download(tickers=asset, period='1d', interval='1m', progress=False)
            
            if data is not None and not data.empty:
                df = data.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [str(col).lower() for col in df.columns]
                
                # সিগন্যাল যে মিনিটে দেওয়া হয়েছে তার ক্লোজিং প্রাইস খুঁজুন
                # আমরা সিগন্যাল টাইমের ১ মিনিট পরের ক্যান্ডেল চেক করব (ট্রেড এক্সপায়ারি)
                target_time = signal_time.replace(second=0, microsecond=0)
                
                # ডাটাফ্রেমের ইনডেক্সকে লোকাল টাইমে কনভার্ট করা (Asia/Dhaka)
                df.index = df.index.tz_convert('Asia/Dhaka')
                
                # টার্গেট সময়ের ক্যান্ডেলটি খুঁজে বের করা
                if target_time in df.index:
                    current_price = float(df.loc[target_time, 'close'])
                    
                    if "CALL" in direction:
                        win = current_price > entry_price
                    else:
                        win = current_price < entry_price
                        
                    status = "✅ WIN" if win else "❌ LOSS"
                    
                    res_msg = (
                        f"📝 *SIGNAL RESULT: {display_name}*\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"Status: *{status}*\n"
                        f"Entry: {entry_price:.5f}\n"
                        f"Close: {current_price:.5f}\n"
                        f"{'Target Hit!' if win else 'MTG 1 Step Recommended'}"
                    )
                    send_telegram_msg(res_msg)
                    print(f"🎯 Result Sent: {display_name} -> {status}")
                    return # কাজ শেষ হলে ফাংশন থেকে বের হয়ে যাবে
                else:
                    print(f"⚠️ Candle for {target_time} not found in Yahoo data yet. Retrying in 20s...")
            
        except Exception as e:
            print(f"❌ Error for {asset} (Attempt {attempt+1}): {e}")
        
        time.sleep(20) # ডাটা না পাওয়া গেলে ২০ সেকেন্ড পর আবার ট্রাই করবে

def process_asset(symbol):
    try:
        data = yf.download(tickers=symbol, period='2d', interval=config.get('timeframe', '1m'), progress=False)
        if data.empty or len(data) < 100: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except: return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Bot Running | Advanced Result Tracker Active")
    
    last_signal_time = {}
    result_executor = ThreadPoolExecutor(max_workers=25)

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            
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
                            f"⏰ *TIMEFRAME:* {current_config['timeframe']}\n"
                            f"⏳ *EXPIRY:* {current_config['expiry']}\n"
                            f"🕒 *TIME (BD):* {now.strftime('%H:%M:%S')}\n\n"
                            f"⚠️ *Note:* Use 1st Step Martingale"
                        )
                        send_telegram_msg(msg)
                        last_signal_time[asset] = current_min
                        
                        # এখন সিগন্যাল টাইমসহ রেজাল্ট চেকারে পাঠানো হচ্ছে
                        result_executor.submit(check_result, asset, float(entry_price), signal, now)

            time.sleep(5) 
        except Exception as e:
            print(f"Main Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
