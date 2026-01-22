import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    try:
        # ইন্ডিকেটর
        df['rsi'] = ta.rsi(df['close'], length=7)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        
        last = df.iloc[-1]
        
        if pd.isna(last['rsi']) or pd.isna(last['ema_200']) or pd.isna(last[bbl_col]):
            return None, None

        price = last['close']
        rsi = last['rsi']
        ema_trend = last['ema_200']
        lower_band = last[bbl_col]
        upper_band = last[bbu_col]
        
        # ডিলে কমানোর জন্য লজিক কিছুটা রিল্যাক্স করা হয়েছে (যাতে সিগন্যাল সময়মতো আসে)
        # CALL (UP)
        if price <= (lower_band * 1.0002) and rsi < 38:
            quality = "⭐⭐⭐ HIGH" if price > ema_trend else "⭐⭐ NORMAL"
            return "🟢 CALL (UP)", quality

        # PUT (DOWN)
        elif price >= (upper_band * 0.9998) and rsi > 62:
            quality = "⭐⭐⭐ HIGH" if price < ema_trend else "⭐⭐ NORMAL"
            return "🔴 PUT (DOWN)", quality
        
        return None, None

    except Exception as e:
        return None, None
