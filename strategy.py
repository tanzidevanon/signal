import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    try:
        # ইন্ডিকেটর ক্যালকুলেশন
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['rsi'] = ta.rsi(df['close'], length=14)
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
        df = pd.concat([df, stoch], axis=1)
        
        bbl = [c for c in df.columns if c.startswith('BBL')][0]
        bbu = [c for c in df.columns if c.startswith('BBU')][0]
        stk = [c for c in df.columns if c.startswith('STOCHK')][0]

        last = df.iloc[-1]
        close = last['close']
        rsi = last['rsi']
        stoch_k = last[stk]
        
        signal = None
        accuracy_pct = 0

        # --- সহজ CALL (UP) লজিক ---
        # প্রাইস যদি লোয়ার ব্যান্ডের আশেপাশে থাকে এবং RSI ৫০ এর নিচে থাকে
        if close <= (last[bbl] * 1.002) and rsi < 50:
            signal = "🟢 CALL (UP)"
            # পার্সেন্টেজ ক্যালকুলেশন (সহজ পদ্ধতি)
            score = 70 # বেস স্কোর
            if rsi < 40: score += 10
            if stoch_k < 30: score += 10
            if close <= last[bbl]: score += 8
            accuracy_pct = min(score, 98)

        # --- সহজ PUT (DOWN) লজিক ---
        # প্রাইস যদি আপার ব্যান্ডের আশেপাশে থাকে এবং RSI ৫০ এর উপরে থাকে
        elif close >= (last[bbu] * 0.998) and rsi > 50:
            signal = "🔴 PUT (DOWN)"
            score = 70
            if rsi > 60: score += 10
            if stoch_k > 70: score += 10
            if close >= last[bbu]: score += 8
            accuracy_pct = min(score, 98)

        return signal, f"{accuracy_pct}%", close

    except:
        return None, None, None
