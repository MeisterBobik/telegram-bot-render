import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Получаем токен
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен!")
    exit(1)

# Команда /start с кнопками
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Создаем клавиатуру с кнопками "Да" и "Нет"
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="yes"),
            InlineKeyboardButton("❌ Нет", callback_data="no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Вы хотите чтобы я рассказал что я умею?",
        reply_markup=reply_markup
    )

# Обработка нажатия кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Ответим на callback, чтобы убрать "часики" у кнопки
    
    if query.data == "yes":
        await query.edit_message_text(
            text="🤖 **Что я умею:**\n\n"
                 "• Отвечать на ваши сообщения (эхо)\n"
                 "• Команда /start - начать диалог\n"
                 "• Команда /help - помощь\n"
                 "• Команда /time - текущее время\n"
                 "• Команда /info - информация о вас\n\n"
                 "Я работаю на Render 24/7! 🚀",
            parse_mode="Markdown"
        )
    elif query.data == "no":
        await query.edit_message_text(
            text="Хорошо! Если передумаете - просто напишите /help или задайте вопрос!"
        )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 **Доступные команды:**\n\n"
        "/start - Начать диалог с кнопками\n"
        "/help - Помощь и список команд\n"
        "/time - Текущее время\n"
        "/info - Информация о вас\n\n"
        "Просто напишите сообщение, и я его повторю!"
    )

# Команда /time
async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M:%S")
    await update.message.reply_text(f"⏰ Текущее время: {current_time}")

# Команда /info
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👤 **Информация о вас:**\n"
        f"• Имя: {user.first_name}\n"
        f"• Фамилия: {user.last_name or 'не указана'}\n"
        f"• Username: @{user.username or 'не указан'}\n"
        f"• ID: {user.id}"
    )

# Ответ на обычные сообщения (эхо)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Вы сказали: {update.message.text}")

def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("info", info_command))
    
    # Регистрируем обработчик кнопок (callback)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрируем обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем бота
    logging.info("🚀 Бот запущен с кнопками!")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
