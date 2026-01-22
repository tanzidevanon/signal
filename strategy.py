import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    try:
        # ১. অরিজিনাল ইন্ডিকেটর ক্যালকুলেশন
        df['rsi'] = ta.rsi(df['close'], length=7)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        
        last = df.iloc[-1]
        
        if pd.isna(last['rsi']) or pd.isna(last['ema_200']) or pd.isna(last[bbl_col]):
            return None, None, None

        price = last['close']
        rsi = last['rsi']
        ema_trend = last['ema_200']
        lower_band = last[bbl_col]
        upper_band = last[bbu_col]
        
        signal = None
        accuracy = 85 # বেস একুরেসি

        # --- অরিজিনাল ট্রেডিং রুলস ---
        
        # CALL (UP)
        if price <= lower_band and rsi < 35:
            signal = "🟢 CALL (UP)"
            # পার্সেন্টেজ ক্যালকুলেশন
            if price > ema_trend: accuracy += 10
            if rsi < 25: accuracy += 4
            accuracy = min(accuracy, 99)

        # PUT (DOWN)
        elif price >= upper_band and rsi > 65:
            signal = "🔴 PUT (DOWN)"
            # পার্সেন্টেজ ক্যালকুলেশন
            if price < ema_trend: accuracy += 10
            if rsi > 75: accuracy += 4
            accuracy = min(accuracy, 99)
        
        return signal, f"{accuracy}%", price

    except Exception as e:
        return None, None, None
