import logging
import re
import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, CallbackContext
from dotenv import load_dotenv

load_dotenv()

# --- МИНИ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
app = Flask('')

@app.route('/')
def home():
    return "Бот ИНТЦ запущен и работает!"

def run_web():
    # Hugging Face требует порт 7860
    app.run(host='0.0.0.0', port=7860)

# --- ЛОГИКА БОТА ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
import os
import logging
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Мини-сервер для Koyeb (обязателен, чтобы сервис не выключался)
app = Flask(__name__)
@app.route('/')
def index():
    return "Бот ИНТЦ работает на Koyeb! Все системы в норме."

def run_flask():
    # Koyeb сам скажет нам, какой порт использовать через переменную PORT
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Логика пересылки
async def forward_to_group(update, context):
    group_id = os.getenv("GROUP_ID")
    if update.message and group_id:
        user = update.message.from_user
        text = f"Вопрос от @{user.username or 'Аноним'} (ID: {user.id}):\n{update.message.text}"
        try:
            await context.bot.send_message(chat_id=int(group_id), text=text)
            await update.message.reply_text("Ваш вопрос передан в поддержку.")
        except Exception as e:
            logger.error(f"Ошибка пересылки: {e}")

def main():
    # 1. Запуск веб-сервера
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Берем токен из переменных окружения (введем в Koyeb)
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("Токен не найден!")
        return

    # 3. Запуск бота
    application = ApplicationBuilder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, forward_to_group))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()