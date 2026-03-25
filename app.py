import os
import logging
import threading
import re
from flask import Flask
from telegram import Update
# Добавлен CommandHandler
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

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

# НОВЫЙ ОБРАБОТЧИК: Специально для команды /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "**Добро пожаловать в службу поддержки ИНТЦ «Русский»!**\n\n"
        "Я — ваш цифровой ассистент для оперативного взаимодействия с командой Центра.\n\n"
        "**Чем я могу помочь:**\n"
        "• **Задать вопрос:** Просто напишите сообщение в этот чат. Я передам его специалистам, и вы получите ответ здесь же.\n"
        "• **Изучить регламенты:** Нажмите кнопку **«Open»** в меню. Она откроет приложение с базой документов и описанием процедур.\n\n"
        "Пожалуйста, изложите ваш вопрос ниже."
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# 1. ПЕРЕСЫЛКА: Теперь игнорирует команды
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")
    
    # Если это команда (начинается с /), выходим из функции
    if update.message.text.startswith('/'):
        return

    if update.message and group_id:
        user = update.message.from_user
        username = user.username or "Аноним"
        text = f"Вопрос от @{username} (ID: {user.id}):\n{update.message.text}"
        try:
            await context.bot.send_message(chat_id=int(group_id), text=text)
            await update.message.reply_text("Ваш вопрос передан в поддержку.")
        except Exception as e:
            logger.error(f"Ошибка пересылки: {e}")

# 2. ОТВЕТ: Без изменений (работает корректно)
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")
    if not update.message or not update.message.reply_to_message:
        return
    if str(update.message.chat_id) != group_id:
        return

    replied_msg = update.message.reply_to_message
    match = re.search(r'\(ID: (\d+)\)', replied_msg.text)
    if match:
        user_id = int(match.group(1))
        try:
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
            await update.message.reply_text("✅ Ответ отправлен пользователю.")
        except Exception as e:
            logger.error(f"Ошибка отправки ответа: {e}")
            await update.message.reply_text("❌ Не удалось отправить ответ.")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = os.getenv("BOT_TOKEN")
    group_id = os.getenv("GROUP_ID")
    if not token or not group_id:
        logger.error("Переменные окружения не найдены!")
        return

    application = ApplicationBuilder().token(token.strip()).build()
    
    # ПОРЯДОК ВАЖЕН: сначала обрабатываем команду /start
    application.add_handler(CommandHandler("start", start_command))
    
    # Обработчик для обычного текста (теперь он пропустит /start мимо себя)
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, forward_to_group))
    
    # Обработчик для ответов в группе
    application.add_handler(MessageHandler(filters.REPLY & filters.Chat(chat_id=int(group_id)), handle_group_reply))
    
    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
