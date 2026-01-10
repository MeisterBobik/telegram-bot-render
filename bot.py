import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем токен из переменной окружения Railway
TOKEN = os.environ.get('BOT_TOKEN', 'ВАШ_ТОКЕН_ЗДЕСЬ')  # Railway добавит переменную

# Проверка токена
if TOKEN == 'ВАШ_ТОКЕН_ЗДЕСЬ':
    logging.error("❌ Токен не установлен! Добавьте BOT_TOKEN в переменные окружения Railway.")
    exit(1)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот переехал на Railway и работает 24/7!")

# Команда /railway
async def railway_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚄 Я теперь живу на Railway!\n"
        "• 500 часов бесплатно в месяц\n"
        "• Автоматические обновления\n"
        "• Работаю 24/7\n\n"
        "Исходный код можно посмотреть на GitHub"
    )

# Ответ на сообщения
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Вы: {update.message.text}\n\nБот работает на Railway! 🚄")

def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("railway", railway_command))
    
    # Регистрируем обработчик сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем бота
    port = int(os.environ.get('PORT', 8080))  # Railway использует PORT переменную
    print(f"✅ Бот запущен на Railway (порт: {port})!")
    print("🚀 Ожидаю сообщения...")
    
    # Polling режим (для Railway)
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()