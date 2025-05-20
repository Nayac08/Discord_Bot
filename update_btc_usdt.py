import discord
from dotenv import load_dotenv
import requests
import os
import asyncio
from keep_alive import keep_alive
from pymongo import MongoClient

intents = discord.Intents.default()
intents.message_content = True

keep_alive()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

client = discord.Client(intents=intents)

# MongoDB retrieve
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["update_btc_usdt"]
alerts_col = db["alerts"]  # {channel_id: {'above': float, 'below': float}}
subs_col = db["subscribed_channels"]  # Channels that want 30-min updates

# MongoDB Function


def get_alert(channel_id):
    alert = alerts_col.find_one({"channel_id": channel_id})
    if alert:
        return alert
    else:
        return {"channel_id": channel_id, "above": None, "below": None}


def set_alert(channel_id, above=None, below=None):
    alerts_col.update_one(
        {"channel_id": channel_id},
        {"$set": {"above": above, "below": below}},
        upsert=True
    )


def reset_alert(channel_id, direction: str):
    alerts_col.update_one(
        {"channel_id": channel_id},
        {"$set": {direction: None}}  # <-- Reset 'above' or 'below' to None
    )


def is_subscribed(channel_id):
    return subs_col.find_one({"channel_id": channel_id}) is not None


def subscribe(channel_id):
    subs_col.update_one({"channel_id": channel_id}, {
                        "$set": {"channel_id": channel_id}}, upsert=True)


def unsubscribe(channel_id):
    subs_col.delete_one({"channel_id": channel_id})


async def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return float(response.json()["price"])
    except Exception as e:
        print(f"Error fetching BTC price: {e}")
    return None
# End MongoDB Function


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
    if message.author == client.user or not message.content.startswith("!"):
        return

    content = message.content[1:].strip().lower()
    channel = message.channel
    channel_id = channel.id

    alert = get_alert(channel_id)

    if content == "now":
        await update_btc_usdt(channel)

    elif content.startswith("above ") or content.startswith("over "):
        try:
            value = float(content.split()[1])
            set_alert(channel_id, above=value, below=alert.get('below'))
            await channel.send(f"📈 Alert set! I will notify when BTC goes **above** ${value:,.2f}")
        except:
            await channel.send("⚠️ Invalid number format. Try: `!above 65000`")

    elif content.startswith("below ") or content.startswith("under "):
        try:
            value = float(content.split()[1])
            set_alert(channel_id, above=alert.get('above'), below=value)
            await channel.send(f"📉 Alert set! I will notify when BTC goes **below** ${value:,.2f}")
        except:
            await channel.send("⚠️ Invalid number format. Try: `!below 30000`")

    elif content == "subscribe":
        subscribe(channel_id)
        await channel.send("✅ This channel is now subscribed to 30-minute BTC updates.")

    elif content == "unsubscribe":
        unsubscribe(channel_id)
        await channel.send("❌ This channel has been unsubscribed from 30-minute BTC updates.")

    else:
        await channel.send(
            "Commands:\n"
            "`!now`\n"
            "`!above 65000`\n"
            "`!below 30000`\n"
            "`!subscribe` (get 30-minute BTC updates)\n"
            "`!unsubscribe`"
        )


async def periodic_price_update():
    await client.wait_until_ready()
    while not client.is_closed():
        price = await get_btc_price()
        if price is not None:
            for doc in subs_col.find():
                channel = client.get_channel(doc["channel_id"])
                if channel:
                    await channel.send(f"[30-Min Update] BTC is ${price:,.2f}")
        await asyncio.sleep(1800)


async def price_alert_monitor():
    await client.wait_until_ready()
    while not client.is_closed():
        price = await get_btc_price()
        for alert in alerts_col.find():
            channel_id = alert["channel_id"]
            channel = client.get_channel(channel_id)
            if not channel:
                continue
            above = alert.get("above")
            below = alert.get("below")
            if above is not None and price >= above:
                await channel.send(f"🚨 BTC is ${price:,.2f}, crossed **above** ${above:,.2f}!")
                reset_alert(channel_id, "above")
            if below is not None and price <= below:
                await channel.send(f"⚠️ BTC is ${price:,.2f}, dropped **below** ${below:,.2f}!")
                reset_alert(channel_id, "below")
        await asyncio.sleep(5)

client.run(TOKEN)
