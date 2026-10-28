import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not TOKEN:
    raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

if not OPENROUTER_API_KEY:
    raise RuntimeError("Не задана переменная OPENROUTER_API_KEY")

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}/"
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "openrouter/free"

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


def http_json(url, data=None, headers=None, timeout=40):
    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers or {},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def telegram_request(method, data=None):
    return http_json(
        TELEGRAM_API + method,
        data=data,
        headers={"Content-Type": "application/json"},
    )


def send_message(chat_id, text):
    # Telegram ограничивает длину одного сообщения.
    text = str(text)

    for start in range(0, len(text), 4000):
        telegram_request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text[start:start + 4000],
                "reply_markup": KEYBOARD,
            },
        )


def ask_ai(question):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — помощник спортивного аналитика. "
                    "Отвечай на русском языке. "
                    "Помогай разбирать футбольные матчи, "
                    "форму команд, статистику и возможные риски. "
                    "Не выдумывай результаты, составы, травмы, "
                    "коэффициенты и другие факты. "
                    "Если актуальных данных не предоставили, "
                    "честно скажи об этом. "
                    "Не обещай гарантированный выигрыш. "
                    "Отделяй подтверждённые факты от предположений."
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "temperature": 0.4,
        "max_tokens": 900,
    }

    result = http_json(
        OPENROUTER_API,
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": "Sports Analyst Bot",
        },
        timeout=60,
    )

    choices = result.get("choices", [])

    if not choices:
        raise RuntimeError("ИИ не вернул ответ")

    answer = choices[0].get("message", {}).get("content", "")

    if isinstance(answer, list):
        answer = "\n".join(
            item.get("text", "")
            for item in answer
            if isinstance(item, dict)
        )

    if not answer:
        raise RuntimeError("ИИ вернул пустой ответ")

    return answer


def handle_message(message):
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    if text.startswith("/start"):
        send_message(
            chat_id,
            "Привет! Я спортивный аналитик-бот.\n\n"
            "Выбери вид спорта в меню.\n\n"
            "ИИ подключён в тестовом режиме. "
            "Пока у бота нет источника актуальной спортивной статистики, "
            "поэтому он не может самостоятельно проверять текущие матчи.",
        )
        return

    if text == "⚽ Футбол":
        send_message(
            chat_id,
            "⚽ Футбольная аналитика\n\n"
            "Напиши вопрос или укажи матч, который хочешь разобрать.\n\n"
            "Важно: сейчас бот проверяет работу ИИ, "
            "но ещё не получает актуальную статистику автоматически."
        )
        return

    if text == "🎾 Теннис":
        send_message(
            chat_id,
            "🎾 Раздел тенниса пока в разработке. "
            "Можешь задать вопрос ИИ обычным сообщением."
        )
        return

    if text in [
        "🏀 Баскетбол",
        "🏐 Волейбол",
        "🎱 Снукер",
        "🎮 Dota 2",
        "🔫 CS2",
    ]:
        send_message(
            chat_id,
            f"{text}\n\n"
            "Раздел пока в разработке. "
            "Можешь задать ИИ вопрос обычным сообщением."
        )
        return

    send_message(chat_id, "⏳ Отправляю запрос бесплатной модели ИИ...")

    try:
        answer = ask_ai(text)
        send_message(chat_id, answer)

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print("Ошибка API:", error.code, details[:1500])

        if error.code == 401:
            message_text = (
                "Ошибка авторизации OpenRouter. "
                "Проверь API-ключ в переменных HOKAS."
            )
        elif error.code == 402:
            message_text = (
                "OpenRouter сообщает о проблеме с балансом или доступом. "
                "Проверь статус аккаунта и доступность бесплатных моделей. "
                "Ничего не оплачивай без необходимости."
            )
        elif error.code == 429:
            message_text = (
                "Бесплатная модель временно ограничила запросы. "
                "Попробуй немного позже."
            )
        else:
            message_text = (
                f"Ошибка OpenRouter: HTTP {error.code}. "
                "Попробуй позже; подробности записаны в консоль сервера."
            )

        send_message(chat_id, message_text)

    except Exception as error:
        print("Ошибка ИИ:", repr(error))
        send_message(
            chat_id,
            "Не удалось получить ответ от ИИ. "
            "Проверь консоль HOKAS или попробуй позже."
        )


def main():
    print("Спортивный аналитик-бот запускается...")

    telegram_request(
        "deleteWebhook",
        {"drop_pending_updates": False},
    )

    offset = None

    print("Бот запущен. Ожидаю сообщения.")

    while True:
        try:
            params = {"timeout": 25}

            if offset is not None:
                params["offset"] = offset

            url = TELEGRAM_API + "getUpdates?" + urllib.parse.urlencode(params)

            result = http_json(url, timeout=35)

            if not result.get("ok"):
                print("Ошибка Telegram:", result)
                time.sleep(3)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")

                if message:
                    try:
                        handle_message(message)
                    except Exception as error:
                        print("Ошибка обработки сообщения:", repr(error))

        except Exception as error:
            print("Ошибка соединения:", repr(error))
            time.sleep(3)


if __name__ == "__main__":
    main()
