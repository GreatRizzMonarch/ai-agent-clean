import requests
from datetime import datetime
import pytz

def normalize_symbol(symbol):
    symbol = symbol.upper().replace(".NS", "")
    return symbol + ".NS"

def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except:
        return None

def get_price(symbol):

    print("FETCHING price:", symbol)
    
    symbol = normalize_symbol(symbol)
    #yahoo fetch
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
        
        data = fetch_data(url)
        if not data:            
            print(f"bad status for symbol {symbol}")
            return None

        result = data.get("chart", {}).get("result")
        if not result:
            print(f"No result for symbol {symbol}")
            return None
        
        closes = result[0]['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None]

        return closes[-1] if closes else None
    
    except Exception as e:
        print("Error fetching price:", e)
        return None


def is_market_open():
    india = pytz.timezone("Asia/Kolkata")
    now = datetime.now(india)

    #weekend block
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    
    #NSE timings: 9:15 AM to 3:30 PM IST
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    return market_open <= now <= market_close