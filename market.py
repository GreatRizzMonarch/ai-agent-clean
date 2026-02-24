import requests
from datetime import datetime
import pytz

def get_price(symbol):
    #yahoo fetch
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        data = requests.get(url, timeout=10).json()

        result = data['chart']['result']
        if not result:
            print(f"No data for {symbol}")
            return None
        
        closes = result[0]['indicators']['quote'][0]['close']
        closes = [c for c in closes if c is not None]

        return closes[-1] if closes else None
    
    except:
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