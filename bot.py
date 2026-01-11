import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования для Pydroid 3
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(name)

# Токен бота
TOKEN = "8517372931:AAG66lYcPsP_6bwQA4QVaMa-A_YYYWWBmQQ"

# Временная зона Воронежа
VORONEZH_TZ = pytz.timezone('Europe/Moscow')

# Глобальное хранилище данных
user_data = {}

class UserState:
    MAIN_MENU = "main_menu"
    SET_TIMER_MESSAGE = "set_timer"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Инициализация данных пользователя
    if user_id not in user_data:
        user_data[user_id] = {
            'time_notification': False,
            'scheduled_messages': [],
            'state': UserState.MAIN_MENU
        }
    else:
        user_data[user_id]['state'] = UserState.MAIN_MENU
    
    # Создание клавиатуры
    keyboard = [
        [
            InlineKeyboardButton("⏰ Уведомления о времени", callback_data='time_notif'),
        ],
        [
            InlineKeyboardButton("📝 Запланировать сообщение", callback_data='schedule_msg')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "**Этот Бот предназначен для того чтобы писать каждую минуту какое сейчас время "
        "и чтобы можно было написать что то что ты хочешь чтоб тебе бот прислал в определённое время.**"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if user_id not in user_data:
        user_data[user_id] = {
            'time_notification': False,
            'scheduled_messages': [],
            'state': UserState.MAIN_MENU
        }
    
    if data == 'time_notif':
        # Включить/выключить уведомления о времени
        current_status = user_data[user_id].get('time_notification', False)
        user_data[user_id]['time_notification'] = not current_status
        
        status = "включены" if user_data[user_id]['time_notification'] else "выключены"
        
        # Кнопки для этого состояния
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⏰ Уведомления о времени {status}\n\n"
            f"Бот теперь будет {'присылать' if user_data[user_id]['time_notification'] else 'остановил'} "
            f"сообщения каждую минуту с текущим временем в Воронеже.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data == 'schedule_msg':
        # Переход в режим планирования сообщения
        user_data[user_id]['state'] = UserState.SET_TIMER_MESSAGE
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📝 Режим планирования сообщения\n\n"
            "Пожалуйста, введите сообщение, которое вы хотите получить в определенное время.\n"
        "Формат: \nсообщение | ЧЧ:ММ\n\n"
            "Пример: \nНапомни позвонить маме | 15:30",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data == 'back_to_main':
        # Возврат в главное меню
        user_data[user_id]['state'] = UserState.MAIN_MENU
        
        keyboard = [
            [
                InlineKeyboardButton("⏰ Уведомления о времени", callback_data='time_notif'),
            ],
            [
                InlineKeyboardButton("📝 Запланировать сообщение", callback_data='schedule_msg')
            ]
        ]
        
        # Показ статуса уведомлений
        time_status = "✅ ВКЛ" if user_data[user_id].get('time_notification', False) else "❌ ВЫКЛ"
        
        # Показ запланированных сообщений
        scheduled = user_data[user_id].get('scheduled_messages', [])
        scheduled_count = len(scheduled)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Главное меню\n\n"
            f"⏰ Уведомления о времени: {time_status}\n"
            f"📝 Запланировано сообщений: {scheduled_count}\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data.startswith('cancel_'):
        # Отмена конкретного сообщения
        try:
            msg_index = int(data.split('_')[1])
            scheduled = user_data[user_id].get('scheduled_messages', [])
            if 0 <= msg_index < len(scheduled):
                cancelled_msg = scheduled.pop(msg_index)
                await query.answer(f"Сообщение отменено")
        except:
            pass
        
        # Обновляем список сообщений
        await show_scheduled_messages(update, context)
        
    elif data == 'show_scheduled':
        # Показать запланированные сообщения
        await show_scheduled_messages(update, context)

async def show_scheduled_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список запланированных сообщений"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    scheduled = user_data[user_id].get('scheduled_messages', [])
    
    if not scheduled:
        text = "📭 У вас нет запланированных сообщений."
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]]
    else:
        text = "📋 Ваши запланированные сообщения:\n\n"
        keyboard = []
        
        for i, msg in enumerate(scheduled):
            text += f"{i+1}. {msg.get('text', '')[:30]}... в {msg.get('time', '')}\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Отменить {i+1}", 
                    callback_data=f'cancel_{i}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await start(update, context)
        return
    
    user_state = user_data[user_id].get('state', UserState.MAIN_MENU)
    text = update.message.text
    
    if user_state == UserState.SET_TIMER_MESSAGE:
        # Обработка ввода сообщения для планирования
        if '|' in text:
            try:
                message_text, time_str = [part.strip() for part in text.split('|', 1)]
                
                # Проверка формата времени
                time_obj = datetime.strptime(time_str, '%H:%M').time()
                current_time = datetime.now(VORONEZH_TZ).time()
                
                # Создаем datetime для сегодня с указанным временем
                target_datetime = datetime.now(VORONEZH_TZ).replace(
                    hour=time_obj.hour,
                    minute=time_obj.minute,
                    second=0,
                    microsecond=0
                )
                
                # Если время уже прошло сегодня, планируем на завтра
                if target_datetime.time() < current_time:
                    target_datetime += timedelta(days=1)
                
                # Инициализируем список, если его нет
                if 'scheduled_messages' not in user_data[user_id]:
                    user_data[user_id]['scheduled_messages'] = []
                
                # Сохраняем сообщение
                user_data[user_id]['scheduled_messages'].append({
                    'text': message_text,
                    'time': time_str,
                    'datetime': target_datetime
                })
                
                # Кнопки после сохранения
                keyboard = [
                    [InlineKeyboardButton("📋 Показать запланированные", callback_data='show_scheduled')],
                    [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ Сообщение запланировано!\n\n"
                    f"📝 Текст: {message_text[:50]}...\n"
                    f"⏰ Время: {time_str}\n\n"
                    f"Вы получите это сообщение в указанное время.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                # Возвращаем в главное меню
                user_data[user_id]['state'] = UserState.MAIN_MENU
                
            except ValueError as e:
                await update.message.reply_text(
                    "❌ Ошибка в формате!\n\n"
                    "Пожалуйста, используйте правильный формат:\n"
                    "сообщение | ЧЧ:ММ\n\n"
                    "Пример:\nНапомни позвонить маме | 15:30",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                "❌ Неверный формат!\n\n"
                "Используйте вертикальную черту | для разделения сообщения и времени.\n"
                "Пример: Напомни позвонить маме | 15:30",
                parse_mode='Markdown'
            )
    else:
        # Если не в режиме планирования, отправляем в главное меню
        await start(update, context)

async def send_time_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка уведомлений о времени каждую минуту"""
    current_time = datetime.now(VORONEZH_TZ)
    time_str = current_time.strftime("%H:%M")
    
    # Отправляем только активным пользователям
    for user_id, data in list(user_data.items()):
        if data.get('time_notification', False):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ Текущее время в Воронеже: {time_str}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                # Если ошибка, удаляем пользователя из активных
                if "Chat not found" in str(e) or "Forbidden" in str(e):
                    user_data.pop(user_id, None)
                logger.error(f"Ошибка отправки уведомления: {e}")

async def check_scheduled_messages(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка и отправка запланированных сообщений"""
    current_time = datetime.now(VORONEZH_TZ)
    for user_id, data in list(user_data.items()):
        scheduled_messages = data.get('scheduled_messages', [])
        messages_to_remove = []
        
        for i, msg in enumerate(scheduled_messages):
            msg_time = msg.get('datetime')
            if msg_time and msg_time <= current_time:
                try:
                    # Отправляем сообщение
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 Напоминание!\n\n{msg.get('text', '')}",
                        parse_mode='Markdown'
                    )
                    # Помечаем для удаления
                    messages_to_remove.append(i)
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания: {e}")
                    # Если пользователь заблокировал бота, удаляем его данные
                    if "Chat not found" in str(e) or "Forbidden" in str(e):
                        user_data.pop(user_id, None)
                        break
        
        # Удаляем отправленные сообщения (в обратном порядке)
        for index in sorted(messages_to_remove, reverse=True):
            if index < len(scheduled_messages):
                scheduled_messages.pop(index)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        "📚 Помощь по использованию бота:\n\n"
        "1. Уведомления о времени - бот будет присылать текущее время в Воронеже каждую минуту\n"
        "2. Запланировать сообщение - вы можете запланировать напоминание на определенное время\n\n"
        "Формат для планирования:\n"
        "текст сообщения | ЧЧ:ММ\n\n"
        "Пример:\n"
        "Не забудь купить хлеб | 18:30\n\n"
        "Используйте /start для возврата в главное меню."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error("Exception while handling an update:", exc_info=context.error)

def main() -> None:
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем задачи для уведомлений
    job_queue = application.job_queue
    if job_queue:
        # Отправка времени каждую минуту
        job_queue.run_repeating(send_time_notifications, interval=60, first=5)
        # Проверка запланированных сообщений каждые 30 секунд
        job_queue.run_repeating(check_scheduled_messages, interval=30, first=10)
    
    print("🚀 Бот запускается...")
    print("📱 Откройте Telegram и найдите своего бота")
    print("💬 Отправьте команду /start")
    
    # Запускаем бота
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if name == 'main':
    # Для Pydroid 3 используем asyncio.run()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        logger.error(f"Ошибка при запуске: {e}")
