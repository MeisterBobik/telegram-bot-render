import os
import sys
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Получаем токен из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logging.error("❌ BOT_TOKEN не найден! Установите переменную окружения в настройках Koyeb.")
    sys.exit(1)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает на Koyeb!")

# Ответ на сообщения
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

def main():
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        
        # Регистрируем команды
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Запускаем бота
        logging.info("🚀 Запускаю бота на Koyeb...")
        print("=== Бот стартовал ===")
        
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
