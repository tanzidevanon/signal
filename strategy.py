import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    try:
        # ইন্ডিকেটর
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['rsi'] = ta.rsi(df['close'], length=10)
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
        df = pd.concat([df, stoch], axis=1)
        df['ema_200'] = ta.ema(df['close'], length=200)

        bbl = [c for c in df.columns if c.startswith('BBL')][0]
        bbu = [c for c in df.columns if c.startswith('BBU')][0]
        stk = [c for c in df.columns if c.startswith('STOCHK')][0]

        last = df.iloc[-1]
        close = last['close']
        rsi = last['rsi']
        stoch_k = last[stk]
        ema = last['ema_200']

        signal = None
        quality = "⭐⭐ NORMAL"

        # 🟢 CALL (UP)
        if (close <= last[bbl] or last['low'] <= last[bbl]) and rsi < 40:
            if stoch_k < 30:
                signal = "🟢 CALL (UP)"
                if close > ema: quality = "⭐⭐⭐ HIGH"

        # 🔴 PUT (DOWN)
        elif (close >= last[bbu] or last['high'] >= last[bbu]) and rsi > 60:
            if stoch_k > 70:
                signal = "🔴 PUT (DOWN)"
                if close < ema: quality = "⭐⭐⭐ HIGH"

        return signal, quality, close # প্রাইসও রিটার্ন করছি রেজাল্ট চেক করার জন্য

    except:
        return None, None, None
