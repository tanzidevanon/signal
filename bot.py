import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    try:
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
        
        signal = None
        quality = "NORMAL"

        if price <= lower_band and rsi < 35:
            signal = "🟢 CALL (UP)"
            quality = "⭐⭐⭐ HIGH" if price > ema_trend else "⭐⭐ NORMAL"
        elif price >= upper_band and rsi > 65:
            signal = "🔴 PUT (DOWN)"
            quality = "⭐⭐⭐ HIGH" if price < ema_trend else "⭐⭐ NORMAL"
        
        return signal, quality
    except:
        return None, None
