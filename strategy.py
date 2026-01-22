import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    """
    এই ফাংশনটি ডাটাফ্রেম গ্রহণ করে এবং (Signal, Quality) রিটার্ন করে।
    """
    try:
        # ১. ইন্ডিকেটর ক্যালকুলেশন
        df['rsi'] = ta.rsi(df['close'], length=7)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        # ২. ডাইনামিক কলাম শনাক্তকরণ (BB এর জন্য)
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        
        # সর্বশেষ ক্যান্ডেলের ডাটা নেওয়া
        last = df.iloc[-1]
        
        # --- ৩. ডাটা চেক (NaN হ্যান্ডেল করা) - এখানে বসবে ---
        # যদি কোনো কারণে ইন্ডিকেটর ক্যালকুলেট না হয় (যেমন যথেষ্ট ডাটা নেই), তবে সিগন্যাল দিবে না
        if pd.isna(last['rsi']) or pd.isna(last['ema_200']) or pd.isna(last[bbl_col]):
            return None, None
        # -----------------------------------------------

        # ৪. ভেরিয়েবল সেটআপ
        price = last['close']
        rsi = last['rsi']
        ema_trend = last['ema_200']
        lower_band = last[bbl_col]
        upper_band = last[bbu_col]
        
        signal = None
        quality = "NORMAL"

        # --- ৫. ট্রেডিং রুলস ---
        
        # CALL (UP) কন্ডিশন
        if price <= lower_band and rsi < 35:
            signal = "🟢 CALL (UP)"
            if price > ema_trend:
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"

        # PUT (DOWN) কন্ডিশন
        elif price >= upper_band and rsi > 65:
            signal = "🔴 PUT (DOWN)"
            if price < ema_trend:
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"
        
        return signal, quality

    except Exception as e:
        print(f"Strategy Error: {e}")
        return None, None
