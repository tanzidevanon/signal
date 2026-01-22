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
        
        # ১. কনফার্মড সিগন্যাল লজিক
        if price <= lower_band and rsi < 35:
            quality = "⭐⭐⭐ HIGH" if price > ema_trend else "⭐⭐ NORMAL"
            return "🟢 CALL (UP)", quality
        
        elif price >= upper_band and rsi > 65:
            quality = "⭐⭐⭐ HIGH" if price < ema_trend else "⭐⭐ NORMAL"
            return "🔴 PUT (DOWN)", quality

        # ২. প্রি-অ্যালার্ট লজিক (অত্যন্ত টাইট কন্ডিশন)
        # ব্যান্ডের ১.০০০৫ গুণের মধ্যে থাকলে এবং RSI খুব কাছে থাকলে
        if price <= (lower_band * 1.0005) and 35 <= rsi <= 38:
            return "PREPARE_CALL", "WAITING"
        elif price >= (upper_band * 0.9995) and 62 <= rsi <= 65:
            return "PREPARE_PUT", "WAITING"
        
        return None, None

    except Exception as e:
        return None, None
