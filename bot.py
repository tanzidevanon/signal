# --- START OF FILE bot.py (MODIFIED) ---

import yfinance as yf
import time
import json
import pytz
import requests
import os
import pandas as pd
from datetime import datetime, timedelta
from strategy import get_trading_signal
import threading # New import for threading

# কনফিগ লোড
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

# গ্লোবাল কনফিগ
config = load_config()

# টেলিগ্রাম মেসেজ ফাংশন (Modified to return message_id)
def send_telegram_msg(message):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()
        if result['ok']:
            return result['result']['message_id']
    except requests.exceptions.RequestException as e:
        print(f"Telegram send error: {e}")
    return None

# টেলিগ্রাম মেসেজ এডিট ফাংশন (New function)
def edit_telegram_msg(message_id, new_text):
    token = config['telegram_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': new_text,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Telegram edit error for message_id {message_id}: {e}")

# helper function to convert expiry string to seconds
def get_expiry_seconds(expiry_str):
    parts = expiry_str.split()
    if len(parts) != 2:
        return 60 # default to 1 minute if format is wrong
    
    value = int(parts[0])
    unit = parts[1].lower()
    
    if "min" in unit:
        return value * 60
    elif "sec" in unit:
        return value
    elif "hour" in unit:
        return value * 3600
    else:
        return 60 # default to 1 minute

# ডাটা প্রসেস ফাংশন
def process_asset(symbol, tf, period_val): # Added tf, period_val as args
    try:
        data = yf.download(tickers=symbol, period=period_val, interval=tf, progress=False)
        if data.empty or len(data) < 201: return None # Ensure enough data for indicators
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]

        return get_trading_signal(df)
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return None

# New function to check signal result after expiry
def check_signal_result(message_id, asset, signal_datetime_utc, signal_direction, expiry_seconds, initial_message_text, user_tz_name):
    print(f"Checking result for {asset} at {signal_datetime_utc.strftime('%H:%M:%S')} with expiry {expiry_seconds}s...")
    
    # Wait for the expiry period
    time.sleep(expiry_seconds)

    try:
        # Re-fetch data for the specific interval to get the closing price after expiry
        # We need to make sure we fetch data that includes the candle *after* the signal
        # For a 1-minute candle, if signal is at HH:MM:00, expiry is at HH:MM:59.
        # The result candle will be the one that starts at HH:MM+1:00
        
        # Determine appropriate period and interval for result checking
        tf = config.get('timeframe', '1m')
        # We need at least two candles after the signal for comparison (the signal candle itself + the expiry candle)
        # If the signal is at T, and expiry is 1m, we need data up to T+1m
        # yfinance interval fetches data where each row represents the candle *starting* at that time.
        # So for a signal at 10:00:00 (1m candle), its close is at 10:00:59.
        # The expiry for 1m means we need the close of the 10:01:00 candle.
        
        # To reliably get the candle after expiry, fetch a small window
        # For a 1-minute timeframe, we need at least 2 minutes of data past the signal time
        fetch_start_time = signal_datetime_utc - timedelta(minutes=2) # Get some context before
        fetch_end_time = signal_datetime_utc + timedelta(minutes=5) # Ensure we cover the expiry candle
        
        # Convert to epoch for yfinance period parameter if needed, or use datetime directly
        # For yfinance, `start` and `end` parameters are better for specific timeframes.
        
        data_for_result = yf.download(
            tickers=asset,
            start=fetch_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end=fetch_end_time.strftime('%Y-%m-%d %H:%M:%S'),
            interval=tf,
            progress=False
        )

        if data_for_result.empty:
            print(f"No data for result check of {asset} around {signal_datetime_utc}")
            return

        df_result = data_for_result.copy()
        if isinstance(df_result.columns, pd.MultiIndex):
            df_result.columns = df_result.columns.get_level_values(0)
        df_result.columns = [str(col).lower() for col in df_result.columns]
        
        # Find the candle *containing* the signal time (or the closest one before it if exact match isn't there)
        # The signal_datetime_utc should ideally be the start of the candle for yfinance.
        # If the signal was generated at HH:MM:SS, and interval is 1m, the candle starts at HH:MM:00.
        
        # We need to find the close price of the candle that started *at or just before* signal_datetime_utc
        # And the close price of the candle that started *expiry_seconds* after that.
        
        # The easiest approach is to find the candle that aligns with the signal, then find the one 'expiry_seconds' later.
        # For '1m' timeframe, if signal_datetime_utc is 10:00:05, the relevant candle starts at 10:00:00.
        # We need its close. Then for 1 min expiry, we need the close of the candle starting at 10:01:00.
        
        # Let's align signal_datetime_utc to the start of its minute for '1m' interval
        signal_candle_start_time = signal_datetime_utc.replace(second=0, microsecond=0)
        
        # Find the signal candle
        signal_candle_df = df_result[df_result.index == signal_candle_start_time]
        if signal_candle_df.empty:
             # If exact match not found, try to find the last candle before or at the signal time
            signal_candle_df = df_result[df_result.index <= signal_candle_start_time].iloc[[-1]]
        
        if signal_candle_df.empty:
            print(f"Could not find signal candle for {asset} at {signal_datetime_start_time}")
            return
            
        initial_close_price = signal_candle_df['close'].iloc[0]
        
        # Calculate the target expiry candle start time
        expiry_candle_start_time = signal_candle_start_time + timedelta(seconds=expiry_seconds)
        
        # Find the expiry candle
        expiry_candle_df = df_result[df_result.index == expiry_candle_start_time]
        if expiry_candle_df.empty:
             # If exact match not found, try to find the first candle after or at expiry time
            expiry_candle_df = df_result[df_result.index >= expiry_candle_start_time].iloc[[0]]
            
        if expiry_candle_df.empty:
            print(f"Could not find expiry candle for {asset} at {expiry_candle_start_time}")
            return

        final_close_price = expiry_candle_df['close'].iloc[0]
        
        result_str = ""
        result_emoji = ""
        
        if "CALL" in signal_direction: # Expect price to go UP
            if final_close_price > initial_close_price:
                result_str = "✅ *WIN*"
                result_emoji = "✅"
            else:
                result_str = "❌ *LOSS*"
                result_emoji = "❌"
        elif "PUT" in signal_direction: # Expect price to go DOWN
            if final_close_price < initial_close_price:
                result_str = "✅ *WIN*"
                result_emoji = "✅"
            else:
                result_str = "❌ *LOSS*"
                result_emoji = "❌"
        
        # Reconstruct the message with the result
        user_tz = pytz.timezone(user_tz_name)
        now_bd = datetime.now(user_tz)
        current_time_str_bd = now_bd.strftime('%H:%M:%S')

        # Add the result to the initial message text
        updated_message = f"{initial_message_text}\n\n📊 *RESULT:* {result_str} {result_emoji}\n_Checked at {current_time_str_bd} BD Time_"
        
        edit_telegram_msg(message_id, updated_message)
        print(f"Result for {asset} ({signal_direction}) at {signal_datetime_utc.strftime('%H:%M:%S')} : {result_str}")

    except Exception as e:
        print(f"Error checking signal result for {asset} (message_id {message_id}): {e}")

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
            telegram_token = current_config['telegram_token'] # Ensure token is loaded for threads if needed
            chat_id = current_config['chat_id']
            
            expiry_seconds = get_expiry_seconds(exp_label)

            for asset in assets:
                if asset not in last_signal_time: last_signal_time[asset] = ""
                
                # Use current_config values for processing
                res = process_asset(asset, tf_label, '5d' if tf_label != '1m' else '2d') # Pass tf and period_val
                time.sleep(1.2) # API Safety
                
                if res:
                    signal, quality = res
                    if signal:
                        now = datetime.now(user_tz)
                        current_time_str = now.strftime('%H:%M:%S')
                        current_min = now.strftime('%H:%M') # একই মিনিটে বারবার মেসেজ না পাঠানোর জন্য
                        
                        if last_signal_time[asset] != current_min:
                            display_name = asset.replace('=X', '').replace('-', '')
                            
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
                            
                            message_id = send_telegram_msg(msg)
                            if message_id:
                                # Start a new thread to check the result after expiry
                                # Store the signal generation time in UTC for accurate comparison
                                signal_datetime_utc = datetime.utcnow()
                                threading.Thread(
                                    target=check_signal_result,
                                    args=(
                                        message_id,
                                        asset,
                                        signal_datetime_utc,
                                        signal,
                                        expiry_seconds,
                                        msg, # Pass the original message text for editing
                                        current_config.get('timezone', 'Asia/Dhaka') # Pass timezone name for result print
                                    )
                                ).start()
                            
                            last_signal_time[asset] = current_min
                            print(f"[{current_time_str}] Signal Sent: {display_name}")
            
            time.sleep(15)
        except Exception as e:
            print(f"Engine Loop Error: {e}")
            time.sleep(20)

if __name__ == "__main__":
    main()
# --- END OF FILE bot.py (MODIFIED) ---
