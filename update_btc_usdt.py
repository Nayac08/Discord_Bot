import discord
from dotenv import load_dotenv
import requests
import os
import asyncio
import datetime
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
client = discord.Client(intents=intents)

app = Flask('')


@app.route('/')
def home():
    return "Bot is running!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    while (True):
        await update_btc_usdt()
        await asyncio.sleep(60)


previous_price_btc_usdt = None
CHANNEL_ID_UPDATE_BTC_USDT = os.getenv("CHANNEL_ID_UPDATE_BTC_USDT")
if CHANNEL_ID_UPDATE_BTC_USDT is None:
    raise ValueError("CHANNEL_ID_UPDATE_BTC_USDT environment variable not set")


async def update_btc_usdt():
    global previous_price_btc_usdt
    channel = client.get_channel(int(CHANNEL_ID_UPDATE_BTC_USDT))

    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        price = float(data["price"])

        # Compare with previous price
        if previous_price_btc_usdt is None:
            change_str = "No previous data"
            emoji = "🔵"
        else:
            diff = price - previous_price_btc_usdt
            percent_change = (diff / previous_price_btc_usdt) * 100
            if diff > 0:
                emoji = "📈"  # price up
                change_str = f"Up {diff:.2f} USD (+{percent_change:.2f}%)"
            elif diff < 0:
                emoji = "📉"  # price down
                change_str = f"Down {abs(diff):.2f} USD ({percent_change:.2f}%)"
            else:
                emoji = "⏸️"
                change_str = "No change"

        previous_price_btc_usdt = price  # update for next round

        now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S GMT+7")

        embed = discord.Embed(title="💰 BTC/USDT Price Update",
                              description=f"The current price of Bitcoin is:",
                              color=0xf2a900)
        embed.add_field(name="Price (USD)",
                        value=f"${price:,.2f}",
                        inline=False)
        embed.add_field(name="Change",
                        value=f"{emoji} {change_str}",
                        inline=False)
        embed.set_footer(text=f"Source: Binance API | Updated at {time_str}")
        await channel.send(embed=embed)

    else:
        print(f"Failed to get data. Status code: {response.status_code}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

keep_alive()

client.run(str(TOKEN))
