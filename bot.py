from email.mime import text
import os
from turtle import pd
from urllib import response
import requests
import sqlite3
import time
last_signal = {}
last_signal_time = {}
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

conn = sqlite3.connect("alerts.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    symbol TEXT,
    target_price REAL
)
""")
conn.commit()

def fetch_data(url, retries=3):
    for _ in range(retries):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )

            if response.status_code != 200:
                time.sleep(1)
                continue

            return response.json()

        except Exception:
            time.sleep(1)

    return None

def get_price(symbol: str):
    try:
        symbol = symbol.upper()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        result = data.get("chart", {}).get("result")

        if not result:
            return None

        return result[0]["meta"]["regularMarketPrice"]

    except Exception as e:
        print("Price fetch error:", e)
        return None
    
import pandas as pd

def calculate_sma(symbol, period=20):
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

def calculate_ema(symbol, period=20):
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
        return None 

def identify_trend(symbol):
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

def calculate_rsi(symbol, period=14):
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
    
import time

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
                        

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""Welcome on this bot created by Harsh Raj Gupta.
This bot delivers data-driven trading signals powered by technical analysis and algorithmic models.
What you can expect: 
• Real-time market analysis
• Structured entry, stop-loss & target levels
• Risk-focused strategy logic
• No emotional trading
Before using any signal, understand your risk.
Markets are volatile. 
Trade responsibly.
Type /help to see available commands
Bot is alive 🚀""")
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Welcome message\n"
        "/ping - Check if bot is responsive\n"
        "/price SYMBOL - Get current price of a stock\n"
        "/alert SYMBOL TARGET_PRICE - Set price alert\n"
        "/sma SYMBOL - Get 20-day SMA\n"
        "/ema SYMBOL [PERIOD] - Get EMA (default 20)\n"
        "/trend SYMBOL - Identify trend and momentum\n"
        "/rsi SYMBOL - Get 14-day RSI\n"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong 🏓")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price SYMBOL")
        return

    symbol = context.args[0].upper()
    current_price = get_price(symbol)

    if current_price is None:
        await update.message.reply_text("Invalid stock symbol ❌")
    else:
        await update.message.reply_text(f"{symbol} price: ₹{current_price}")
async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /alert SYMBOL TARGET_PRICE")
        return

    symbol = context.args[0].upper()

    try:
        target_price = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Target price must be a number.")
        return

    chat_id = update.effective_chat.id

    cursor.execute(
        "INSERT INTO alerts (chat_id, symbol, target_price) VALUES (?, ?, ?)",
        (chat_id, symbol, target_price),
    )
    conn.commit()

    await update.message.reply_text(
        f"Alert set for {symbol} at ₹{target_price}"
    )        

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT id, chat_id, symbol, target_price FROM alerts")
    rows = cursor.fetchall()

    for alert_id, chat_id, symbol, target_price in rows:
        current_price = get_price(symbol)

        if current_price is None:
            continue

        if current_price >= target_price:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚨 {symbol} hit ₹{target_price}!\nCurrent: ₹{current_price}"
            )

            cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
            conn.commit()

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import pandas as pd
    import numpy as np

    await update.message.reply_text("Pandas & Numpy working ✅")

async def sma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /sma SYMBOL, e.g. /sma SBIN")
        return

    symbol = context.args[0].upper()
    value = calculate_sma(symbol)

    if value is None:
        await update.message.reply_text("Could not calculate SMA ❌")
    else:
        await update.message.reply_text(f"{symbol} 20-day SMA: ₹{value}")

async def ema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /ema SYMBOL PERIOD, e.g. /ema SBIN 20")
        return

    symbol = context.args[0]
    period = int(context.args[1]) if len(context.args) > 1 else 20

    ema_value = calculate_ema(symbol, period)

    if ema_value is None:
        await update.message.reply_text("Could not calculate EMA ❌")
    else:
        await update.message.reply_text(f"{symbol.upper()} {period}-day EMA: ₹{ema_value}")

async def trend(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        if not context.args:
            await update.message.reply_text("Usage: /trend SYMBOL, e.g. /trend SBIN")
            return

        symbol = context.args[0].upper()

        trend = identify_trend(symbol)
        rsi = calculate_rsi(symbol)

        status = "Neutral"

        if rsi is not None:
            if "Bullish" in trend and rsi > 50:
                status = "Trend Confirmed ✅"
            elif "Bearish" in trend and rsi < 50:
                status = "Trend Confirmed ✅"
            else:
                status = "Weak Trend ⚠️"

        await update.message.reply_text(
            f"{symbol} Trend: {trend}\n"
            f"RSI: {rsi}\n"
            f"Status: {status}"
        )

        if trend is None:
            await update.message.reply_text("Could not identify trend ❌")
            return

    except Exception as e:
        print("TREND ERROR:", e)
        await update.message.reply_text(f"Error: {e}")

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /score SYMBOL, e.g. /score SBIN")
        return

    symbol = context.args[0].upper()
    result = calculate_trend_score(symbol)

    if result is None:
        await update.message.reply_text("Could not calculate trend score ❌")
        return

    await update.message.reply_text(
        f"📊 {symbol} Trend Score\n"
        f"Score: {result['score']}/100\n"
        f"Bias: {result['bias']}\n"
        f"Momentum: {result['momentum']}\n"
        f"Risk: {result['risk']}\n"
        f"RSI: {result['rsi']}"
    )

    await update.message.reply_text(text)

async def rsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /rsi SYMBOL, e.g. /rsi SBIN")
        return

    symbol = context.args[0]

    rsi_value = calculate_rsi(symbol)

    if rsi_value is None:
        await update.message.reply_text("Could not calculate RSI ❌")
    elif isinstance(rsi_value, str):
        await update.message.reply_text(rsi_value)
    else:
        await update.message.reply_text(f"{symbol.upper()} 14-day RSI: {rsi_value}") 

async def auto_signal_job(context):
    symbols = ["SBIN", "TCS", "MRF", "RELIANCE", "YESBANK", "IRFC", "LENSKART", "SUZLON", "ETERNAL",
               "KRN", "TATAINVEST", "SILVERBEES", "HINDCOPPER", "ONGC"]  # edit later

    for symbol in symbols:
        result = generate_signal(symbol)

        if result:
            text = (
                f"⚡ AUTO SIGNAL\n"
                f"{symbol}: {result['signal']}\n"
                f"Score: {result['score']}/100\n"
                f"Bias: {result['bias']}\n"
                f"RSI: {result['rsi']}"
            )

            await context.bot.send_message(
                chat_id=7894459956,
                text=text
            )

WATCHLIST = ["SBIN", "TCS", "MRF", "RELIANCE", "YESBANK", "IRFC", "LENSKART", "SUZLON", "ETERNAL",
             "KRN", "TATAINVEST", "SILVERBEES", "HINDCOPPER", "ONGC"]  # edit later

async def auto_signal_engine(context):
    bot = context.bot

    for symbol in WATCHLIST:

        if not can_send_signal(symbol):
            continue

        result = generate_auto_signal(symbol)

        if result is None:
            continue

        msg = (
            f"🚨 AUTO SIGNAL 🚨\n"
            f"{result['symbol']} → {result['signal']}\n"
            f"Price: ₹{result['price']}\n"
            f"Trend: {result['trend']}\n"
            f"Score: {result['score']}/100\n"
            f"RSI: {result['rsi']}"
        )

        # replace CHAT_ID with yours
        await bot.send_message(chat_id=7894459956, text=msg)

async def id(update, context):
    await update.message.reply_text(str(update.effective_chat.id))              

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("sma", sma))
    app.add_handler(CommandHandler("ema", ema))
    app.add_handler(CommandHandler("trend", trend))
    app.add_handler(CommandHandler("rsi", rsi))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("id", id))

    print("AutoSignal Engine Running...")
    # Schedule the alert checking function to run every 1 minutes
    app.job_queue.run_repeating(check_alerts, interval=60, first=10)
    app.job_queue.run_repeating(auto_signal_job, interval=300, first=10)  # Run every 5 minutes
    job_queue = app.job_queue
    job_queue.run_repeating(auto_signal_engine, interval=300, first=10) # Run every 5 minutes
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()