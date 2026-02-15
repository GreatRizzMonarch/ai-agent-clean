import os
from turtle import pd
import requests
import sqlite3
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
    
def calculate_sma(symbol: str, period: int = 20):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range=3mo&interval=1d"
        response = requests.get(url, timeout=10)
        data = response.json()

        result = data.get("chart", {}).get("result")
        if not result:
            return None

        closes = result[0]["indicators"]["quote"][0]["close"]
        df = pd.DataFrame(closes, columns=["close"])
        df.dropna(inplace=True)

        df["SMA"] = df["close"].rolling(window=period).mean()

        return round(df["SMA"].iloc[-1], 2)

    except Exception as e:
        print("SMA error:", e)
        return None
    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is alive 🚀")

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
        await update.message.reply_text("Usage: /alert SUZLON 50")
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
        await update.message.reply_text("Usage: /sma SBIN")
        return

    symbol = context.args[0].upper()
    value = calculate_sma(symbol)

    if value is None:
        await update.message.reply_text("Could not calculate SMA ❌")
    else:
        await update.message.reply_text(f"{symbol} 20-day SMA: ₹{value}")

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("sma", sma))

    # Schedule the alert checking function to run every 1 minutes
    app.job_queue.run_repeating(check_alerts, interval=60, first=10)
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()