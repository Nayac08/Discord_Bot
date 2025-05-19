import discord
from dotenv import load_dotenv
import requests
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID_UPDATE_BTC_USDT = os.getenv("CHANNEL_ID_UPDATE_BTC_USDT")
if CHANNEL_ID_UPDATE_BTC_USDT is None:
    raise ValueError("CHANNEL_ID_UPDATE_BTC_USDT environment variable not set")

client = discord.Client(intents=intents)

alert_higher = None
alert_lower = None
alert_channel_id = None


async def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return float(response.json()["price"])
    except Exception as e:
        print(f"Error fetching BTC price: {e}")
    return None


async def update_btc_usdt(channel):
    price = await get_btc_price()
    if price is not None:
        await channel.send(f"BTC is ${price:,.2f}")
    else:
        await channel.send("Failed to fetch BTC price.")


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    client.loop.create_task(periodic_price_update())
    client.loop.create_task(price_alert_monitor())


@client.event
async def on_message(message):
    global alert_higher, alert_lower, alert_channel_id

    if message.author == client.user:
        return

    if not message.content.startswith("!"):
        return

    content = message.content[1:].strip().lower()
    channel = message.channel

    if content == "now":
        await update_btc_usdt(channel)

    elif content.startswith("above ") or content.startswith("over "):
        try:
            alert_higher = float(content.split()[1])
            alert_channel_id = channel.id
            await channel.send(f"📈 Alert set! I will notify when BTC goes **above** ${alert_higher:,.2f}")
        except:
            await channel.send("⚠️ Invalid number format. Try: `!above 65000`")

    elif content.startswith("below ") or content.startswith("under "):
        try:
            alert_lower = float(content.split()[1])
            alert_channel_id = channel.id
            await channel.send(f"📉 Alert set! I will notify when BTC goes **below** ${alert_lower:,.2f}")
        except:
            await channel.send("⚠️ Invalid number format. Try: `!below 30000`")

    else:
        await channel.send("Commands:\n`!now`\n`!above 65000`\n`!below 30000`")


async def periodic_price_update():
    await client.wait_until_ready()
    channel = client.get_channel(int(CHANNEL_ID_UPDATE_BTC_USDT))
    while not client.is_closed():
        await update_btc_usdt(channel)
        await asyncio.sleep(1800)


async def price_alert_monitor():
    global alert_higher, alert_lower, alert_channel_id
    await client.wait_until_ready()
    while not client.is_closed():
        price = await get_btc_price()
        if price is not None and alert_channel_id is not None:
            channel = client.get_channel(alert_channel_id)
            if alert_higher is not None and price >= alert_higher:
                await channel.send(f"🚨 BTC is ${price:,.2f}, crossed **above** ${alert_higher:,.2f}!")
                alert_higher = None
            if alert_lower is not None and price <= alert_lower:
                await channel.send(f"⚠️ BTC is ${price:,.2f}, dropped **below** ${alert_lower:,.2f}!")
                alert_lower = None
        await asyncio.sleep(1)

client.run(TOKEN)
