import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

if not OPENROUTER_API_KEY:
    raise RuntimeError("Не задана переменная OPENROUTER_API_KEY")


TELEGRAM_API = (
    "https://api.telegram.org/bot"
    + TELEGRAM_BOT_TOKEN
    + "/"
)

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"


SPORTS = {
    "⚽ Футбол": "футбол",
    "🎾 Теннис": "теннис",
    "🏀 Баскетбол": "баскетбол",
    "🏐 Волейбол": "волейбол",
    "🎱 Снукер": "снукер",
    "🎮 Dota 2": "Dota 2",
    "🔫 CS2": "Counter-Strike 2",
}


def http_json(url, data=None, headers=None, timeout=30):
    request_headers = {
        "User-Agent": "SportsAnalystBot/1.0",
    }

    if headers:
        request_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method="POST" if body is not None else "GET",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = response.read().decode("utf-8")

    return json.loads(result)


def telegram_request(method, data=None):
    url = TELEGRAM_API + method
    return http_json(url, data=data, timeout=40)


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,
        }

    try:
        telegram_request("sendMessage", payload)
    except Exception as error:
        print("Ошибка отправки сообщения:", repr(error))


def make_keyboard():
    return [
        ["⚽ Футбол", "🎾 Теннис"],
        ["🏀 Баскетбол", "🏐 Волейбол"],
        ["🎱 Снукер"],
        ["🎮 Dota 2", "🔫 CS2"],
    ]


def ask_ai(question):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты спортивный аналитик и отвечаешь на русском языке. "
                    "Помогай анализировать футбол, теннис, баскетбол, "
                    "волейбол, снукер, Dota 2 и Counter-Strike 2. "
                    "Объясняй аргументы, сильные и слабые стороны команд "
                    "и возможные сценарии. Не выдумывай текущие результаты, "
                    "составы, травмы, коэффициенты и статистику. "
                    "Если у тебя нет актуальных данных, честно сообщи об этом. "
                    "Не обещай гарантированный выигрыш и указывай на риски "
                    "при обсуждении ставок."
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

    headers = {
        "Authorization": "Bearer " + OPENROUTER_API_KEY,
        "HTTP-Referer": "https://openrouter.ai/",
        "X-Title": "Sports Analyst Telegram Bot",
    }

    result = http_json(
        OPENROUTER_API,
        data=payload,
        headers=headers,
        timeout=60,
    )

    choices = result.get("choices", [])

    if not choices:
        raise RuntimeError("ИИ не вернул ответ")

    message = choices[0].get("message", {})
    answer = message.get("content", "")

    if isinstance(answer, list):
        answer = "\n".join(
            item.get("text", "")
            for item in answer
            if isinstance(item, dict)
        )

    answer = str(answer).strip()

    if not answer:
        raise RuntimeError("ИИ вернул пустой ответ")

    return answer


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return

    text = text.strip()

    if text.startswith("/start"):
        send_message(
            chat_id,
            "Привет! Я спортивный аналитик.\n\n"
            "Выбери вид спорта кнопкой или напиши свой вопрос "
            "для анализа.\n\n"
            "Важно: сейчас я не получаю автоматически актуальную "
            "статистику матчей. Для точного анализа укажи команды, "
            "турнир и дату матча.",
            make_keyboard(),
        )
        return

    if text in SPORTS:
        sport = SPORTS[text]
        send_message(
            chat_id,
            "Выбран спорт: " + sport + ".\n\n"
            "Напиши, что именно нужно разобрать: матч, команды, "
            "игроков или прогноз. Если нужны актуальные данные, "
            "укажи матч и дату.",
            make_keyboard(),
        )
        return

    send_message(chat_id, "Анализирую вопрос. Подожди немного...")

    try:
        answer = ask_ai(text)

        # Telegram ограничивает длину одного сообщения.
        max_length = 4000
        for start in range(0, len(answer), max_length):
            send_message(chat_id, answer[start:start + max_length])

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print("Ошибка OpenRouter:", error.code, details)

        if error.code == 401:
            reply = (
                "Ошибка авторизации OpenRouter. Проверь API-ключ "
                "в переменной OPENROUTER_API_KEY."
            )
        elif error.code == 402:
            reply = (
                "OpenRouter сообщает о проблеме с доступным балансом "
                "или лимитами. Проверь настройки своего аккаунта."
            )
        elif error.code == 429:
            reply = (
                "Превышен лимит запросов к ИИ. Попробуй немного позже."
            )
        else:
            reply = (
                "OpenRouter вернул ошибку HTTP "
                + str(error.code)
                + ". Подробности сохранены в журнале сервера."
            )

        send_message(chat_id, reply)

    except Exception as error:
        print("Ошибка обработки запроса:", repr(error))
        send_message(
            chat_id,
            "Не удалось получить ответ от ИИ. Попробуй ещё раз позже.",
        )


def main():
    print("Спортивный аналитик-бот запускается...")

    # Удаляем webhook, чтобы использовать long polling.
    try:
        telegram_request(
            "deleteWebhook",
            {"drop_pending_updates": False},
        )
    except Exception as error:
        print("Не удалось удалить webhook:", repr(error))

    print("Бот запущен. Ожидаю сообщения.")

    offset = None

    while True:
        try:
            params = {"timeout": 25}

            if offset is not None:
                params["offset"] = offset

            query = urllib.parse.urlencode(params)
            url = TELEGRAM_API + "getUpdates?" + query

            result = http_json(url, timeout=40)

            if not result.get("ok"):
                print("Telegram вернул ошибку:", result)
                time.sleep(3)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if message:
                    handle_message(message)

        except Exception as error:
            print("Ошибка основного цикла:", repr(error))
            time.sleep(3)


if __name__ == "__main__":
    main()
