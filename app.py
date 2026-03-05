import os
import logging
import threading
import re
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def index():
    return "Цифровой агент ИНТЦ «Русский» активен!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 1. ПЕРЕСЫЛКА: Из лички бота -> В группу поддержки
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")
    if update.message and group_id:
        user = update.message.from_user
        username = user.username or "Аноним"
        text = f"Вопрос от @{username} (ID: {user.id}):\n{update.message.text}"
        try:
            await context.bot.send_message(chat_id=int(group_id), text=text)
            await update.message.reply_text("Ваш вопрос передан в поддержку.")
        except Exception as e:
            logger.error(f"Ошибка пересылки: {e}")

# 2. ОТВЕТ: Из группы поддержки -> Обратно пользователю
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")
    
    # Проверяем, что это ответ в нужной группе
    if not update.message or not update.message.reply_to_message:
        return
    if str(update.message.chat_id) != group_id:
        return

    replied_msg = update.message.reply_to_message
    
    # Ищем ID пользователя в тексте сообщения, на которое вы ответили
    match = re.search(r'\(ID: (\d+)\)', replied_msg.text)
    if match:
        user_id = int(match.group(1))
        try:
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
            await update.message.reply_text("✅ Ответ отправлен пользователю.")
        except Exception as e:
            logger.error(f"Ошибка отправки ответа: {e}")
            await update.message.reply_text("❌ Не удалось отправить ответ. Возможно, пользователь заблокировал бота.")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = os.getenv("BOT_TOKEN")
    group_id = os.getenv("GROUP_ID")
    if not token or not group_id:
        logger.error("Переменные окружения не найдены!")
        return

    application = ApplicationBuilder().token(token.strip()).build()
    
    # Обработчик для личных сообщений (от пользователя к вам)
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, forward_to_group))
    
    # Обработчик для ответов в группе (от вас к пользователю)
    application.add_handler(MessageHandler(filters.REPLY & filters.Chat(chat_id=int(group_id)), handle_group_reply))
    
    logger.info("Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == "__main__":
    main()
