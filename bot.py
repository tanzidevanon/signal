import yfinance as yf
import time, json, pytz, requests, os
import pandas as pd
from datetime import datetime
from strategy import get_trading_signal

def load_config():
    with open('config.json', 'r') as f: return json.load(f)

config = load_config()
user_tz = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))
TOKEN = config['telegram_token']
CHAT_ID = config['chat_id']

# মেমোরিতে অ্যালার্ট মেসেজ আইডি সেভ রাখার জন্য
active_alerts = {} 

def send_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}&parse_mode=Markdown"
    res = requests.get(url).json()
    return res['result']['message_id'] if res['ok'] else None

def edit_msg(msg_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText?chat_id={CHAT_ID}&message_id={msg_id}&text={text}&parse_mode=Markdown"
    requests.get(url)

def process_asset(symbol, is_pre=False):
    try:
        tf = config.get('timeframe', '1m')
        data = yf.download(tickers=symbol, period='2d', interval=tf, progress=False)
        if data.empty: return None
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return get_trading_signal(df, is_pre_signal=is_pre)
    except: return None

def main():
    print("🚀 Smart Edit Bot Started...")
    last_min = -1

    while True:
        now = datetime.now(user_tz)
        
        # --- ৪৫ সেকেন্ডে প্রি-অ্যালার্ট ---
        if now.second == 45 and now.minute != last_min:
            for asset in config['assets']:
                direction, prob = process_asset(asset, is_pre=True)
                if direction:
                    display_name = asset.replace('=X', '')
                    text = (f"⏳ *PRE-SIGNAL ALERT*\n"
                            f"📊 Asset: {display_name}\n"
                            f"🚀 Target: {direction}\n"
                            f"🔥 Probability: {prob}\n"
                            f"🕒 Wait for 15s...")
                    msg_id = send_msg(text)
                    active_alerts[asset] = msg_id
            last_min = now.minute

        # --- ০০ সেকেন্ডে এডিট বা ডিলিট ---
        if now.second == 0:
            for asset, msg_id in list(active_alerts.items()):
                signal, quality = process_asset(asset, is_pre=False)
                display_name = asset.replace('=X', '')
                
                if signal:
                    text = (f"🔥 *TRADE NOW - ENTRY* 🔥\n"
                            f"📊 Asset: {display_name}\n"
                            f"🚀 Direction: {signal}\n"
                            f"🎯 Quality: {quality}\n"
                            f"⏳ Duration: {config['expiry']}\n"
                            f"🕒 BD Time: {now.strftime('%H:%M:%S')}")
                    edit_msg(msg_id, text)
                else:
                    # যদি লজিক না মিলে তবে মেসেজটি এডিট করে ক্যান্সেল দেখাবে
                    text = f"❌ *SIGNAL CANCELLED*\n📊 Asset: {display_name}\n💡 Reason: Condition not met."
                    edit_msg(msg_id, text)
            
            active_alerts.clear() # লুপ শেষে মেমোরি ক্লিয়ার
            time.sleep(1)

        time.sleep(0.5)

if __name__ == "__main__":
    main()
