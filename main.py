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
            url = f"{API}getUpdates?{query}"

            with urllib.request.urlopen(url, timeout=35) as response:
                data = json.loads(response.read().decode("utf-8"))

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message or "text" not in message:
                    continue

                chat_id = message["chat"]["id"]
                text = message["text"].strip()

                if text == "/start":
                    send_message(
                        chat_id,
                        "Привет! Я спортивный аналитик.\n\n"
                        "Выбери вид спорта:\n"
                        "🏀 Баскетбол\n"
                        "🏐 Волейбол\n"
                        "🎾 Теннис\n"
                        "🎱 Снукер\n"
                        "🎮 Dota 2\n"
                        "🔫 CS2"
                    )
                else:
                    send_message(chat_id, "Напиши /start, чтобы открыть меню.")

        except Exception as error:
            print(f"Ошибка: {error}")
            time.sleep(3)
