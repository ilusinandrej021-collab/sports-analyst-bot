import os
import json
import time
import urllib.request
import urllib.parse

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

API = f"https://api.telegram.org/bot{TOKEN}/"


def send_message(chat_id, text):
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text
    }).encode("utf-8")

    request = urllib.request.Request(
        API + "sendMessage",
        data=data
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def main():
    print("Спортивный аналитик-бот запущен!")
    offset = None

    while True:
        try:
            params = {"timeout": 30}

            if offset is not None:
                params["offset"] = offset

            query = urllib.parse.urlencode(params)

            with urllib.request.urlopen
