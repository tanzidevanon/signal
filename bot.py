import time
import json
import pytz
import requests
from datetime import datetime
from tradingview_ta import TA_Handler, Interval

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

def get_signal(asset_string):
    try:
        # অ্যাসেট ফরম্যাট: "EXCHANGE:SYMBOL" -> "FX:EURUSD"
        parts = asset_string.split(":")
        exchange = parts[0]
        symbol = parts[1]

        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener="forex", # ক্রিপ্টো হলে "crypto" হবে
            interval=Interval.INTERVAL_1_MINUTE
        )

        analysis = handler.get_analysis()
        indicators = analysis.indicators
        
        # Robust Logic (RSI, Bollinger Bands, and EMA)
        rsi = indicators["RSI"]
        sma = indicators["SMA10"] # Simple Moving Average
        close = indicators["close"]
        bb_upper = indicators["BB.upper"]
        bb_lower = indicators["BB.lower"]
        ema200 = indicators["EMA200"]

        signal = None
        quality = "Normal"

        # CALL Strategy: Price below BB lower, RSI < 30 (Oversold)
        if close <= bb_lower and rsi < 35:
            signal = "🟢 CALL (UP)"
            if close > ema200: # Trend is up
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"

        # PUT Strategy: Price above BB upper, RSI > 70 (Overbought)
        elif close >= bb_upper and rsi > 65:
            signal = "🔴 PUT (DOWN)"
            if close < ema200: # Trend is down
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"

        return signal, quality
    except Exception as e:
        print(f"Error analyzing {asset_string}: {e}")
        return None

def main():
    print("Robust Bot is running 24/7...")
    last_signal_time = {}

    while True:
        try:
            current_config = load_config()
            for asset in current_config['assets']:
                if asset not in last_signal_time:
                    last_signal_time[asset] = ""
                
                res = get_signal(asset)
                if res:
                    signal, quality = res
                    current_min = datetime.now(TZ).strftime('%H:%M')
                    
                    if last_signal_time[asset] != current_min:
                        msg = (
                            f"🔔 *QUOTEX PREMIUM SIGNAL*\n\n"
                            f"📊 *ASSET:* {asset.split(':')[-1]}\n"
                            f"🚀 *SIGNAL:* {signal}\n"
                            f"🎯 *QUALITY:* {quality}\n"
                            f"⏰ *TF:* 1 MIN | *EXP:* 1 MIN\n"
                            f"🕒 *TIME (BD):* {current_min}\n\n"
                            f"⚠️ *Note:* Use 1st Step Martingale if needed."
                        )
                        send_telegram_msg(msg)
                        last_signal_time[asset] = current_min
            
            time.sleep(10) # ১০ সেকেন্ড পর পর চেক করবে
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
