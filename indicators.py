import pandas as pd
import market

# =========================
# SMA
# =========================
def calculate_sma_from_data(closes, period=20):
    try:
        if closes is None or len(closes) < period:
            return None

        series = pd.Series(closes)
        sma = series.rolling(window=period).mean().iloc[-1]

        return round(float(sma), 2)

    except Exception as e:
        print("SMA error:", e)
        return None


# =========================
# EMA
# =========================
def calculate_ema_from_data(closes, period=20):
    try:
        if closes is None or len(closes) < period:
            return None

        series = pd.Series(closes)
        ema = series.ewm(span=period, adjust=False).mean().iloc[-1]

        return round(float(ema), 2)

    except Exception as e:
        print("EMA error:", e)
        return None
    




import pandas as pd
from market import fetch_data, normalize_symbol

def calculate_sma(symbol, period=20):
    try:
        symbol = market.normalize_symbol(symbol)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
        data = market.fetch_data(url)

        if not data:
            return None

        result = data.get("chart", {}).get("result")
        if not result:
            return None

        closes = result[0]["indicators"]["quote"][0]["close"]

        df = pd.DataFrame(closes, columns=["close"])
        df.dropna(inplace=True)

        if len(df) < period:
            return None

        sma = df["close"].rolling(window=period).mean().iloc[-1]

        return round(float(sma), 2)

    except Exception as e:
        print("SMA error:", e)
        return None

# =========================
# RSI
# =========================
def calculate_rsi_from_data(closes, period=14):
    try:
        if closes is None or len(closes) < period:
            return None

        series = pd.Series(closes)

        delta = series.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        rsi_value = rsi.iloc[-1]

        if pd.isna(rsi_value):
            return None

        return round(float(rsi_value), 2)

    except Exception as e:
        print("RSI error:", e)
        return None


def calculate_rsi(symbol, period=14):
    try:
        from market import fetch_data, normalize_symbol

        symbol = market.normalize_symbol(symbol)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2y&interval=1d"

        data = market.fetch_data(url)
        if not data:
            return None

        result = data.get("chart", {}).get("result")
        if not result:
            return None

        closes = result[0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]

        return calculate_rsi_from_data(closes, period)

    except Exception as e:
        print("RSI wrapper error:", e)
        return None   
        
        
# ===============================
# VOLATILITY (simple ATR style)
# ===============================
def calculate_volatility(closes, period=14):

    if len(closes) < period + 1:
        return None

    moves = []

    for i in range(1, len(closes)):
        moves.append(abs(closes[i] - closes[i-1]))

    avg_move = sum(moves[-period:]) / period
    return avg_move


# ===============================
# TARGET PRICE CALCULATOR
# ===============================
def calculate_targets(closes, trend, price):

    volatility = calculate_volatility(closes)

    if volatility is None:
        return None

    # Risk Reward setup
    rr_safe = 1.5
    rr_aggressive = 2.5

    if "Bullish" in trend:

        stoploss = price - volatility
        target1 = price + volatility * rr_safe
        target2 = price + volatility * rr_aggressive

    elif "Bearish" in trend:

        stoploss = price + volatility
        target1 = price - volatility * rr_safe
        target2 = price - volatility * rr_aggressive

    else:
        return None

    return {
        "target1": round(target1, 2),
        "target2": round(target2, 2),
        "stoploss": round(stoploss, 2),
    }