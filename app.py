import os
import logging
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# 1. Настройка логов (Исправлено)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Мини-сервер для Koyeb (Health Check)
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот ИНТЦ «Русский» успешно запущен на Koyeb!"

def run_flask():
    # Koyeb выдает порт автоматически через переменную PORT
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. Логика пересылки сообщений
async def forward_to_group(update, context):
    group_id = os.getenv("GROUP_ID")
    if update.message and group_id:
        user = update.message.from_user
        username = user.username or "Аноним"
        text = f"Вопрос от @{username} (ID: {user.id}):\n{update.message.text}"
        try:
            await context.bot.send_message(chat_id=int(group_id), text=text)
            await update.message.reply_text("Ваш вопрос передан в поддержку.")
        except Exception as e:
            logger.error(f"Ошибка при пересылке: {e}")

def main():
    # Запуск Flask в фоне, чтобы Koyeb не ругался на Health Check
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не найден!")
        return

    # Запуск Telegram бота
    application = ApplicationBuilder().token(token.strip()).build()
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, forward_to_group))
    
    logger.info("Бот ИНТЦ прошел проверку и запускается...")
    application.run_polling()

if __name__ == "__main__":
    main()
