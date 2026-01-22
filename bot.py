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
    try: requests.get(url, timeout=10)
    except: pass

def check_result(asset, entry_price, direction):
    time.sleep(62) # ১ মিনিট পর রেজাল্ট চেক
    try:
        data = yf.download(tickers=asset, period='1d', interval='1m', progress=False)
        current_price = data['Close'].iloc[-1]
        display_name = asset.replace('=X', '').replace('-', '')
        win = (current_price > entry_price) if "CALL" in direction else (current_price < entry_price)
        status = "✅ WIN" if win else "❌ LOSS"
        msg = f"📝 *RESULT: {display_name}*\n━━━━━━━━━━━━━━━\nStatus: *{status}*\nEntry: {entry_price:.5f}\nExit: {current_price:.5f}"
        send_telegram_msg(msg)
    except: pass

def process_asset(symbol):
    try:
        data = yf.download(tickers=symbol, period='1d', interval=config.get('timeframe', '1m'), progress=False)
        if data.empty: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df)
    except: return None

def main():
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    print(f"🚀 Bot Running | Quality: Balanced | Result Tracker: ON")
    
    last_signal_time = {}
    res_executor = ThreadPoolExecutor(max_workers=5)

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            
            # দ্রুত প্যারালাল স্ক্যান
            with ThreadPoolExecutor(max_workers=15) as executor:
                results = list(executor.map(process_asset, assets))
            
            for i, res in enumerate(results):
                if res and res[0]:
                    asset = assets[i]
                    signal, quality, entry_price = res
                    now = datetime.now(user_tz)
                    current_min = now.strftime('%H:%M')
                    
                    if last_signal_time.get(asset) != current_min:
                        display_name = asset.replace('=X', '').replace('-', '')
                        msg = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {display_name}\n"
                            f"🚀 *DIRECTION:* {signal}\n"
                            f"🎯 *QUALITY:* {quality}\n"
                            f"⏰ *TIMEFRAME:* {current_config['timeframe']}\n"
                            f"⏳ *EXPIRY:* {current_config['expiry']}\n"
                            f"🕒 *TIME (BD):* {now.strftime('%H:%M:%S')}\n\n"
                            f"⚠️ *Note:* 1st Step Martingale"
                        )
                        send_telegram_msg(msg)
                        last_signal_time[asset] = current_min
                        res_executor.submit(check_result, asset, entry_price, signal)

            time.sleep(5) # প্রতি ৫ সেকেন্ড পরপর চেক করবে
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    main()
