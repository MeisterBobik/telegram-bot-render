import logging
import pytz
import asyncio
from datetime import datetime, time as dt_time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
MAIN_MENU, SET_REMINDER_TEXT, SET_REMINDER_TIME = range(3)

# Хранение данных пользователей
user_data_store = {}
time_timer_tasks = {}
reminder_tasks = {}

# Часовой пояс Воронежа (MSK)
VORONEZH_TZ = pytz.timezone('Europe/Moscow')

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Инициализация данных пользователя
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            'time_timer_active': False,
            'reminders': []
        }
    
    welcome_text = (
        "Этот Бот предназначен для того чтобы писать каждую минуту какое сейчас время "
        "и чтобы можно было написать что-то что ты хочешь чтоб тебе бот прислал в определённое время."
    )
    
    keyboard = [
        [InlineKeyboardButton("⏰ Таймер времени Воронежа", callback_data='toggle_timer')],
        [InlineKeyboardButton("📝 Запланировать сообщение", callback_data='set_reminder')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    return MAIN_MENU

# Функция отправки времени каждую минуту
async def send_time_periodically(user_id: int, app):
    while user_id in user_data_store and user_data_store[user_id].get('time_timer_active', False):
        try:
            current_time = datetime.now(VORONEZH_TZ).strftime("%H:%M:%S")
            await app.bot.send_message(
                chat_id=user_id,
                text=f"🕒 Сейчас в Воронеже: {current_time}"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки времени: {e}")
            break
        await asyncio.sleep(60)  # Ждем 1 минуту

# Обработка таймера времени
async def toggle_time_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in user_data_store:
        user_data_store[user_id] = {'time_timer_active': False, 'reminders': []}
    
    user_data = user_data_store[user_id]
    
    if user_data['time_timer_active']:
        # Выключаем таймер
        user_data['time_timer_active'] = False
        if user_id in time_timer_tasks:
            time_timer_tasks[user_id].cancel()
            del time_timer_tasks[user_id]
        
        await query.edit_message_text(
            text="Таймер времени Воронежа выключен.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ])
        )
    else:
        # Включаем таймер
        user_data['time_timer_active'] = True
        
        # Запускаем задачу отправки времени
        task = asyncio.create_task(send_time_periodically(user_id, context.application))
        time_timer_tasks[user_id] = task
        
        # Отправляем первое сообщение
        current_time = datetime.now(VORONEZH_TZ).strftime("%H:%M:%S")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🕒 Таймер включен! Сейчас в Воронеже: {current_time}"
        )
        
        await query.edit_message_text(
            text="Таймер времени Воронежа включен!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔕 Выключить таймер", callback_data='toggle_timer')],
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ])
        )
    
    return MAIN_MENU

# Установка напоминания
async def set_reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📝 Напишите текст сообщения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ])
    )
    
    return SET_REMINDER_TEXT

async def set_reminder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['reminder_text'] = update.message.text
    
    await update.message.reply_text(
        text=f"📝 Текст сохранен!\n\n"
             f"🕒 Теперь введите время (ЧЧ:ММ):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ])
    )
    
    return SET_REMINDER_TIME

async def set_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    time_str = update.message.text
    
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        
        reminder_id = f"reminder_{user_id}_{int(datetime.now().timestamp())}"
        
        # Сохраняем напоминание
        if user_id not in user_data_store:
            user_data_store[user_id] = {'reminders': [], 'time_timer_active': False}
        
        user_data_store[user_id]['reminders'].append({
            'id': reminder_id,
            'text': context.user_data['reminder_text'],
            'time': f"{hour:02d}:{minute:02d}"
        })
        
        # Создаем задачу для напоминания
        task = asyncio.create_task(
            send_reminder_at_time(user_id, context.user_data['reminder_text'], reminder_id, hour, minute, context.application)
        )
        reminder_tasks[reminder_id] = task
        
        await update.message.reply_text(
            text=f"✅ Напоминание установлено на {hour:02d}:{minute:02d}!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 Отключить", callback_data=f'disable_{reminder_id}')],
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ])
        )
        
        if 'reminder_text' in context.user_data:
            del context.user_data['reminder_text']
        
    except:
        await update.message.reply_text(
            text="❌ Неверный формат. Введите ЧЧ:ММ (например, 14:30)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ])
        )
        return SET_REMINDER_TIME
    
    return MAIN_MENU

# Функция отправки напоминания в указанное время
async def send_reminder_at_time(user_id: int, text: str, reminder_id: str, hour: int, minute: int, app):
    try:
        while True:
            now = datetime.now(VORONEZH_TZ)
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if now >= target_time:
                target_time += timedelta(days=1)
            
            wait_seconds = (target_time - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            
            if reminder_id not in reminder_tasks:
                break
                
            await app.bot.send_message(
                chat_id=user_id,
                text=f"🔔 Напоминание:\n\n{text}"
            )
            
            # Удаляем задачу после отправки
            if reminder_id in reminder_tasks:
                del reminder_tasks[reminder_id]
            if user_id in user_data_store:
                user_data_store[user_id]['reminders'] = [
                    r for r in user_data_store[user_id]['reminders'] 
                    if r['id'] != reminder_id
                ]
            break
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания: {e}")

# Отключение напоминания
async def disable_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reminder_id = query.data.replace('disable_', '')
    
    if reminder_id in reminder_tasks:
        reminder_tasks[reminder_id].cancel()
        del reminder_tasks[reminder_id]
    
    await query.edit_message_text(
        text="✅ Напоминание отключено.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ])
    )
    
    return MAIN_MENU

# Основная функция
def main():
    # Создаем Application
    application = Application.builder().token("8517372931:AAG66lYcPsP_6bwQA4QVaMa-A_YYYWWBmQQ").build()
    
    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(toggle_time_timer, pattern='^toggle_timer$'),
                CallbackQueryHandler(set_reminder_start, pattern='^set_reminder$'),
                CallbackQueryHandler(start, pattern='^back_to_main$'),
                CallbackQueryHandler(disable_reminder, pattern='^disable_.*$')
            ],
            SET_REMINDER_TEXT: [
                CallbackQueryHandler(start, pattern='^back_to_main$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_reminder_text)
            ],
            SET_REMINDER_TIME: [
                CallbackQueryHandler(start, pattern='^back_to_main$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_reminder_time)
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
