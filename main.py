import os
import json
import time
import urllib.request
import urllib.parse

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

API = f"https://api.telegram.org/bot{TOKEN}/"


SPORTS_KEYBOARD = {
    "keyboard": [
        [
            {"text": "🏀 Баскетбол"},
            {"text": "🏐 Волейбол"}
        ],
        [
            {"text": "🎾 Теннис"},
            {"text": "🎱 Снукер"}
        ],
        [
            {"text": "🎮 Dota 2"},
            {"text": "🎯 CS2"}
        ]
    ],
    "resize_keyboard": True
}


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    data = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(
        API + "sendMessage",
        data=data
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def main():
    print("Спортивный аналитик-бот запущен!", flush=True)

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

            if not data.get("ok"):
                print(f"Ошибка Telegram API: {data}", flush=True)
                time.sleep(3)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")

                if not message or "text" not in message:
                    continue

                chat_id = message["chat"]["id"]
                text = message["text"].strip()

                if text == "/start" or text == "📋 Меню":
                    send_message(
                        chat_id,
                        "Привет! Я спортивный аналитик.\n\n"
                        "Выбери вид спорта кнопкой ниже:",
                        SPORTS_KEYBOARD
                    )

                elif text in [
                    "🏀 Баскетбол",
                    "🏐 Волейбол",
                    "🎾 Теннис",
                    "🎱 Снукер",
                    "🎮 Dota 2",
                    "🎯 CS2"
                ]:
                    sport = text

                    send_message(
                        chat_id,
                        f"Ты выбрал: {sport}\n\n"
                        "Раздел находится в разработке. "
                        "Следующим этапом добавим поиск матчей "
                        "и статистику.\n\n"
                        "Чтобы вернуться к выбору спорта, "
                        "нажми /start.",
                        SPORTS_KEYBOARD
                    )

                else:
                    send_message(
                        chat_id,
                        "Выбери вид спорта с помощью кнопок "
                        "или напиши /start.",
                        SPORTS_KEYBOARD
                    )

        except Exception as error:
            print(f"Ошибка: {error}", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
