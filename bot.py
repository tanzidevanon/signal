import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import json
import pytz
import requests
from datetime import datetime

# কনফিগ লোড
def load_config():
    with open('config.json') as f:
        return json.load(f)

config = load_config()
TZ = pytz.timezone(config['timezone'])

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{config['telegram_token']}/sendMessage?chat_id={config['chat_id']}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url, timeout=10)
    except:
        pass

def get_signal(symbol):
    try:
        # Yahoo Finance থেকে ডাটা সংগ্রহ (১ মিনিটের ক্যান্ডেল)
        data = yf.download(tickers=symbol, period='1d', interval='1m', progress=False)
        
        if data.empty or len(data) < 30:
            return None
        
        df = data.copy()
        
        # ইন্ডিকেটর ক্যালকুলেশন
        df['rsi'] = ta.rsi(df['Close'], length=7)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df['bb_low'] = bb['BBL_20_2.0']
        df['bb_up'] = bb['BBU_20_2.0']
        df['ema_200'] = ta.ema(df['Close'], length=200)
        
        last = df.iloc[-1]
        
        signal = None
        quality = "Normal"

        # CALL Logic
        if last['Close'] <= last['bb_low'] and last['rsi'] < 35:
            signal = "🟢 CALL (UP)"
            if last['Close'] > last['ema_200']: quality = "⭐⭐⭐ HIGH"
            else: quality = "⭐⭐ NORMAL"

        # PUT Logic
        elif last['Close'] >= last['bb_up'] and last['rsi'] > 65:
            signal = "🔴 PUT (DOWN)"
            if last['Close'] < last['ema_200']: quality = "⭐⭐⭐ HIGH"
            else: quality = "⭐⭐ NORMAL"
            
        return signal, quality
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def main():
    print("Bot is running with Yahoo Finance Data (24/7)...")
    last_signal_time = {}

    while True:
        try:
            current_config = load_config()
            assets = current_config['assets']
            
            for asset in assets:
                if asset not in last_signal_time:
                    last_signal_time[asset] = ""
                
                res = get_signal(asset)
                
                if res:
                    signal, quality = res
                    if signal:
                        now = datetime.now(TZ)
                        current_min = now.strftime('%H:%M')
                        
                        if last_signal_time[asset] != current_min:
                            # ডিসপ্লে নাম সুন্দর করা (যেমন: EURUSD=X থেকে EURUSD)
                            display_name = asset.replace('=X', '').replace('-', '')
                            
                            msg = (
                                f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                                f"📊 *ASSET:* {display_name}\n"
                                f"🚀 *SIGNAL:* {signal}\n"
                                f"🎯 *QUALITY:* {quality}\n"
                                f"⏰ *TF:* 1 MIN | *EXP:* 1 MIN\n"
                                f"🕒 *TIME (BD):* {current_min}\n\n"
                                f"⚠️ *Note:* Use 1st Step Martingale if needed."
                            )
                            send_telegram_msg(msg)
                            last_signal_time[asset] = current_min
            
            # প্রতি লুপ শেষে ৩০ সেকেন্ড বিরতি
            time.sleep(30)
            
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
