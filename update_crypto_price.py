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

# Only allow these tokens
ALLOWED_TOKENS = {"BTC", "ETH", "ZIL"}

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["update_crypto_price"]
# alerts_col = db["alerts"]
subs_col = db["subscribed_channels"]


# Get current price from Binance
async def get_price(symbol: str):
    symbol = symbol.upper()
    try:
        usd_response = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT")
        usd_price = float(usd_response.json()[
                          "price"]) if usd_response.status_code == 200 else None
        thb_response = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=THB")
        thb_rate = float(thb_response.json()[
                         "rates"]["THB"]) if thb_response.status_code == 200 else None
        if usd_price and thb_rate:
            thb_price = usd_price * thb_rate
            return {"usd": usd_price, "thb": thb_price}
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")

    return None


# MongoDB function
# def get_alert(channel_id, token):
#     return alerts_col.find_one({"channel_id": channel_id, "token": token.upper()}) or {
#         "channel_id": channel_id,
#         "token": token.upper(),
#         "above": None,
#         "below": None
#     }


# def set_alert(channel_id, token, above=None, below=None):
#     alerts_col.update_one(
#         {"channel_id": channel_id, "token": token.upper()},
#         {"$set": {"above": above, "below": below}},
#         upsert=True
#     )


# def reset_alert(channel_id, token, direction: str):
#     alerts_col.update_one(
#         {"channel_id": channel_id, "token": token.upper()},
#         {"$set": {direction: None}}
#     )


def is_subscribed(channel_id, token):
    return subs_col.find_one({"channel_id": channel_id, "token": token.upper()}) is not None


def subscribe(channel_id, token):
    subs_col.update_one(
        {"channel_id": channel_id, "token": token.upper()},
        {"$set": {"channel_id": channel_id, "token": token.upper()}},
        upsert=True
    )


def unsubscribe(channel_id, token):
    subs_col.delete_one({"channel_id": channel_id, "token": token.upper()})
# end MongoDB function


@client.event
async def on_ready():
    print(f"🟢 Logged in as {client.user}", flush=True)

    # Always (re)start the background task on ready
    if hasattr(client, 'price_update_task'):
        if client.price_update_task.done():
            print("🔄 Restarting periodic_price_update (previous task ended)", flush=True)
            client.price_update_task = client.loop.create_task(
                periodic_price_update())
        else:
            print("✅ periodic_price_update already running", flush=True)
    else:
        print("🚀 Starting periodic_price_update for the first time", flush=True)
        client.price_update_task = client.loop.create_task(
            periodic_price_update())


@client.event
async def on_message(message):
    if message.author == client.user or not message.content.startswith("!"):
        return

    parts = message.content[1:].strip().split()
    cmd = parts[0].lower() if parts else ""
    channel = message.channel
    channel_id = channel.id

    if len(parts) > 1:
        token = parts[1].upper()
    else:
        await channel.send(
            "Commands:\n"
            "`!now [token]`\n"
            # "`!above [token] [price]`\n"
            # "`!below [token] [price]`\n"
            "`!sub [token]`\n"
            "`!unsub [token]`\n"
            "Allowed tokens: BTC, ETH, ZIL\n"
            # "Example: `!above BTC 65000`, `!below ZIL 0.03`"
        )
        return

    if token not in ALLOWED_TOKENS:
        await channel.send(f"❌ Token `{token}` is not supported. Allowed tokens: BTC, ETH, ZIL")
        return

    # alert = get_alert(channel_id, token)

    if cmd == "now":
        price_data = await get_price(token)
        if price_data:
            if (token == "ZIL"):
                await channel.send(
                    f"{token} is ${price_data['usd']:,.4f} ≈ ฿{price_data['thb']:,.4f}"
                )
            else:
                await channel.send(
                    f"{token} is ${int(price_data['usd']):,} ≈ ฿{int(price_data['thb']):,}"
                )
        else:
            await channel.send(f"⚠️ Could not fetch {token} price.")
    # elif cmd in ("above", "over") and len(parts) == 3:
    #     try:
    #         value = float(parts[2])
    #         set_alert(channel_id, token, above=value, below=alert.get("below"))
    #         await channel.send(f"📈 Alert set! Notify when {token} goes **above** ${value:,.6f}")
    #     except:
    #         await channel.send("⚠️ Invalid format. Try: `!above BTC 65000`")
    # elif cmd in ("below", "under") and len(parts) == 3:
    #     try:
    #         value = float(parts[2])
    #         set_alert(channel_id, token, above=alert.get("above"), below=value)
    #         await channel.send(f"📉 Alert set! Notify when {token} goes **below** ${value:,.6f}")
    #     except:
    #         await channel.send("⚠️ Invalid format. Try: `!below ETH 3000`")
    elif cmd == "sub":
        subscribe(channel_id, token)
        await channel.send(f"✅ Subscribed to {token} 45-min updates.")
    elif cmd == "unsub":
        unsubscribe(channel_id, token)
        await channel.send(f"❌ Unsubscribed from {token} 45-min updates.")
    else:
        await channel.send(
            "Commands:\n"
            "`!now [token]`\n"
            # "`!above [token] [price]`\n"
            # "`!below [token] [price]`\n"
            "`!sub [token]`\n"
            "`!unsub [token]`\n"
            "Allowed tokens: BTC, ETH, ZIL\n"
            # "Example: `!above BTC 65000`, `!below ZIL 0.03`"
        )


async def periodic_price_update():
    await client.wait_until_ready()
    print("🚀 Started periodic_price_update", flush=True)
    while not client.is_closed():
        try:
            subscribers = list(subs_col.find())
            print(
                f"🔍 Found {len(subscribers)} subscribed channels", flush=True)

            for doc in subscribers:
                token = doc.get("token")
                channel_id = doc.get("channel_id")
                if not token or not channel_id:
                    print(
                        f"❌ Missing token or channel_id in doc: {doc}", flush=True)
                    continue

                channel = client.get_channel(channel_id)
                if not channel:
                    print(f"⚠️ Channel {channel_id} not found", flush=True)
                    continue

                price_data = await get_price(token)
                if not price_data:
                    print(f"⚠️ Failed to fetch price for {token}", flush=True)
                    continue

                msg = (
                    f"[1-Hour Update] {token} is ${price_data['usd']:,.4f} ≈ ฿{price_data['thb']:,.4f}"
                    if token == "ZIL"
                    else f"[1-Hour Update] {token} is ${int(price_data['usd']):,} ≈ ฿{int(price_data['thb']):,}"
                )
                await channel.send(msg)
                print(
                    f"✅ Sent update for {token} to channel {channel_id}", flush=True)

        except Exception as e:
            print(f"❌ Exception in periodic update: {e}", flush=True)

        await asyncio.sleep(3600)  # 1 hour


# async def price_alert_monitor():
#     await client.wait_until_ready()
#     while not client.is_closed():
#         for alert in alerts_col.find():
#             token = alert["token"]
#             price = await get_price(token)
#             if price is None:
#                 continue
#             channel = client.get_channel(alert["channel_id"])
#             if not channel:
#                 continue
#             above = alert.get("above")
#             below = alert.get("below")
#             if above is not None and price >= above:
#                 await channel.send(f"🚨 {token} is ${price:,.6f}, crossed **above** ${above:,.6f}!")
#                 reset_alert(alert["channel_id"], token, "above")
#             if below is not None and price <= below:
#                 await channel.send(f"⚠️ {token} is ${price:,.6f}, dropped **below** ${below:,.6f}!")
#                 reset_alert(alert["channel_id"], token, "below")
#         await asyncio.sleep(1)


client.run(TOKEN)
