import time

from market import get_price, get_candles, is_market_open
from indicators import (
    calculate_ema_from_data,
    calculate_rsi_from_data,
    calculate_targets,
)

# ===============================
# Signal tracking (anti spam)
# ===============================
last_signal = {}
last_signal_time = {}

SIGNAL_COOLDOWN = 600   # 10 min


# ===============================
# TREND IDENTIFIER
# ===============================
def identify_trend(symbol):

    try:
        closes = get_candles(symbol)

        if not closes:
            return None

        ema20 = calculate_ema_from_data(closes, 20)
        ema50 = calculate_ema_from_data(closes, 50)
        rsi_value = calculate_rsi_from_data(closes)
        current_price = get_price(symbol)

        # safety check
        if None in (ema20, ema50, rsi_value, current_price):
            return None

        # trend logic
        if ema20 > ema50 and rsi_value > 55:
            return "Strong Bullish Uptrend 📈🔥"

        elif ema20 < ema50 and rsi_value < 45:
            return "Strong Bearish Downtrend 📉🔥"

        elif 45 <= rsi_value <= 55:
            return "Sideways / Low Momentum 🟨"

        else:
            return "Neutral"

    except Exception as e:
        print("Trend error:", e)
        return None


# ===============================
# TREND SCORE (0–100)
# ===============================
def calculate_trend_score(symbol):

    try:
        closes = get_candles(symbol)

        if not closes:
            return None

        ema20 = calculate_ema_from_data(closes, 20)
        ema50 = calculate_ema_from_data(closes, 50)
        rsi = calculate_rsi_from_data(closes)
        price = get_price(symbol)

        if None in (ema20, ema50, rsi, price):
            return None

        score = 50

        # EMA strength
        if ema20 > ema50:
            score += 20
        else:
            score -= 20

        # price vs ema20
        if price > ema20:
            score += 15
        else:
            score -= 15

        # RSI strength
        if rsi > 60:
            score += 15
        elif rsi < 40:
            score -= 15

        score = max(0, min(100, score))

        return score

    except Exception as e:
        print("Score error:", e)
        return None


# ===============================
# AUTO SIGNAL GENERATOR
# ===============================
def generate_signal(symbol):

    try:
        closes = get_candles(symbol)

        if not closes:
            return None

        ema20 = calculate_ema_from_data(closes, 20)
        ema50 = calculate_ema_from_data(closes, 50)
        rsi = calculate_rsi_from_data(closes)
        price = get_price(symbol)

        if None in (ema20, ema50, rsi, price):
            return None

        score = calculate_trend_score(symbol)

        if score is None:
            return None

        signal = None
        bias = "Neutral"

        # BUY logic
        if ema20 > ema50 and rsi > 55 and price > ema20:
            signal = "BUY"
            bias = "Bullish"

        # SELL logic
        elif ema20 < ema50 and rsi < 45 and price < ema20:
            signal = "SELL"
            bias = "Bearish"

        if not signal:
            return None

        return {
            "signal": signal,
            "bias": bias,
            "price": round(price, 2),
            "score": score,
            "rsi": rsi,
        }

    except Exception as e:
        print("Signal error:", e)
        return None


# ===============================
# AUTO SIGNAL ENGINE
# ===============================
def generate_auto_signal(symbol):

    if not is_market_open():
        return None

    now = time.time()

    result = generate_signal(symbol)

    if not result:
        return None

    # anti spam logic
    last = last_signal.get(symbol)
    last_time = last_signal_time.get(symbol, 0)

    if last == result["signal"] and (now - last_time) < SIGNAL_COOLDOWN:
        return None

    last_signal[symbol] = result["signal"]
    last_signal_time[symbol] = now

    return result

# ===============================
# TARGET PREDICTOR
# ===============================
def predict_target(symbol):

    try:
        closes = get_candles(symbol)

        if not closes:
            return None

        trend = identify_trend(symbol)
        price = get_price(symbol)

        if trend is None or price is None:
            return None

        targets = calculate_targets(closes, trend, price)

        if not targets:
            return None

        return {
            "price": round(price, 2),
            "trend": trend,
            "target1": targets["target1"],
            "target2": targets["target2"],
            "stoploss": targets["stoploss"]
        }

    except Exception as e:
        print("Target prediction error:", e)
        return None