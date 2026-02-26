from email.mime import text
import os
from turtle import pd
from datetime import datetime
import pytz
from urllib import response
import requests
import sqlite3
import time
import config
import market
from strategy import identify_trend, calculate_trend_score, generate_signal, generate_auto_signal, can_send_signal
from market import get_price, is_market_open
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from indicators import calculate_ema, calculate_sma, calculate_rsi

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
    current_price = market.get_price(symbol)

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
        current_price = market.get_price(symbol)

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
    await auto_signal_engine(context)


async def auto_signal_engine(context):
    bot = context.bot

    if not market.is_market_open():
        print("Market is closed. Skipping signal generation.")
        return

    for symbol in config.WATCHLIST:

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
    job_queue.run_repeating(auto_signal_job, interval=300)
    job_queue = app.job_queue 
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()