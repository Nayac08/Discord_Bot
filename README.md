# Discord_Bot

A simple Discord bot written in Python that is used in a Discord channel

---

## Features

- Fetches BTC/USDT price from Binance API every 60 seconds
- Posts price updates with change indicators in a Discord channel
- Runs a lightweight Flask server to keep the bot alive (useful for certain hosting platforms)

---

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/Discord_Bot.git
   cd Discord_Bot

2. Install dependencies
   ```bash
   pip install -r requirements.txt

3. Create a .env file with the following variables
   ```bash
   DISCORD_TOKEN=your-discord-bot-token
   CHANNEL_ID_UPDATE_BTC_USDT=your-discord-channel-id

4. Run the bot
   ```bash
   python bot.py
