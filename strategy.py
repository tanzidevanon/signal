import pandas_ta as ta
import pandas as pd

def get_trading_signal(df, is_pre_signal=False):
    try:
        df['rsi'] = ta.rsi(df['close'], length=7)
        bb = ta.bbands(df['close'], length=20, std=2)
        df = pd.concat([df, bb], axis=1)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        bbl_col = [c for c in df.columns if c.startswith('BBL')][0]
        bbu_col = [c for c in df.columns if c.startswith('BBU')][0]
        
        last = df.iloc[-1]
        price, rsi, ema = last['close'], last['rsi'], last['ema_200']
        lower_band, upper_band = last[bbl_col], last[bbu_col]

        # ১. প্রি-সিগন্যাল লজিক (একটু শিথিল যাতে আগে অ্যালার্ট দেয়)
        if is_pre_signal:
            # প্রাইস ব্যান্ডের ৫ পিপসের মধ্যে এবং RSI লজিকের কাছাকাছি
            is_call_pre = price <= (lower_band * 1.0005) and rsi < 40
            is_put_pre = price >= (upper_band * 0.9995) and rsi > 60
            
            if is_call_pre or is_put_pre:
                # সম্ভাবনা গণনা (ট্রেন্ডের সাথে থাকলে ৯০%, না থাকলে ৭০%)
                prob = "90%" if (is_call_pre and price > ema) or (is_put_pre and price < ema) else "70%"
                direction = "CALL" if is_call_pre else "PUT"
                return direction, prob
            return None, None

        # ২. ফাইনাল সিগন্যাল লজিক (কঠোর লজিক)
        if price <= lower_band and rsi < 35:
            return "🟢 CALL (UP)", "HIGH" if price > ema else "NORMAL"
        elif price >= upper_band and rsi > 65:
            return "🔴 PUT (DOWN)", "HIGH" if price < ema else "NORMAL"
            
        return None, None
    except:
        return None, None
