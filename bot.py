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

# রেজাল্ট চেক করার ফাংশন
def check_result(asset, entry_price, direction, entry_time):
    time.sleep(65) # ১ মিনিট এক্সপায়ারির জন্য অপেক্ষা
    try:
        data = yf.download(tickers=asset, period='1d', interval='1m', progress=False)
        current_price = data['Close'].iloc[-1]
        display_name = asset.replace('=X', '').replace('-', '')
        
        result_msg = ""
        if "CALL" in direction:
            if current_price > entry_price: result_msg = f"✅ *WIN* \n📊 {display_name} Success!"
            else: result_msg = f"❌ *LOSS* \n📊 {display_name} | Use Martingale"
        else:
            if current_price < entry_price: result_msg = f"✅ *WIN* \n📊 {display_name} Success!"
            else: result_msg = f"❌ *LOSS* \n📊 {display_name} | Use Martingale"
            
        send_telegram_msg(f"📝 *SIGNAL RESULT*\n\n{result_msg}\n💰 Entry: {entry_price:.5f}\n📉 Exit: {current_price:.5f}")
    except: pass

def process_asset(symbol):
    try:
        tf = config.get('timeframe', '1m')
        data = yf.download(tickers=symbol, period='2d', interval=tf, progress=False)
        if data.empty or len(data) < 50: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except: return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Premium Bot with Result Tracker Active")
    
    last_signal_time = {}
    executor = ThreadPoolExecutor(max_workers=10)

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            tf_label = current_config.get('timeframe', '1m')
            exp_label = current_config.get('expiry', '1 min')
            
            # স্ক্যানিং
            with ThreadPoolExecutor(max_workers=10) as scan_executor:
                results = list(scan_executor.map(process_asset, assets))
            
            for i, res in enumerate(results):
                asset = assets[i]
                if res:
                    signal, quality, entry_price = res
                    if signal:
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
                                f"⚠️ *Note:* Use 1st Step Martingale"
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
                            
                            # রেজাল্ট চেক করার জন্য আলাদা থ্রেড চালানো
                            executor.submit(check_result, asset, entry_price, signal, now)

            time.sleep(5) 
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    main()
