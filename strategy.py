import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    try:
        # ১. ইন্ডিকেটর সেটআপ
        # Bollinger Bands (20, 2)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        # Stochastic (14, 3, 3) - বাইনারি ট্রেডিংয়ের জন্য সেরা
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        df = pd.concat([df, stoch], axis=1)
        
        # EMA 200 (Trend Filter)
        df['ema_200'] = ta.ema(df['close'], length=200)

        # কলাম নাম ঠিক করা
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        stoch_k = [c for c in df.columns if c.startswith('STOCHK')][0]
        stoch_d = [c for c in df.columns if c.startswith('STOCHD')][0]

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        if pd.isna(last[stoch_k]) or pd.isna(last['ema_200']): return None, None

        # ডাটা ভেরিয়েবল
        close = last['close']
        open_p = last['open']
        high = last['high']
        low = last['low']
        
        # রিজেকশন ক্যালকুলেশন (উইক বা ছায়া)
        lower_wick = min(open_p, close) - low
        upper_wick = high - max(open_p, close)
        body_size = abs(close - open_p)

        signal = None
        quality = "⭐⭐ NORMAL"

        # --- হাই কোয়ালিটি রুলস ---

        # 🟢 CALL (UP) সিগন্যাল লজিক
        # ১. ক্যান্ডেল নিচের ব্যান্ডকে টাচ বা ক্রস করেছে
        # ২. স্টোকাস্টিক ২০ এর নিচে (ওভারসোল্ড) এবং ক্রসওভার করছে
        # ৩. ক্যান্ডেল রিজেকশন দিচ্ছে (নিচে বড় উইক আছে)
        if close <= last[bbl_col] or low <= last[bbl_col]:
            if last[stoch_k] < 25 and last[stoch_k] > last[stoch_d]:
                if lower_wick > (body_size * 0.5): # স্ট্রং রিজেকশন
                    signal = "🟢 CALL (UP)"
                    if close > last['ema_200']: quality = "⭐⭐⭐ HIGH"

        # 🔴 PUT (DOWN) সিগন্যাল লজিক
        # ১. ক্যান্ডেল উপরের ব্যান্ডকে টাচ বা ক্রস করেছে
        # ২. স্টোকাস্টিক ৮০ এর উপরে (ওভারবট) এবং ক্রসওভার করছে
        # ৩. ক্যান্ডেল রিজেকশন দিচ্ছে (উপরে বড় উইক আছে)
        elif close >= last[bbu_col] or high >= last[bbu_col]:
            if last[stoch_k] > 75 and last[stoch_k] < last[stoch_d]:
                if upper_wick > (body_size * 0.5): # স্ট্রং রিজেকশন
                    signal = "🔴 PUT (DOWN)"
                    if close < last['ema_200']: quality = "⭐⭐⭐ HIGH"

        return signal, quality

    except Exception as e:
        return None, None
