import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Не задана переменная окружения TELEGRAM_BOT_TOKEN"
    )

API = f"https://api.telegram.org/bot{TOKEN}/"

KEYBOARD = {
    "keyboard": [
        [{"text": "⚽ Футбол"}, {"text": "🎾 Теннис"}],
        [{"text": "🏀 Баскетбол"}, {"text": "🏐 Волейбол"}],
        [{"text": "🎱 Снукер"}],
        [{"text": "🎮 Dota 2"}, {"text": "🔫 CS2"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def telegram_request(method, data=None):
    url = API + method

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=40) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"Ошибка Telegram API: {result}")

    return result


def send_message(chat_id, text):
    telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": KEYBOARD,
        },
    )


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    if text.startswith("/start"):
        send_message(
            chat_id,
            "Привет! Я спортивный аналитик-бот.\n\n"
            "Выбери вид спорта в меню ниже.\n\n"
            "Начнём с футбола, затем подключим теннис "
            "и искусственный интеллект для анализа матчей.",
        )

    elif text == "⚽ Футбол":
        send_message(
            chat_id,
            "⚽ ФУТБОЛ\n\n"
            "Раздел футбола открыт!\n\n"
            "Следующий этап — подключить ИИ для анализа матчей. "
            "Он будет помогать оценивать команды, их форму, "
            "результаты и другие доступные данные.\n\n"
            "Ты сможешь выбирать матчи для анализа, "
            "а мы настроим правила отбора.\n\n"
            "Пока анализ матчей ещё не подключён.",
        )

    elif text == "🎾 Теннис":
        send_message(
            chat_id,
            "🎾 ТЕННИС\n\n"
            "Раздел пока в разработке. "
            "Сначала настроим футбольную аналитику.",
        )

    elif text in [
        "🏀 Баскетбол",
        "🏐 Волейбол",
        "🎱 Снукер",
        "🎮 Dota 2",
        "🔫 CS2",
    ]:
        send_message(
            chat_id,
            f"{text}\n\n"
            "Этот раздел пока в разработке. "
            "Сначала займёмся футболом.",
        )

    else:
        send_message(
            chat_id,
            "Выбери вид спорта с помощью кнопок в меню.",
        )


def main():
    print("Спортивный аналитик-бот запускается...")

    telegram_request("deleteWebhook", {"drop_pending_updates": False})

    offset = None

    print("Бот запущен и ожидает сообщения.")

    while True:
        try:
            params = {"timeout": 25}

            if offset is not None:
                params["offset"] = offset

            query = urllib.parse.urlencode(params)
            url = API + "getUpdates?" + query

            request = urllib.request.Request(url)

            with urllib.request.urlopen(
                request,
                timeout=35,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            if not result.get("ok"):
                print("Telegram API вернул ошибку:", result)
                time.sleep(3)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")

                if message:
                    try:
                        handle_message(message)
                    except Exception as error:
                        print("Ошибка обработки сообщения:", error)

        except Exception as error:
            print("Ошибка соединения:", error)
            time.sleep(3)


if __name__ == "__main__":
    main()
