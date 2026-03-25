import os
import logging
import threading
import re
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- МИНИ-СЕРВЕР (ДЛЯ KOYEB/HEALTH CHECK) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Цифровой агент ИНТЦ «Русский» активен и готов к работе!"

def run_flask():
    # Порт подхватывается автоматически из настроек сервиса
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА ПРИВЕТСТВИЯ (/start) ---
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

# --- ЛОГИКА ПЕРЕСЫЛКИ: Пользователь -> Группа поддержки ---
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")
    
    # Игнорируем команды (начинающиеся с /), чтобы не спамить в группу
    if not update.message or not update.message.text or update.message.text.startswith('/'):
        return

    if group_id:
        user = update.message.from_user
        username = user.username or "Аноним"
        
        # Оформление карточки вопроса для сотрудников (стиль "Бланк")
        card_text = (
            f"📥 **Новое обращение**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Отправитель:** @{username}\n"
            f"🆔 **ID:** `{user.id}`\n\n"
            f"📝 **Вопрос:**\n{update.message.text}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        try:
            await context.bot.send_message(chat_id=int(group_id), text=card_text, parse_mode='Markdown')
            
            # Статусное уведомление для пользователя (курсив для легкости)
            status_msg = (
                "📨 **Запрос зарегистрирован**\n"
                "_Ваше обращение передано в работу специалистам ИНТЦ._"
            )
            await update.message.reply_text(status_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка пересылки: {e}")

# --- ЛОГИКА ОТВЕТА: Группа поддержки -> Пользователь ---
async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")
    
    if not update.message or not update.message.reply_to_message or not update.message.text:
        return
    if str(update.message.chat_id) != group_id:
        return

    replied_msg = update.message.reply_to_message
    # Извлекаем ID из карточки вопроса (ищем цифры после "ID: ")
    match = re.search(r'ID: (\d+)', replied_msg.text)
    
    if match:
        user_id = int(match.group(1))
        
        # Оформление официального ответа для пользователя
        official_reply = (
            f"🏛 **Официальный ответ ИНТЦ «Русский»**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{update.message.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f" _Вы можете отправить уточняющий вопрос в ответ на это сообщение._"
        )
        
        try:
            await context.bot.send_message(chat_id=user_id, text=official_reply, parse_mode='Markdown')
            await update.message.reply_text("✅ **Ответ успешно доставлен**")
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            await update.message.reply_text("❌ **Ошибка доставки: пользователь заблокировал бота**")

# --- ЗАПУСК БОТА ---
def main():
    # Запуск Flask в отдельном потоке (keep-alive)
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = os.getenv("BOT_TOKEN")
    group_id = os.getenv("GROUP_ID")
    
    if not token or not group_id:
        logger.error("Ошибка: Переменные окружения BOT_TOKEN или GROUP_ID не заданы!")
        return

    application = ApplicationBuilder().token(token.strip()).build()
    
    # 1. Обработка команды /start
    application.add_handler(CommandHandler("start", start_command))
    
    # 2. Обработка входящих вопросов (в личке бота)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, 
        forward_to_group
    ))
    
    # 3. Обработка ответов сотрудников (в группе поддержки)
    application.add_handler(MessageHandler(
        filters.REPLY & filters.Chat(chat_id=int(group_id)), 
        handle_group_reply
    ))
    
    logger.info("Бот ИНТЦ «Русский» успешно запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
