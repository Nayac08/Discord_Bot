from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import os

app = Flask('')


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    PORT = int(os.getenv("PORT"))
    app.run(host='0.0.0.0', port=PORT)


def keep_alive():
    t = Thread(target=run)
    t.start()
