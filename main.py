import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import html

# ==========================================
# НАСТРОЙКИ
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Бесплатный маршрутизатор моделей OpenRouter.
MODEL = "openrouter/free"

MAX_HISTORY = 12
MAX_TELEGRAM_LENGTH = 4000

SYSTEM_PROMPT = """
Ты — спортивный аналитик и собеседник, отвечающий на русском языке.

ТВОИ ЗАДАЧИ:
1. Анализировать футбольные и другие спортивные матчи.
2. Сравнивать команды и отдельных игроков.
3. Анализировать последние результаты, форму, статистику,
   личные встречи, составы и травмы, когда данные доступны.
4. Отвечать на любые вопросы о спорте обычным языком.
5. Поддерживать диалог и учитывать предыдущие сообщения.
6. Объяснять, на чём основаны твои выводы.

ПРАВИЛА АНАЛИЗА:
- Если пользователь просит актуальную информацию, используй
  поиск в интернете, если соответствующий инструмент доступен.
- Учитывай текущую дату, а не предполагай, что старые сведения
  всё ещё актуальны.
- Не выдумывай результаты матчей, статистику, травмы,
  составы, коэффициенты или новости.
- Если надёжных данных недостаточно, прямо сообщи об этом.
- Отделяй подтверждённые факты от предположений.
- При анализе матча оценивай форму команд, результаты,
  домашнее поле, кадровую ситуацию и другие доступные факторы.
- Не обещай гарантированную победу и не выдавай прогноз
  за достоверный результат.
- Если пользователь не указал дату матча, уточни её,
  когда без этого нельзя правильно определить встречу.
- Если пользователь просит сравнить последние пять матчей,
  не придумывай эти пять матчей: найди данные или объясни,
  почему не удалось их получить.
- Если пользователь задаёт обычный вопрос, отвечай прямо,
  без лишних вступлений.

ФОРМАТ:
Пиши понятно, структурированно и по существу.
Для анализа матча по возможности указывай:
1. Текущую форму команд.
2. Сильные и слабые стороны.
3. Ключевые факторы матча.
4. Вероятный сценарий игры.
5. Итоговую оценку и основные риски.
6. Источники актуальных сведений, если они использовались.

Ты не отправляешь сообщения самостоятельно.
Ты отвечаешь только на сообщения пользователя.
"""

# ==========================================
# КНОПКИ TELEGRAM
# ==========================================

KEYBOARD = {
    "keyboard": [
        ["⚽ Футбол", "🎾 Теннис"],
        ["🏀 Баскетбол", "🏐 Волейбол"],
        ["🎱 Снукер"],
        ["🎮 Dota 2", "🔫 CS2"],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

SPORTS = {
    "⚽ футбол": "футбол",
    "🎾 теннис": "теннис",
    "🏀 баскетбол": "баскетбол",
    "🏐 волейбол": "волейбол",
    "🎱 снукер": "снукер",
    "🎮 dota 2": "Dota 2",
    "🔫 cs2": "CS2",
}

# История диалога отдельно для каждого чата.
chat_histories = {}

# ==========================================
# TELEGRAM API
# ==========================================

def telegram_request(method, data=None, timeout=40):
    url = f"{TELEGRAM_URL}/{method}"

    payload = json.dumps(data or {}).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(
            result.get("description", "Ошибка Telegram API")
        )

    return result.get("result")


def send_message(chat_id, text, show_keyboard=True):
    if not text:
        text = "Не удалось получить ответ. Попробуй ещё раз."

    # Не используем HTML-разметку для текста ИИ:
    # так случайные символы не ломают сообщение.
    chunks = []

    while len(text) > MAX_TELEGRAM_LENGTH:
        split_at = text.rfind(
            "\n",
            0,
            MAX_TELEGRAM_LENGTH,
        )

        if split_at < MAX_TELEGRAM_LENGTH // 2:
            split_at = MAX_TELEGRAM_LENGTH

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    for index, chunk in enumerate(chunks):
        data = {
            "chat_id": chat_id,
            "text": chunk,
        }

        if show_keyboard and index == len(chunks) - 1:
            data["reply_markup"] = KEYBOARD

        telegram_request("sendMessage", data)


def send_typing(chat_id):
    try:
        telegram_request(
            "sendChatAction",
            {
                "chat_id": chat_id,
                "action": "typing",
            },
        )
    except Exception:
        pass


# ==========================================
# OPENROUTER API
# ==========================================

def ask_ai(chat_id, user_text):
    if not OPENROUTER_KEY:
        return (
            "Не настроен OPENROUTER_API_KEY.\n"
            "Добавь ключ в переменные окружения HOKAS."
        )

    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    history = chat_histories[chat_id]

    history.append({
        "role": "user",
        "content": user_text,
    })

    # Ограничиваем историю, чтобы не раздувать запросы.
    if len(history) > MAX_HISTORY:
        del history[:-MAX_HISTORY]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ] + history

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1200,
        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_results": 5,
                    "max_total_results": 10,
                },
            }
        ],
    }

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://openrouter.ai",
            "X-Title": "Sports Analyst Bot",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=100) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        answer = result["choices"][0]["message"]["content"]

        if isinstance(answer, list):
            answer = "\n".join(
                item.get("text", "")
                for item in answer
                if isinstance(item, dict)
            )

        if not answer:
            answer = (
                "Модель не вернула текстовый ответ. "
                "Попробуй переформулировать запрос."
            )

        history.append({
            "role": "assistant",
            "content": answer,
        })

        return answer

    except urllib.error.HTTPError as error:
        details = error.read().decode(
            "utf-8",
            errors="replace",
        )

        print(
            f"OpenRouter HTTP {error.code}: {details[:1000]}",
            flush=True,
        )

        if error.code == 401:
            return (
                "Ошибка авторизации OpenRouter. "
                "Проверь OPENROUTER_API_KEY в HOKAS."
            )

        if error.code == 402:
            return (
                "OpenRouter сообщает о недостатке средств "
                "или доступного лимита. Проверь баланс "
                "и доступность выбранной модели."
            )

        if error.code == 429:
            return (
                "Слишком много запросов или достигнут лимит. "
                "Подожди немного и попробуй снова."
            )

        if error.code == 400:
            return (
                "OpenRouter отклонил формат запроса. "
                "Возможно, выбранная бесплатная модель "
                "не поддерживает поиск. Подробности "
                "записаны в консоль сервера."
            )

        return (
            f"Ошибка OpenRouter: HTTP {error.code}. "
            "Подробности доступны в консоли сервера."
        )

    except urllib.error.URLError as error:
        print(f"OpenRouter connection error: {error}", flush=True)

        return (
            "Не удалось подключиться к OpenRouter. "
            "Попробуй ещё раз немного позже."
        )

    except Exception as error:
        print(f"AI error: {error}", flush=True)

        return (
            "Не удалось обработать запрос. "
            "Попробуй ещё раз."
        )


# ==========================================
# ОБРАБОТКА СООБЩЕНИЙ
# ==========================================

def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return

    text = text.strip()

    if not text:
        return

    normalized = text.lower()

    if normalized.startswith("/start"):
        send_message(
            chat_id,
            "Привет! Я спортивный ИИ-аналитик. ⚽\n\n"
            "Можешь задавать мне любые вопросы о спорте.\n\n"
            "Например:\n"
            "• Проанализируй матч Реал — Барселона.\n"
            "• Сравни последние игры двух команд.\n"
            "• Какая команда сейчас в лучшей форме?\n"
            "• Найди ближайшие матчи популярных лиг.\n"
            "• Объясни сильные и слабые стороны команды.\n\n"
            "Я постараюсь использовать актуальные источники, "
            "когда это необходимо и доступно.\n\n"
            "Выбери вид спорта кнопкой или просто напиши вопрос.",
        )
        return

    if normalized.startswith("/reset"):
        chat_histories.pop(chat_id, None)

        send_message(
            chat_id,
            "История нашего диалога очищена. "
            "Можем начать новую тему!",
        )
        return

    if normalized.startswith("/help"):
        send_message(
            chat_id,
            "Я могу обсуждать спортивные события, "
            "анализировать матчи, сравнивать команды "
            "и отвечать на вопросы о спорте.\n\n"
            "Просто напиши свой вопрос.\n\n"
            "/start — главное меню\n"
            "/reset — начать новый диалог\n"
            "/help — помощь",
        )
        return

    if normalized in SPORTS:
        sport = SPORTS[normalized]

        send_message(
            chat_id,
            f"Выбрали: {sport}.\n\n"
            f"Что хочешь узнать о {sport}?\n"
            "Например, попроси проанализировать матч, "
            "сравнить команды или найти ближайшие игры.",
        )
        return

    send_typing(chat_id)

    answer = ask_ai(chat_id, text)

    send_message(chat_id, answer)


# ==========================================
# ЗАПУСК БОТА
# ==========================================

def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "Не задана переменная TELEGRAM_BOT_TOKEN."
        )

    if not OPENROUTER_KEY:
        raise RuntimeError(
            "Не задана переменная OPENROUTER_API_KEY."
        )

    print("Sports Analyst Bot запускается...", flush=True)

    # Удаляем webhook, поскольку используем getUpdates.
    telegram_request(
        "deleteWebhook",
        {"drop_pending_updates": False},
    )

    offset = None

    while True:
        try:
            params = {"timeout": 30}

            if offset is not None:
                params["offset"] = offset

            query = urllib.parse.urlencode(params)

            updates = telegram_request(
                f"getUpdates?{query}",
                timeout=40,
            )

            for update in updates:
                offset = update["update_id"] + 1

                message = update.get("message")

                if message:
                    try:
                        handle_message(message)
                    except Exception as error:
                        print(
                            f"Message handling error: {error}",
                            flush=True,
                        )

                        chat_id = message.get(
                            "chat", {}
                        ).get("id")

                        if chat_id:
                            try:
                                send_message(
                                    chat_id,
                                    "Произошла внутренняя ошибка. "
                                    "Попробуй ещё раз.",
                                )
                            except Exception:
                                pass

        except KeyboardInterrupt:
            print("Бот остановлен.", flush=True)
            break

        except Exception as error:
            print(
                f"Polling error: {error}",
                flush=True,
            )
            time.sleep(3)


if __name__ == "__main__":
    main()
