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

# গ্লোবাল কনফিগ
config = load_config()

# টেলিগ্রাম মেসেজ ফাংশন
def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url, timeout=10)
    except:
        pass

# ডাটা প্রসেস ফাংশন
def process_asset(symbol):
    try:
        # কনফিগ থেকে টাইমফ্রেম নেওয়া (যেমন: '1m', '5m')
        tf = config.get('timeframe', '1m')
        
        # টাইমফ্রেম অনুযায়ী পিরিয়ড নির্ধারণ
        period_val = '2d' if tf == '1m' else '5d'
        
        data = yf.download(tickers=symbol, period=period_val, interval=tf, progress=False)
        if data.empty or len(data) < 201: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]

        return get_trading_signal(df)
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return None

def main():
    # টাইমজোন সেটআপ (কনফিগ থেকে)
    user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
    
    print(f"🚀 Engine Started | Timezone: {user_tz} | TF: {config['timeframe']}")
    
    last_signal_time = {}

    while True:
        try:
            # প্রতি লুপে লেটেস্ট কনফিগ চেক (অ্যাসেট বা এক্সপায়ারি চেঞ্জের জন্য)
            current_config = load_config()
            assets = current_config['assets']
            tf_label = current_config.get('timeframe', '1m')
            exp_label = current_config.get('expiry', '1 min')
            
            for asset in assets:
                if asset not in last_signal_time: last_signal_time[asset] = ""
                
                res = process_asset(asset)
                time.sleep(1.2) # API Safety
                
                if res:
                    signal, quality = res
                    if signal:
                        # বর্তমান সময় সেকেন্ডসহ (HH:MM:SS)
                        now = datetime.now(user_tz)
                        current_time_str = now.strftime('%H:%M:%S')
                        current_min = now.strftime('%H:%M') # একই মিনিটে বারবার মেসেজ না পাঠানোর জন্য
                        
                        if last_signal_time[asset] != current_min:
                            display_name = asset.replace('=X', '').replace('-', '')
                            
                            # ডাইনামিক মেসেজ (সব কনফিগ থেকে আসবে)
                            msg = (
                                f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"🚀 *DIRECTION:* {signal}\n"
                                f"🎯 *QUALITY:* {quality}\n"
                                f"⏰ *TIMEFRAME:* {tf_label}\n"
                                f"⏳ *EXPIRY:* {exp_label}\n"
                                f"🕒 *TIME (BD):* {current_time_str}\n\n"
                                f"⚠️ *Note:* Use 1st Step Martingale"
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
                            print(f"[{current_time_str}] Signal Sent: {display_name}")
            
            time.sleep(15)
        except Exception as e:
            print(f"Engine Loop Error: {e}")
            time.sleep(20)

if __name__ == "__main__":
    main()
