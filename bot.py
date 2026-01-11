import logging
import pytz
import asyncio
from datetime import datetime, time as dt_time
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

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
active_timers = {}
active_reminders = {}

# Часовой пояс Воронежа (MSK)
VORONEZH_TZ = pytz.timezone('Europe/Moscow')

# Функция для запуска планировщика
async def start_scheduler(app):
    scheduler = AsyncIOScheduler(timezone=VORONEZH_TZ)
    scheduler.start()
    app.scheduler = scheduler

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

# Обработка таймера времени
async def toggle_time_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = user_data_store[user_id]
    
    if user_data['time_timer_active']:
        # Выключаем таймер
        user_data['time_timer_active'] = False
        if user_id in active_timers:
            job = active_timers[user_id]
            if job:
                job.remove()
            del active_timers[user_id]
        
        await query.edit_message_text(
            text="Таймер времени Воронежа выключен. Бот больше не будет присылать время каждую минуту.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ])
        )
    else:
        # Включаем таймер
        user_data['time_timer_active'] = True
        
        # Создаем задачу на отправку времени каждую минуту
        if hasattr(context.application, 'scheduler'):
            job = context.application.scheduler.add_job(
                send_time_update,
                'cron',
                minute='*',
                args=[user_id, context.application],
                id=f'time_timer_{user_id}',
                replace_existing=True
            )
            active_timers[user_id] = job
            
            # Отправляем первое сообщение сразу
            current_time = datetime.now(VORONEZH_TZ).strftime("%H:%M:%S")
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🕒 Таймер времени Воронежа включен! Сейчас в Воронеже: {current_time}"
            )
            
            await query.edit_message_text(
                text="Таймер времени Воронежа включен! Бот будет присылать время каждую минуту.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔕 Выключить таймер", callback_data='toggle_timer')],
                    [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
                ])
            )
        else:
            await query.edit_message_text(
                text="Ошибка: планировщик не инициализирован.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
                ])
            )
    
    return MAIN_MENU

# Функция отправки времени
async def send_time_update(user_id: int, app):
    try:
        if user_id in user_data_store and user_data_store[user_id]['time_timer_active']:
            current_time = datetime.now(VORONEZH_TZ).strftime("%H:%M:%S")
            await app.bot.send_message(
                chat_id=user_id,
                text=f"🕒 Сейчас в Воронеже: {current_time}"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки времени пользователю {user_id}: {e}")
        # Если пользователь заблокировал бота, удаляем таймер
        if user_id in active_timers:
            active_timers[user_id].remove()
            del active_timers[user_id]
        if user_id in user_data_store:
            user_data_store[user_id]['time_timer_active'] = False

# Установка напоминания - шаг 1
async def set_reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📝 Напишите текст сообщения, которое вы хотите получить:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ])
    )
    
    return SET_REMINDER_TEXT

# Установка напоминания - шаг 2
async def set_reminder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminder_text = update.message.text
    
    # Сохраняем текст в контексте
    context.user_data['reminder_text'] = reminder_text
    
    await update.message.reply_text(
        text=f"📝 Текст сохранен: \"{reminder_text}\"\n\n"
             f"🕒 Теперь введите время в формате ЧЧ:ММ (например, 14:30):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ])
    )
    
    return SET_REMINDER_TIME

# Установка напоминания - шаг 3
async def set_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    time_str = update.message.text
    
    try:
        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        
        # Создаем объект времени
        reminder_time = dt_time(hour, minute)
        
        # Создаем уникальный ID для напоминания
        reminder_id = f"reminder_{user_id}_{int(datetime.now().timestamp())}"
        
        # Сохраняем напоминание
        reminder_data = {
            'id': reminder_id,
            'text': context.user_data.get('reminder_text', ''),
            'time': reminder_time,
            'active': True
        }
        
        if user_id not in user_data_store:
            user_data_store[user_id] = {'reminders': [], 'time_timer_active': False}
        
        user_data_store[user_id]['reminders'].append(reminder_data)
        
        # Создаем задачу в планировщике
        if hasattr(context.application, 'scheduler'):
            trigger = CronTrigger(hour=hour, minute=minute, timezone=VORONEZH_TZ)
            job = context.application.scheduler.add_job(
                send_reminder,
                trigger,
                args=[user_id, context.user_data.get('reminder_text', ''), reminder_id, context.application],
                id=reminder_id,
                replace_existing=True
            )
            
            active_reminders[reminder_id] = job
            
            await update.message.reply_text(
                text=f"✅ Напоминание установлено!\n\n"
                     f"📝 Текст: \"{context.user_data.get('reminder_text', '')}\"\n"
                     f"🕒 Время: {time_str}\n\n"
                     f"Бот отправит вам это сообщение в указанное время.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚫 Отключить это сообщение", callback_data=f'disable_{reminder_id}')],
                    [InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_main')]
                ])
            )
        else:
            await update.message.reply_text(
                text="Ошибка: планировщик не инициализирован.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
                ])
            )
            
    except (ValueError, IndexError):
        await update.message.reply_text(
            text="❌ Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
            ])
        )
        return SET_REMINDER_TIME
    
    # Очищаем временные данные
    if 'reminder_text' in context.user_data:
        del context.user_data['reminder_text']
    
    return MAIN_MENU

# Отправка напоминания
async def send_reminder(user_id: int, text: str, reminder_id: str, app):
    try:
        await app.bot.send_message(
            chat_id=user_id,
            text=f"🔔 Напоминание:\n\n{text}"
        )
        
        # Удаляем задачу после отправки
        if reminder_id in active_reminders:
            del active_reminders[reminder_id]
        
        # Удаляем из списка пользователя
        if user_id in user_data_store:
            user_data_store[user_id]['reminders'] = [
                r for r in user_data_store[user_id]['reminders'] 
                if r['id'] != reminder_id
            ]
            
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания {reminder_id}: {e}")
        if reminder_id in active_reminders:
            del active_reminders[reminder_id]

# Отключение напоминания
async def disable_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reminder_id = query.data.replace('disable_', '')
    user_id = query.from_user.id
    
    # Удаляем задачу из планировщика
    if reminder_id in active_reminders:
        active_reminders[reminder_id].remove()
        del active_reminders[reminder_id]
    
    # Удаляем из списка пользователя
    if user_id in user_data_store:
        user_data_store[user_id]['reminders'] = [
            r for r in user_data_store[user_id]['reminders'] 
            if r['id'] != reminder_id
        ]
    
    await query.edit_message_text(
        text="✅ Напоминание отключено и не будет отправлено.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_main')]
        ])
    )
    
    return MAIN_MENU

# Обработка неизвестных команд
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Извините, я не понял эту команду. Используйте /start для начала работы."
    )

# Основная функция
async def main():
    # Создаем Application
    application = Application.builder().token("8517372931:AAG66lYcPsP_6bwQA4QVaMa-A_YYYWWBmQQ").build()
    
    # Инициализируем планировщик
    await start_scheduler(application)
    
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
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Запуск бота
    print("Бот запущен...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Запускаем бесконечный цикл
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        await application.stop()
        if hasattr(application, 'scheduler'):
            application.scheduler.shutdown()

if __name__ == '__main__':
    # Запускаем асинхронную функцию
    asyncio.run(main())
