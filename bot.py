import time
import json
import pytz
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime
from tvdatafeed import TvDatafeed, Interval

# কনফিগ লোড
def load_config():
    with open('config.json') as f:
        return json.load(f)

config = load_config()
tv = TvDatafeed()
TZ = pytz.timezone(config['timezone'])

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{config['telegram_token']}/sendMessage?chat_id={config['chat_id']}&text={message}&parse_mode=Markdown"
    try: requests.get(url)
    except: pass

def get_signal(symbol):
    try:
        # TradingView থেকে ডাটা আনা (১ মিনিটের ১০০টি ক্যান্ডেল)
        df = tv.get_hist(symbol=symbol.split(':')[-1], exchange=symbol.split(':')[0], interval=Interval.in_1_minute, n_bars=100)
        if df is None: return None
        
        # ইন্ডিকেটর ক্যালকুলেশন
        df['rsi'] = ta.rsi(df['close'], length=7)
        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_low'] = bb['BBL_20_2.0']
        df['bb_up'] = bb['BBU_20_2.0']
        df['ema_20'] = ta.ema(df['close'], length=20)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        quality = "Normal"

        # CALL Logic
        if last['close'] <= last['bb_low'] and last['rsi'] < 35:
            signal = "🟢 CALL (UP)"
            if last['close'] > last['ema_20']: quality = "⭐⭐⭐ HIGH"
            else: quality = "⭐⭐ NORMAL"

        # PUT Logic
        elif last['close'] >= last['bb_up'] and last['rsi'] > 65:
            signal = "🔴 PUT (DOWN)"
            if last['close'] < last['ema_20']: quality = "⭐⭐⭐ HIGH"
            else: quality = "⭐⭐ NORMAL"
            
        return signal, quality
    except:
        return None

def main():
    print("Bot is running 24/7 on Ubuntu...")
    last_signal_time = {}

    while True:
        current_config = load_config()
        for asset in current_config['assets']:
            if asset not in last_signal_time: last_signal_time[asset] = 0
            
            res = get_signal(asset)
            if res:
                signal, quality = res
                now = datetime.now(TZ)
                current_min = now.strftime('%H:%M')
                
                if last_signal_time[asset] != current_min:
                    msg = (
                        f"📊 *ASSET:* {asset.split(':')[-1]}\n"
                        f"🚀 *SIGNAL:* {signal}\n"
                        f"🎯 *QUALITY:* {quality}\n"
                        f"⏰ *TF:* 1 MIN | *EXP:* 1 MIN\n"
                        f"🕒 *TIME (BD):* {current_min}\n"
                        f"⚠️ *Note:* Use 1st Step Martingale"
                    )
                    send_telegram_msg(msg)
                    last_signal_time[asset] = current_min
        
        time.sleep(10)

if __name__ == "__main__":
    main()
