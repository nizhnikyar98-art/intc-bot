import os
import logging
import threading
import re
import time
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
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Цифровой агент ИНТЦ «Русский» активен и готов к работе!"

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.getenv("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)

# --- ЛОГИКА ПРИВЕТСТВИЯ (/start) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "➖➖➖➖➖➖➖➖➖➖\n"
        "<b>Добро пожаловать в службу поддержки ИНТЦ «Русский»!</b>\n\n"
        "Я — ваш цифровой ассистент для оперативного взаимодействия с командой Центра.\n\n"
        "<b>Чем я могу помочь:</b>\n"
        "• <b>Задать вопрос:</b> Просто напишите сообщение в этот чат. Я передам его специалистам, и вы получите ответ здесь же.\n"
        "• <b>Изучить регламенты:</b> Нажмите кнопку <b>«Open»</b> в меню. Она откроет приложение с базой документов и описанием процедур.\n\n"
        "Пожалуйста, изложите ваш вопрос ниже.\n"
        "➖➖➖➖➖➖➖➖➖➖"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML')

# --- ЛОГИКА ПЕРЕСЫЛКИ: Пользователь -> Группа поддержки ---
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = os.getenv("GROUP_ID")

    if not update.message or not update.message.text or update.message.text.startswith('/'):
        return

    if group_id:
        user = update.message.from_user
        username = user.username or "Аноним"

        card_text = (
            f"📥 <b>Новое обращение</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"👤 <b>Отправитель:</b> @{username}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n\n"
            f"📝 <b>Вопрос:</b>\n{update.message.text}\n"
            f"➖➖➖➖➖➖➖➖➖➖"
        )

        try:
            await context.bot.send_message(chat_id=int(group_id), text=card_text, parse_mode='HTML')

            status_msg = (
                "📨 <b>Запрос зарегистрирован</b>\n"
                "<i>Ваше обращение передано в работу специалистам ИНТЦ.</i>"
            )
            await update.message.reply_text(status_msg, parse_mode='HTML')
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
    if not replied_msg.text:
        return

    # Ищем ID в тексте карточки (text содержит уже отрендеренный текст без HTML-тегов)
    match = re.search(r'ID:\s*(\d+)', replied_msg.text)

    if match:
        user_id = int(match.group(1))

        official_reply = (
            f"🏛 <b>Официальный ответ ИНТЦ «Русский»</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n\n"
            f"{update.message.text}\n\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"<i>Вы можете отправить уточняющий вопрос в ответ на это сообщение.</i>"
        )

        try:
            await context.bot.send_message(chat_id=user_id, text=official_reply, parse_mode='HTML')
            await update.message.reply_text("✅ <b>Ответ успешно доставлен</b>", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            await update.message.reply_text("❌ <b>Ошибка доставки: пользователь заблокировал бота</b>", parse_mode='HTML')

# --- ЗАПУСК БОТА ---
def main():
    # Запуск Flask в отдельном потоке — НЕ daemon, 
    # чтобы health check работал даже если бот ещё не запустился
    flask_thread = threading.Thread(target=run_flask, daemon=False)
    flask_thread.start()
    logger.info("Flask health-check сервер запущен.")

    token = os.getenv("BOT_TOKEN")
    group_id = os.getenv("GROUP_ID")

    if not token or not group_id:
        logger.error("Ошибка: Переменные окружения BOT_TOKEN или GROUP_ID не заданы!")
        # НЕ выходим — Flask должен продолжать работу, 
        # чтобы Koyeb не застрял в Provisioning.
        # Просто ждём, пока переменные не будут заданы.
        flask_thread.join()
        return

    application = ApplicationBuilder().token(token.strip()).build()

    application.add_handler(CommandHandler("start", start_command))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        forward_to_group
    ))

    application.add_handler(MessageHandler(
        filters.REPLY & filters.Chat(chat_id=int(group_id)),
        handle_group_reply
    ))

    logger.info("Бот ИНТЦ «Русский» успешно запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
