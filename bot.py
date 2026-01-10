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

# Токен из переменных окружения Render
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен! Добавьте в Environment Variables на Render.")
    sys.exit(1)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает на Render 24/7!")

# Ответ на сообщения
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Вы сказали: {update.message.text}")

def main():
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        logging.info("🚀 Бот запускается на Render...")
        print("=== Бот работает! ===")
        
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
