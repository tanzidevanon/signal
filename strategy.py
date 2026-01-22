import pandas_ta as ta
import pandas as pd

def get_trading_signal(df):
    """
    এই ফাংশনটি ডাটাফ্রেম গ্রহণ করে এবং (Signal, Quality) রিটার্ন করে।
    এটি সম্পূর্ণ আলাদা রাখা হয়েছে যাতে রুলস পরিবর্তন করা সহজ হয়।
    """
    try:
        # ১. ইন্ডিকেটর ক্যালকুলেশন
        # RSI 7
        df['rsi'] = ta.rsi(df['close'], length=7)
        
        # Bollinger Bands (20, 2)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        
        # EMA 200 (Trend Filter)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        # ২. ডাইনামিক কলাম শনাক্তকরণ (BB এর জন্য)
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        
        last = df.iloc[-1]
        
        # ৩. ভেরিয়েবল সেটআপ
        price = last['close']
        rsi = last['rsi']
        ema_trend = last['ema_200']
        lower_band = last[bbl_col]
        upper_band = last[bbu_col]
        
        signal = None
        quality = "NORMAL"

        # --- ৪. ট্রেডিং রুলস (এখানে আপনার সব লজিক) ---
        
        # CALL (UP) কন্ডিশন
        if price <= lower_band and rsi < 35:
            signal = "🟢 CALL (UP)"
            # ট্রেন্ড ফিল্টার
            if price > ema_trend:
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"

        # PUT (DOWN) কন্ডিশন
        elif price >= upper_band and rsi > 65:
            signal = "🔴 PUT (DOWN)"
            # ট্রেন্ড ফিল্টার
            if price < ema_trend:
                quality = "⭐⭐⭐ HIGH"
            else:
                quality = "⭐⭐ NORMAL"
        
        return signal, quality

    except Exception as e:
        print(f"Strategy Error: {e}")
        return None, None
