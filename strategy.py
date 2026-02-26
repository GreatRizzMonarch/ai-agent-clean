from indicators import calculate_ema, calculate_rsi
from market import get_price, is_market_open, normalize_symbol
import time


# Initialize global dictionaries for signal tracking
last_signal = {}
last_signal_time = {}


def identify_trend(symbol):

    symbol = normalize_symbol(symbol)
    
    try:
        ema20 = calculate_ema(symbol, 20)
        ema50 = calculate_ema(symbol, 50)
        current_price = get_price(symbol)
        rsi_value = calculate_rsi(symbol)

        # SAFETY CHECK
        if None in (ema20, ema50, current_price, rsi_value):
            return None

        # TREND LOGIC
        if ema20 > ema50 and rsi_value > 55:
            return "Strong Bullish Uptrend 📈🔥"

        elif ema20 < ema50 and rsi_value < 45:
            return "Strong Bearish Downtrend 📉🔥"

        elif 45 <= rsi_value <= 55:
            return "Sideways / Low Momentum 🔄"

        else:
            return "Weak / Transition Phase ⚠️"

    except Exception as e:
        print("Trend error:", e)
        return None
    
def calculate_trend_score(symbol):
    try:
        price = get_price(symbol)
        ema20 = calculate_ema(symbol, 20)
        ema50 = calculate_ema(symbol, 50)
        rsi = calculate_rsi(symbol)

        if None in (price, ema20, ema50, rsi):
            return None

        score = 0

        # ---------- 1️⃣ EMA Structure (40 pts) ----------
        if price > ema20 > ema50:
            score += 40
            bias = "Bullish 📈"
        elif price < ema20 < ema50:
            score += 40
            bias = "Bearish 📉"
        else:
            score += 20
            bias = "Sideways 🔄"

        # ---------- 2️⃣ RSI Momentum (30 pts) ----------
        if 55 <= rsi <= 70:
            score += 30
            momentum = "Strong"
        elif 45 <= rsi < 55 or 70 < rsi <= 80:
            score += 15
            momentum = "Moderate"
        else:
            momentum = "Weak"

        # ---------- 3️⃣ Distance from EMA20 (20 pts) ----------
        distance = abs(price - ema20) / ema20 * 100

        if distance > 3:
            score += 20
        elif distance > 1:
            score += 10

        # ---------- 4️⃣ Risk check ----------
        if rsi > 80:
            risk = "Overbought ⚠️"
            score -= 10
        elif rsi < 20:
            risk = "Oversold ⚠️"
            score -= 10
        else:
            risk = "Normal"

        score = max(0, min(100, score))

        return {
            "score": score,
            "bias": bias,
            "momentum": momentum,
            "risk": risk,
            "rsi": round(rsi, 2)
        }

    except Exception as e:
        print("Trend Score Error:", e)
        return None
    
def generate_signal(symbol):
    data = calculate_trend_score(symbol)

    if data is None:
        return None

    score = data["score"]
    bias = data["bias"]
    rsi = data["rsi"]

    # ===== BUY signal =====
    if score >= 70 and "Bullish" in bias and rsi < 75:
        signal = "BUY 🚀"

    # ===== SELL signal =====
    elif score >= 70 and "Bearish" in bias and rsi > 25:
        signal = "SELL 🔻"

    else:
        return None

    # anti-spam check
    if last_signal.get(symbol) == signal:
        return None

    last_signal[symbol] = signal

    return {
        "signal": signal,
        "score": score,
        "bias": bias,
        "rsi": rsi
    } 

    
def generate_auto_signal(symbol):
    try:
        # ===== DATA =====
        price = get_price(symbol)
        ema20 = calculate_ema(symbol, 20)
        ema50 = calculate_ema(symbol, 50)
        rsi = calculate_rsi(symbol)
        score_data = calculate_trend_score(symbol)

        if score_data is None:
            return None

        score = score_data["score"]

        if None in (price, ema20, ema50, rsi, score):
            return None

        # ===== ANALYSIS =====
        trend = "Sideways"

        if ema20 > ema50:
            trend = "Bullish"
        elif ema20 < ema50:
            trend = "Bearish"

        # ===== SIGNAL LOGIC =====
        signal = "WAIT"

        if trend == "Bullish" and score >= 70 and rsi < 75:
            signal = "BUY"

        elif trend == "Bearish" and score >= 70 and rsi > 25:
            signal = "SELL"

        # ===== FINAL FILTER =====
        if signal == "WAIT":
            return None

        return {
            "symbol": symbol,
            "signal": signal,
            "price": price,
            "trend": trend,
            "rsi": round(rsi, 2),
            "score": score
        }

    except Exception as e:
        print("Signal error:", e)
        return None
    
def can_send_signal(symbol, cooldown=900):
    # 900 sec = 15 min

    now = time.time()

    if symbol not in last_signal_time:
        last_signal_time[symbol] = now
        return True

    if now - last_signal_time[symbol] > cooldown:
        last_signal_time[symbol] = now
        return True

    return False