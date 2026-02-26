import pandas as pd
import requests

from market import fetch_data, normalize_symbol

def calculate_ema(symbol, period):
    try:
        symbol = symbol.upper()

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range=2y&interval=1d"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print("Bad status:", response.status_code)
            return None

        try:
            data = response.json()
        except Exception as e:
            print("JSON error:", e)
            return None

        result = data.get("chart", {}).get("result")
        if not result:
            print("No result in API")
            return None

        closes = result[0]["indicators"]["quote"][0]["close"]

        if not closes:
            return None

        df = pd.DataFrame(closes, columns=["close"])
        df.dropna(inplace=True)

        if len(df) < period:
            return None

        df["ema"] = df["close"].ewm(span=period, adjust=False).mean()

        ema_value = df["ema"].iloc[-1]

        if pd.isna(ema_value):
            return None

        return round(ema_value, 2)

    except Exception as e:
        print("EMA error:", e)
        return ema_value

def calculate_sma(symbol, period = 20):
    try:
        symbol = symbol.upper()

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range=3mo&interval=1d"
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )

        if response.status_code != 200:
            print("HTTP Error:", response.status_code)
            print("Response:", response.text[:200])
            return None

        try:
            data = response.json()
        except Exception as e:
            print("JSON decode error:", e)
            print("Raw response:", response.text[:200])
            return None

        result = data.get("chart", {}).get("result")
        if not result:
            print("No result in API")
            return None

        indicators = result[0].get("indicators", {})
        quotes = indicators.get("quote", [{}])[0]
        closes = quotes.get("close")

        if not closes:
            print("No close data")
            return None

        df = pd.DataFrame(closes, columns=["close"])
        df.dropna(inplace=True)

        if len(df) < period:
            print("Not enough data:", len(df))
            return None

        df["sma"] = df["close"].rolling(window=period).mean()

        sma_value = df["sma"].iloc[-1]

        if pd.isna(sma_value):
            return None

        return round(float(sma_value), 2)

    except Exception as e:
        print("SMA error:", e)
        return None
    
def calculate_rsi(symbol, period=14):

    symbol = normalize_symbol(symbol)
    
    try:
        symbol = symbol.upper()

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range=6mo&interval=1d"
        data = fetch_data(url)
        if not data:
            return None

        result = data.get("chart", {}).get("result")
        if not result:
            return None

        closes = result[0]["indicators"]["quote"][0]["close"]

        closes = [c for c in closes if c is not None]
        df = pd.DataFrame(closes, columns=["close"])
        df.dropna(inplace=True)

        if len(df) < period:
            return None

        delta = df["close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        rsi_value = df["rsi"].iloc[-1]

        if pd.isna(rsi_value):
            return None

        return round(rsi_value, 2)

    except Exception as e:
        return f"Error: {str(e)}"