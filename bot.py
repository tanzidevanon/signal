import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import json
import pytz
import requests
import os
from datetime import datetime

# ১. কনফিগ ফাইল লোড করার ফাংশন
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

# প্রাথমিক কনফিগ সেটআপ
config = load_config()
TZ = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))

# ২. টেলিগ্রামে সিগন্যাল পাঠানোর ফাংশন
def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ৩. সিগন্যাল লজিক (ইন্ডিকেটর এনালাইসিস)
def get_signal(symbol):
    try:
        # ১ মিনিটের ডাটা সংগ্রহ (Yahoo Finance)
        data = yf.download(tickers=symbol, period='1d', interval='1m', progress=False)
        
        if data.empty or len(data) < 50:
            return None
        
        df = data.copy()
        
        # কলাম নাম ঠিক করা (yfinance মাঝে মাঝে Multi-index দিতে পারে)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # --- ইন্ডিকেটর ক্যালকুলেশন ---
        # RSI (7 পিরিয়ড - দ্রুত সিগন্যালের জন্য)
        df['rsi'] = ta.rsi(df['Close'], length=7)
        
        # Bollinger Bands (20, 2)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df['bb_low'] = bb['BBL_20_2.0']
        df['bb_up'] = bb['BBU_20_2.0']
        
        # EMA 200 (ট্রেন্ড ফিল্টারের জন্য)
        df['ema_200'] = ta.ema(df['Close'], length=200)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        quality = "NORMAL"

        # --- সিগন্যাল কন্ডিশন (Robust Rules) ---
        
        # CALL (UP) লজিক: 
        # ১. প্রাইস নিচের ব্যান্ডের নিচে বা সমান। ২. RSI ৩০ এর নিচে (Oversold)।
        if last['Close'] <= last['bb_low'] and last['rsi'] < 35:
            signal = "🟢 CALL (UP)"
            # যদি প্রাইস EMA 200 এর উপরে থাকে তবে এটি স্ট্রং আপট্রেন্ড (High Quality)
            if last['Close'] > last['ema_200']:
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"

        # PUT (DOWN) লজিক:
        # ১. প্রাইস উপরের ব্যান্ডের উপরে বা সমান। ২. RSI ৭০ এর উপরে (Overbought)।
        elif last['Close'] >= last['bb_up'] and last['rsi'] > 65:
            signal = "🔴 PUT (DOWN)"
            # যদি প্রাইস EMA 200 এর নিচে থাকে তবে এটি স্ট্রং ডাউনট্রেন্ড (High Quality)
            if last['Close'] < last['ema_200']:
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"
            
        return signal, quality
    except Exception as e:
        print(f"Analysis Error for {symbol}: {e}")
        return None

# ৪. মেইন লুপ (২৪/৭ রান হবে)
def main():
    print(f"✅ Bot Started at {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Monitoring {len(config['assets'])} assets...")
    
    last_signal_time = {}

    while True:
        try:
            # গিটহাব থেকে পুল করার পর কনফিগ আপডেট পেতে প্রতিবার লোড করা হচ্ছে
            current_config = load_config()
            assets = current_config['assets']
            
            for asset in assets:
                if asset not in last_signal_time:
                    last_signal_time[asset] = ""
                
                # এনালাইসিস করা
                res = get_signal(asset)
                
                # API Rate Limit এড়াতে সামান্য বিরতি
                time.sleep(1.2)
                
                if res:
                    signal, quality = res
                    if signal:
                        now = datetime.now(TZ)
                        current_min = now.strftime('%H:%M')
                        
                        # একই মিনিটে বারবার সিগন্যাল পাঠানো বন্ধ করা
                        if last_signal_time[asset] != current_min:
                            display_name = asset.replace('=X', '').replace('-', '')
                            
                            msg = (
                                f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"🚀 *DIRECTION:* {signal}\n"
                                f"🎯 *QUALITY:* {quality}\n"
                                f"⏰ *TIMEFRAME:* 1 MIN\n"
                                f"⏳ *EXPIRY:* 1 MIN\n"
                                f"🕒 *TIME (BD):* {current_min}\n\n"
                                f"⚠️ *Note:* Use 1st Step Martingale if needed."
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
                            print(f"Sent signal for {display_name} at {current_min}")
            
            # একটি ফুল সাইকেল শেষ হওয়ার পর ২০ সেকেন্ড বিরতি
            time.sleep(20)
            
        except Exception as e:
            print(f"Main Loop Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
