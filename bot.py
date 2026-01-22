import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import json
import pytz
import requests
import os
from datetime import datetime

# ১. কনফিগ ফাইল লোড
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()
TZ = pytz.timezone(config.get('timezone', 'Asia/Dhaka'))

def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ২. সিগন্যাল লজিক (Error Proof)
def get_signal(symbol):
    try:
        # যথেষ্ট পরিমাণ ডাটা নামানো (EMA 200 এর জন্য period='2d' নিরাপদ)
        data = yf.download(tickers=symbol, period='2d', interval='1m', progress=False)
        
        if data.empty or len(data) < 201:
            return None
        
        df = data.copy()
        
        # Yahoo Finance Multi-index কলাম ফিক্স
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # কলাম নাম পরিষ্কার করা
        df.columns = [str(col).lower() for col in df.columns]

        # --- ইন্ডিকেটর ক্যালকুলেশন ---
        # RSI 7
        df['rsi'] = ta.rsi(df['close'], length=7)
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        
        # EMA 200
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        # কলামগুলো মেইন ফ্রেমে জোড়া লাগানো
        df = pd.concat([df, bb], axis=1)

        # কলামগুলোর নাম যাই হোক না কেন, পজিশন অনুযায়ী ডাটা নেওয়া
        # BB_Lower সাধারণত ১ম কলাম, BB_Upper ৩য় কলাম হয়
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        
        last = df.iloc[-1]
        
        signal = None
        quality = "NORMAL"

        # কন্ডিশন চেক
        price = last['close']
        rsi = last['rsi']
        ema = last['ema_200']
        lower_band = last[bbl_col]
        upper_band = last[bbu_col]

        # CALL (UP)
        if price <= lower_band and rsi < 35:
            signal = "🟢 CALL (UP)"
            quality = "⭐⭐⭐ HIGH" if price > ema else "⭐⭐ NORMAL"

        # PUT (DOWN)
        elif price >= upper_band and rsi > 65:
            signal = "🔴 PUT (DOWN)"
            quality = "⭐⭐⭐ HIGH" if price < ema else "⭐⭐ NORMAL"
            
        return signal, quality
    except Exception as e:
        # এরর প্রিন্ট করবে যাতে বোঝা যায় ঠিক কী সমস্যা
        print(f"Analysis Error for {symbol}: {str(e)}")
        return None

# ৩. মেইন লুপ
def main():
    print(f"✅ Bot Started Successfully at {datetime.now(TZ).strftime('%H:%M:%S')}")
    print(f"📊 Monitoring {len(config['assets'])} assets with Yahoo Finance...")
    
    last_signal_time = {}

    while True:
        try:
            # কনফিগ রিলোড
            current_config = load_config()
            assets = current_config['assets']
            
            for asset in assets:
                if asset not in last_signal_time:
                    last_signal_time[asset] = ""
                
                res = get_signal(asset)
                
                # ১.৫ সেকেন্ড গ্যাপ যাতে সার্ভার ব্লক না করে
                time.sleep(1.5)
                
                if res:
                    signal, quality = res
                    if signal:
                        now = datetime.now(TZ)
                        current_min = now.strftime('%H:%M')
                        
                        if last_signal_time[asset] != current_min:
                            display_name = asset.replace('=X', '').replace('-', '')
                            
                            msg = (
                                f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"🚀 *DIRECTION:* {signal}\n"
                                f"🎯 *QUALITY:* {quality}\n"
                                f"⏰ *TF:* 1 MIN | *EXP:* 1 MIN\n"
                                f"🕒 *TIME (BD):* {current_min}\n\n"
                                f"⚠️ *Note:* Use 1st Step Martingale"
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
                            print(f"✅ Signal Sent: {display_name} - {signal}")
            
            # সাইকেল শেষে ২০ সেকেন্ড বিরতি
            time.sleep(20)
            
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(20)

if __name__ == "__main__":
    main()
