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
    }).encode()

    request = urllib.request.Request(
        API + "sendMessage",
        data=data
    )

    urllib.request.urlopen(request, timeout=15)


def main():
    print("Спортивный бот запущен!")
    offset = None

    while True:
        try:
            url = API + "getUpdates?timeout=30"

            if offset is not None:
                url += f"&offset={offset}"

            with urllib.request.urlopen(url, timeout=35) as response:
                updates = json.loads(response.read())

            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message", {})
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                text = message.get("text", "")

                if not chat_id or not text:
                    continue

                if text.startswith("/start"):
                    send_message(
                        chat_id,
                        "Привет! Я спортивный аналитик-бот.\n\n"
                        "Я помогу разбирать матчи и статистику.\n\n"
                        "Выбери спорт:\n"
                        "🏀 Баскетбол\n"
                        "🏐 Волейбол\n"
                        "🎾 Теннис\n"
                        "🎱 Снукер\n"
                        "🎮 Dota 2\n"
                        "🔫 CS2\n\n"
                        "Пока я настраиваюсь. Скоро добавим анализ матчей!"
                    )
                else:
                    send_message(
                        chat_id,
                        "Напиши /start, чтобы открыть главное меню."
                    )

        except Exception as error:
            print("Ошибка:", error)
            time.sleep(3)


if __name__ == "__main__":
    main()
