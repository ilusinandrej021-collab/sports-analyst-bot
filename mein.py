import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

SPORTS = [
    ["🏀 Баскетбол", "🏐 Волейбол"],
    ["🎾 Теннис", "🎱 Снукер"],
    ["🎮 Dota 2", "🔫 CS2"],
    ["📊 Анализ матчей", "💰 Мой баланс"],
    ["ℹ️ Помощь"],
]

WELCOME = (
    "Привет! Я твой спортивный аналитик. 🏆\n\n"
    "Выбери дисциплину в меню ниже.\n\n"
    "Сейчас работает базовая версия. "
    "Для реального анализа позже подключим спортивные данные."
)

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    keyboard = ReplyKeyboardMarkup(
        SPORTS,
        resize_keyboard=True,
    )
    await update.message.reply_text(
        WELCOME,
        reply_markup=keyboard,
    )

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "Выбирай вид спорта в меню. "
        "Команда /start открывает меню заново."
    )

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text

    replies = {
        "🏀 Баскетбол": "🏀 Раздел баскетбола выбран. Подключение статистики добавим следующим этапом.",
        "🏐 Волейбол": "🏐 Раздел волейбола выбран. Подключение статистики добавим следующим этапом.",
        "🎾 Теннис": "🎾 Раздел тенниса выбран. Подключение статистики добавим следующим этапом.",
        "🎱 Снукер": "🎱 Раздел снукера выбран. Подключение статистики добавим следующим этапом.",
        "🎮 Dota 2": "🎮 Раздел Dota 2 выбран. Подключение статистики добавим следующим этапом.",
        "🔫 CS2": "🔫 Раздел CS2 выбран. Подключение статистики добавим следующим этапом.",
        "📊 Анализ матчей": "📊 Для анализа потребуются актуальные матчи, коэффициенты и статистические данные.",
        "💰 Мой баланс": "💰 Автоматическое получение баланса Фонбет пока не подключено. Не отправляй мне пароль или коды доступа.",
        "ℹ️ Помощь": "Используй меню для выбора дисциплины. Команда /start открывает его заново.",
    }

    await update.message.reply_text(
        replies.get(text, "Не понял запрос. Нажми /start, чтобы открыть меню.")
    )

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Не задана переменная TELEGRAM_BOT_TOKEN"
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    app.run_polling()

if __name__ == "__main__":
    main()
