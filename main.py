import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
from flask import Flask
import threading
import time
import requests

# ==================== KEEP ALIVE SYSTEM ====================
from flask import Flask as KeepAliveApp
from threading import Thread as KeepAliveThread
import time as keep_alive_time

# Keep-alive сервер
keep_alive_flask = KeepAliveApp('keep_alive')

@keep_alive_flask.route('/')
def keep_alive_home():
    return "🟢 CAPT BOT is running 24/7! 🚀"

@keep_alive_flask.route('/health')
def health_check():
    return "✅ OK", 200

@keep_alive_flask.route('/ping')
def ping():
    return "🏓 PONG", 200

def run_keep_alive_server():
    keep_alive_flask.run(host='0.0.0.0', port=8080)

# Функция авто-пинга
def auto_ping_self():
    while True:
        try:
            # Получаем URL Replit автоматически
            repl_slug = os.environ.get('REPL_SLUG', 'tg-capt')
            repl_owner = os.environ.get('REPL_OWNER', 'chikenxa')
            url = f"https://{repl_slug}.{repl_owner}.repl.co"
            response = requests.get(url, timeout=10)
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"🟢 Keep-alive ping: {current_time} - Status: {response.status_code}")
        except Exception as e:
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"⚠️  Keep-alive failed: {e} at {current_time}")
        keep_alive_time.sleep(240)  # 4 минуты

# Запускаем keep-alive системы
KeepAliveThread(target=run_keep_alive_server, daemon=True).start()
KeepAliveThread(target=auto_ping_self, daemon=True).start()

print("🔧 Keep-alive system started!")
# ==================== END KEEP ALIVE SYSTEM ====================

# Основной Flask app (оставляем для обратной совместимости)
app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 CAPT BOT is running!"

@app.route('/status')
def status():
    return {
        "status": "online",
        "bot": "CAPT BOT",
        "timestamp": datetime.now().isoformat(),
        "events_count": len(events),
        "active_chats": len(set(chat_id for chat_id, _ in event_messages.values()))
    }

def run_web():
    app.run(host='0.0.0.0', port=5000)

# Запускаем основной Flask в отдельном потоке
threading.Thread(target=run_web, daemon=True).start()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

events = {}
admins = {}  # {user_id: {'username': '', 'first_name': ''}}
root_users = {}  # {user_id: {'username': '', 'first_name': ''}}
ADMIN_PASSWORD = "24680"
ROOT_PASSWORD = "1508"

waiting_for_password = {}
event_messages = {}  # {event_code: (chat_id, message_id)}
bot_messages = []  # [(chat_id, message_id, timestamp)] - для отслеживания сообщений бота
daily_status_sent = {}  # {chat_id: date} - для отслеживания отправки ежедневного статуса

# Московское время постоянно UTC+3 (без летнего времени)
MOSCOW_UTC_OFFSET = 3

def get_moscow_time():
    """Получаем точное московское время (UTC+3)"""
    return datetime.utcnow() + timedelta(hours=MOSCOW_UTC_OFFSET)

def debug_time():
    """Функция для отладки времени"""
    current_utc = datetime.utcnow()
    current_moscow = get_moscow_time()
    
    logger.info(f"🕐 ВРЕМЯ ДЛЯ ОТЛАДКИ:")
    logger.info(f"UTC: {current_utc.strftime('%d.%m.%Y %H:%M:%S')}")
    logger.info(f"МСК: {current_moscow.strftime('%d.%m.%Y %H:%M:%S')}")
    logger.info(f"Час МСК: {current_moscow.hour}, Минута МСК: {current_moscow.minute}")

def is_admin(user_id):
    return user_id in admins

def is_root(user_id):
    return user_id in root_users

async def update_event_message(application, event_code):
    """Обновляем сообщение с участниками капта"""
    if event_code not in events or event_code not in event_messages:
        return
    
    try:
        event = events[event_code]
        chat_id, message_id = event_messages[event_code]
        
        free_slots = int(event['slots']) - len(event['participants'])
        
        # Формируем список участников с @упоминаниями
        participants_list = ""
        if event['participants']:
            participants_list = "\n👥 *Участники:*\n"
            for i, participant in enumerate(event['participants'], 1):
                # Используем @username если есть, иначе display_name
                if participant.get('username'):
                    participants_list += f"{i}. @{participant['username']}\n"
                else:
                    participants_list += f"{i}. {participant['display_name']}\n"
        else:
            participants_list = "\n👥 *Участники:* пока нет\n"
        
        event_text = (
            f"🎯 *КАПТ ОБНОВЛЕН!*\n\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"📝 **Название:** {event['name']}\n"
            f"🎫 **Слоты:** {event['slots']}\n"
            f"📅 **Дата:** {event['date']}\n"
            f"⏰ **Время:** {event['time']} МСК\n"
            f"⚔️ **Оружие:** {event['weapon_type']}\n"
            f"❤️ **Хил:** {event['heal']}\n"
            f"🛡️ **Роль:** {event['role']}\n"
            f"👤 **Создатель:** {event['author']}\n"
            f"👥 **Записано:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов"
            f"{participants_list}\n"
            f"⚡ **Записаться:** `/go {event_code}`\n"
            f"❌ **Выйти:** `/ex {event_code}`"
        )
        
        await application.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=event_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения капта: {e}")

async def pin_event_message(application, chat_id, message_id):
    """Закрепляем сообщение с каптом"""
    try:
        await application.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True
        )
        logger.info(f"Сообщение {message_id} закреплено в чате {chat_id}")
    except Exception as e:
        logger.warning(f"Не удалось закрепить сообщение: {e}")

async def send_event_reminders(application):
    """Отправляем напоминания за 30 минут до капта"""
    try:
        current_time = get_moscow_time()
        logger.info(f"🔔 Проверка напоминаний: {current_time.strftime('%d.%m.%Y %H:%M:%S')} МСК")
        
        for event_code, event in events.items():
            try:
                # Парсим дату и время капта
                event_date_str = event['date']
                event_time_str = event['time']
                
                # Предполагаем текущий год
                current_year = current_time.year
                event_datetime_str = f"{event_date_str}.{current_year} {event_time_str}"
                
                try:
                    event_datetime = datetime.strptime(event_datetime_str, "%d.%m.%Y %H:%M")
                    # Конвертируем в московское время (предполагаем, что время ввода было МСК)
                    event_datetime = event_datetime  # Уже в правильном формате
                except ValueError:
                    logger.error(f"❌ Ошибка парсинга даты: {event_datetime_str}")
                    continue
                
                # Разница во времени
                time_diff = event_datetime - current_time
                time_diff_minutes = time_diff.total_seconds() / 60
                
                logger.info(f"📊 Капт {event_code}: {time_diff_minutes:.1f} минут до начала")
                
                # Если до капта 30 минут или меньше
                if 0 <= time_diff_minutes <= 30:
                    if not event.get('reminder_sent', False):
                        # Отправляем упоминания всем участникам через @username
                        participants = event['participants']
                        if participants:
                            mentions = []
                            for participant in participants:
                                if participant.get('username'):
                                    mentions.append(f"@{participant['username']}")
                                else:
                                    mentions.append(participant['first_name'])
                            
                            if mentions:
                                reminder_text = (
                                    f"🔔 *НАПОМИНАНИЕ О КАПТЕ!*\n\n"
                                    f"🎯 **{event['name']}**\n"
                                    f"⏰ **Через 30 минут!** ({event['time']} МСК)\n"
                                    f"👥 Участники: {', '.join(mentions)}\n\n"
                                    f"⚡ Удачи в игре! 🎮"
                                )
                                
                                # Отправляем в чат где создан капт
                                if event_code in event_messages:
                                    chat_id, _ = event_messages[event_code]
                                    message = await application.bot.send_message(
                                        chat_id=chat_id,
                                        text=reminder_text,
                                        parse_mode='Markdown'
                                    )
                                    # Сохраняем ID сообщения для последующего удаления
                                    bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                                    
                                    logger.info(f"✅ Напоминание отправлено для капта {event_code}")
                            
                            event['reminder_sent'] = True
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки напоминания для капта {event_code}: {e}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка в функции напоминаний: {e}")

async def send_daily_kapt_status(application):
    """Отправляем статус каптов один раз в день в 14:00 по МСК и закрепляем"""
    try:
        current_time = get_moscow_time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_date = current_time.strftime("%Y-%m-%d")
        
        logger.info(f"🕐 Проверка ежедневного статуса: {current_hour:02d}:{current_minute:02d} МСК")
        
        # Проверяем время: только в 14:00 по МСК
        if current_hour == 14 and current_minute == 0:
            logger.info("✅ Отправка ежедневного статуса каптов в 14:00 МСК")
            
            # Получаем список всех уникальных чатов где есть капты
            unique_chats = set()
            for chat_id, _ in event_messages.values():
                unique_chats.add(chat_id)
            
            for chat_id in unique_chats:
                try:
                    # Проверяем, не отправляли ли уже сегодня статус в этот чат
                    if daily_status_sent.get(chat_id) == current_date:
                        logger.info(f"⏭️ Статус уже отправлен сегодня в чат {chat_id}")
                        continue
                    
                    # Используем функцию kapt_command для формирования текста
                    status_text = await generate_kapt_text()
                    
                    if status_text:
                        message = await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"🕐 *ЕЖЕДНЕВНЫЙ СТАТУС КАПТОВ* 🕐\n\n{status_text}",
                            parse_mode='Markdown'
                        )
                        # ЗАКРЕПЛЯЕМ сообщение со статусом
                        await pin_event_message(application, chat_id, message.message_id)
                        
                        # Сохраняем ID сообщения для последующего удаления
                        bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                        
                        # Отмечаем, что статус отправлен сегодня
                        daily_status_sent[chat_id] = current_date
                        
                        logger.info(f"✅ Ежедневный статус отправлен и закреплен в чат {chat_id}")
                    else:
                        message = await application.bot.send_message(
                            chat_id=chat_id,
                            text="🕐 *ЕЖЕДНЕВНЫЙ СТАТУС КАПТОВ* 🕐\n\n📭 *Активных каптов нет*",
                            parse_mode='Markdown'
                        )
                        bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                        daily_status_sent[chat_id] = current_date
                        logger.info(f"✅ Статус 'нет каптов' отправлен в чат {chat_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки ежедневного статуса в чат {chat_id}: {e}")
        else:
            logger.info(f"⏰ Не время для ежедневного статуса: {current_hour:02d}:{current_minute:02d} МСК")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ежедневного статуса: {e}")

async def generate_kapt_text():
    """Генерирует текст для команды /kapt"""
    try:
        if not events:
            return None
        
        text = ""
        
        for code, event in events.items():
            free_slots = int(event['slots']) - len(event['participants'])
            
            participants_list = ""
            if event['participants']:
                participants_list = "\n👥 *Участники:*\n"
                for i, participant in enumerate(event['participants'], 1):
                    if participant.get('username'):
                        participants_list += f"{i}. @{participant['username']}\n"
                    else:
                        participants_list += f"{i}. {participant['display_name']}\n"
            else:
                participants_list = "\n👥 *Участники:* пока нет\n"
            
            text += (
                f"🔢 **Код:** `{code}`\n"
                f"🎯 **{event['name']}**\n"
                f"📅 **Когда:** {event['date']} {event['time']} МСК\n"
                f"👥 **Записано:** {len(event['participants'])}/{event['slots']}\n"
                f"🎫 **Свободно:** {free_slots} слотов\n"
                f"⚔️ **Оружие:** {event['weapon_type']}\n"
                f"❤️ **Хил:** {event['heal']}\n"
                f"🛡️ **Роль:** {event['role']}"
                f"{participants_list}\n"
                f"⚡ `/go {code}`  •  ❌ `/ex {code}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
        
        return text
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации текста каптов: {e}")
        return None

async def send_good_night(application):
    """Отправляем спокойной ночи в 23:59"""
    try:
        current_time = get_moscow_time()
        logger.info(f"🌙 Проверка спокойной ночи: {current_time.strftime('%H:%M')} МСК")
        
        if current_time.hour == 23 and current_time.minute == 59:
            logger.info("✅ Отправка спокойной ночи")
            
            # Получаем список всех уникальных чатов где есть капты
            unique_chats = set()
            for chat_id, _ in event_messages.values():
                unique_chats.add(chat_id)
            
            for chat_id in unique_chats:
                try:
                    message = await application.bot.send_message(
                        chat_id=chat_id,
                        text="🌙 *СИСТЕМА ПЕРЕХОДИТ В НОЧНОЙ РЕЖИМ* 🌙\n\n"
                             "💤 *Спокойной ночи! Всем хорошо выспаться!*\n"
                             "🖥️ *Сервера работают в фоновом режиме...*\n\n"
                             f"👨‍💻 _Разработано ChikenXa (Данил)_",
                        parse_mode='Markdown'
                    )
                    # Сохраняем ID сообщения для последующего удаления
                    bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                    logger.info(f"✅ Спокойной ночи отправлено в чат {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки спокойной ночи в чат {chat_id}: {e}")
        else:
            logger.info(f"⏰ Не время для спокойной ночи: {current_time.strftime('%H:%M')} МСК")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки спокойной ночи: {e}")

async def cleanup_old_messages(application):
    """Удаляем старые сообщения бота в 6:00 утра с красивым выводом"""
    try:
        current_time = get_moscow_time()
        logger.info(f"🧹 Проверка очистки: {current_time.strftime('%H:%M')} МСК")
        
        if current_time.hour == 6 and current_time.minute == 0:
            logger.info("✅ Начало красивой очистки старых сообщений...")
            
            # Получаем список всех уникальных чатов
            unique_chats = set()
            for chat_id, _ in event_messages.values():
                unique_chats.add(chat_id)
            
            for chat_id in unique_chats:
                try:
                    # Отправляем начальное сообщение об очистке
                    status_message = await application.bot.send_message(
                        chat_id=chat_id,
                        text="🖥️ *ЗАПУСК СИСТЕМЫ ОЧИСТКИ* 🖥️\n\n"
                             "🔍 Сканирование базы данных...",
                        parse_mode='Markdown'
                    )
                    
                    # Ждем немного для эффекта
                    await asyncio.sleep(2)
                    
                    # Обновляем сообщение
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text="🖥️ *ЗАПУСК СИСТЕМЫ ОЧИСТКИ* 🖥️\n\n"
                             "✅ База данных просканирована\n"
                             "🔍 Поиск устаревших сообщений...",
                        parse_mode='Markdown'
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Считаем сообщения для удаления
                    messages_to_delete = []
                    current_timestamp = current_time.timestamp()
                    
                    for msg_chat_id, message_id, timestamp in bot_messages[:]:
                        if msg_chat_id == chat_id and current_timestamp - timestamp > 3600:
                            messages_to_delete.append((message_id, timestamp))
                    
                    # Обновляем с количеством найденных сообщений
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text="🖥️ *ЗАПУСК СИСТЕМЫ ОЧИСТКИ* 🖥️\n\n"
                             "✅ База данных просканирована\n"
                             "✅ Найдено устаревших сообщений\n"
                             f"📊 Обнаружено: {len(messages_to_delete)} сообщений\n"
                             "🗑️ Начинаю очистку...",
                        parse_mode='Markdown'
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Процесс удаления
                    deleted_count = 0
                    for message_id, timestamp in messages_to_delete:
                        try:
                            await application.bot.delete_message(chat_id, message_id)
                            deleted_count += 1
                            
                            # Обновляем прогресс каждые 5 сообщений
                            if deleted_count % 5 == 0:
                                await application.bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=status_message.message_id,
                                    text="🖥️ *ЗАПУСК СИСТЕМЫ ОЧИСТКИ* 🖥️\n\n"
                                         "✅ База данных просканирована\n"
                                         "✅ Найдено устаревших сообщений\n"
                                         f"📊 Обнаружено: {len(messages_to_delete)} сообщений\n"
                                         f"🗑️ Удалено: {deleted_count}/{len(messages_to_delete)}\n"
                                         f"📈 Прогресс: {deleted_count/len(messages_to_delete)*100:.1f}%",
                                    parse_mode='Markdown'
                                )
                                await asyncio.sleep(0.5)
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось удалить сообщение {message_id}: {e}")
                    
                    # Удаляем обработанные сообщения из списка
                    for message_id, timestamp in messages_to_delete:
                        for msg in bot_messages[:]:
                            if msg[0] == chat_id and msg[1] == message_id:
                                bot_messages.remove(msg)
                                break
                    
                    # Очищаем завершенные капты
                    current_date = current_time.strftime("%d.%m")
                    events_to_remove = []
                    
                    for event_code, event in events.items():
                        event_date = event['date']
                        try:
                            event_day, event_month = event_date.split('.')
                            current_day, current_month = current_date.split('.')
                            
                            if (int(current_month) > int(event_month)) or \
                               (int(current_month) == int(event_month) and int(current_day) > int(event_day)):
                                events_to_remove.append(event_code)
                        except:
                            pass
                    
                    # Обновляем перед удалением каптов
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text="🖥️ *ЗАПУСК СИСТЕМЫ ОЧИСТКИ* 🖥️\n\n"
                             "✅ База данных просканирована\n"
                             "✅ Найдено устаревших сообщений\n"
                             f"✅ Удалено сообщений: {deleted_count}\n"
                             f"🔍 Найдено каптов для очистки: {len(events_to_remove)}\n"
                             "🗑️ Очищаю архив каптов...",
                        parse_mode='Markdown'
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Удаляем капты
                    for event_code in events_to_remove:
                        if event_code in event_messages:
                            try:
                                event_chat_id, event_message_id = event_messages[event_code]
                                if event_chat_id == chat_id:
                                    await application.bot.delete_message(chat_id, event_message_id)
                                    await application.bot.unpin_chat_message(chat_id, event_message_id)
                            except:
                                pass
                            del event_messages[event_code]
                        del events[event_code]
                    
                    # Финальное сообщение
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text="🖥️ *СИСТЕМА ОЧИСТКИ ЗАВЕРШИЛА РАБОТУ* 🖥️\n\n"
                             "📊 *ОТЧЕТ О ВЫПОЛНЕНИИ:*\n"
                             f"✅ Удалено сообщений: `{deleted_count}`\n"
                             f"✅ Очищено каптов: `{len(events_to_remove)}`\n"
                             f"✅ Активных каптов: `{len(events)}`\n"
                             f"📝 Сообщений в памяти: `{len(bot_messages)}`\n\n"
                             "🎯 *СИСТЕМА ГОТОВА К РАБОТЕ* 🎯\n\n"
                             f"👨‍💻 _Разработано ChikenXa (Данил)_",
                        parse_mode='Markdown'
                    )
                    
                    # Сохраняем финальное сообщение для следующей очистки
                    bot_messages.append((status_message.chat_id, status_message.message_id, current_time.timestamp()))
                    
                    logger.info(f"✅ Красивая очистка завершена в чате {chat_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка красивой очистки в чате {chat_id}: {e}")
            
            logger.info("✅ Красивая очистка сообщений завершена во всех чатах")
        else:
            logger.info(f"⏰ Не время для очистки: {current_time.strftime('%H:%M')} МСК")
            
    except Exception as e:
        logger.error(f"❌ Ошибка красивой очистки сообщений: {e}")

async def scheduled_tasks(application):
    """Планировщик задач"""
    while True:
        try:
            # Выводим отладочную информацию о времени
            debug_time()
            
            await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
            # Напоминания о каптах
            await send_event_reminders(application)
            
            # Ежедневный статус каптов в 14:00
            await send_daily_kapt_status(application)
            
            # Спокойной ночи
            await send_good_night(application)
            
            # Очистка сообщений
            await cleanup_old_messages(application)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в планировщике: {e}")
            await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = await update.message.reply_text(
        f"👋 *Привет, {user.first_name}!*\n\n"
        f"🎮 *CAPT BOT* - твой помощник для организации каптов\n\n"
        f"📱 *Основные команды:*\n"
        f"• `/commands` - все команды\n"
        f"• `/ping` - проверить работу бота\n"
        f"• `/create` - создать капт\n"
        f"• `/kapt` - список каптов\n"
        f"• `/go [код]` - записаться\n"
        f"• `/ex [код]` - выйти\n\n"
        f"⚡ *Быстрый старт:*\n"
        f"`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`\n"
        f"`/go 1` - записаться\n\n"
        f"🕐 *Авто-статус:* каждый день в 14:00 по МСК\n\n"
        f"👨‍💻 _Разработано ChikenXa (Данил)_",
        parse_mode='Markdown'
    )
    # Сохраняем ID сообщения
    bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка работы бота"""
    try:
        start_time = time.time()
        message = await update.message.reply_text("🏓 *Понг!*", parse_mode='Markdown')
        end_time = time.time()
        
        ping_time = round((end_time - start_time) * 1000, 2)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            text=f"🏓 *Понг!*\n⏱️ *Время ответа:* `{ping_time}ms`\n👨‍💻 _Разработано ChikenXa (Данил)_",
            parse_mode='Markdown'
        )
        
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        logger.info(f"✅ Ping command executed: {ping_time}ms")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в команде ping: {e}")
        message = await update.message.reply_text("❌ *Ошибка выполнения команды!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin_user = is_admin(user.id)
    is_root_user = is_root(user.id)
    
    text = "📋 *СПИСОК КОМАНД*\n\n"
    text += "👥 *Для всех:*\n"
    text += "• `/start` - начать работу\n"
    text += "• `/commands` - этот список\n"
    text += "• `/ping` - проверить работу бота\n"
    text += "• `/kapt` - активные капты\n"
    text += "• `/go [код]` - записаться\n"
    text += "• `/ex [код]` - выйти\n\n"
    text += "🎯 *Создание капта:*\n"
    text += "• `/create код название слоты дата время оружие хил роль`\n"
    text += "_Пример: /create 1 Рейд 5 20.11 21:30 Лук Да Защита_\n\n"
    
    text += "🕐 *Автоматические функции:*\n"
    text += "• Напоминания за 30 минут до капта\n"
    text += "• Статус каптов каждый день в 14:00 МСК\n"
    text += "• Спокойной ночи в 23:59\n"
    text += "• Очистка в 6:00\n\n"
    
    if is_admin_user or is_root_user:
        text += "🛠️ *Админ команды:*\n"
        text += "• `/alogin` - войти как админ\n"
        text += "• `/kick @username код` - кикнуть игрока\n"
        text += "• `/del код` - удалить капт\n\n"
    
    if is_root_user:
        text += "👑 *Root команды:*\n"
        text += "• `/root` - войти как root\n"
        text += "• `/addadmin @username` - добавить админа\n"
        text += "• `/removeadmin @username` - удалить админа\n"
        text += "• `/listadmins` - список админов\n\n"
    
    text += "👨‍💻 _Разработано ChikenXa (Данил)_"
    
    message = await update.message.reply_text(text, parse_mode='Markdown')
    bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        await update.message.delete()
    except:
        pass
    
    waiting_for_password[user.id] = 'admin'
    message = await context.bot.send_message(
        chat_id=user.id,
        text="🔐 *Введите пароль админа:*",
        parse_mode='Markdown'
    )
    bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def root_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        await update.message.delete()
    except:
        pass
    
    waiting_for_password[user.id] = 'root'
    message = await context.bot.send_message(
        chat_id=user.id,
        text="👑 *Введите root пароль:*",
        parse_mode='Markdown'
    )
    bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    password = update.message.text
    
    if user.id not in waiting_for_password:
        return
    
    auth_type = waiting_for_password[user.id]
    
    try:
        await update.message.delete()
    except:
        pass
    
    if auth_type == 'admin':
        if password == ADMIN_PASSWORD:
            admins[user.id] = {
                'username': user.username,
                'first_name': user.first_name
            }
            message = await update.message.reply_text(
                f"✅ *Добро пожаловать в админ-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
        else:
            message = await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
    
    elif auth_type == 'root':
        if password == ROOT_PASSWORD:
            root_users[user.id] = {
                'username': user.username,
                'first_name': user.first_name
            }
            admins[user.id] = {
                'username': user.username,
                'first_name': user.first_name
            }
            message = await update.message.reply_text(
                f"👑 *Добро пожаловать в root-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
        else:
            message = await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
    
    bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
    del waiting_for_password[user.id]

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление админа по @username"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            message = await update.message.reply_text("❌ *Только root может добавлять админов!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
            
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи @username*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        target = context.args[0]
        
        if not target.startswith('@'):
            message = await update.message.reply_text("❌ *Укажи @username (начинается с @)*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        username = target[1:]  # Убираем @
        
        # Ищем пользователя по username среди тех, кто писал боту
        target_user_id = None
        target_user_info = None
        
        # Проверяем в событиях
        for event in events.values():
            for participant in event['participants']:
                if participant.get('username') == username:
                    target_user_id = participant['user_id']
                    target_user_info = participant
                    break
            if target_user_id:
                break
        
        if not target_user_id:
            message = await update.message.reply_text(
                f"❌ *Пользователь @{username} не найден!*\n\n"
                f"*Чтобы добавить админа:*\n"
                f"1. Попроси человека написать боту любое сообщение\n"
                f"2. Затем используй команду: `/addadmin @{username}`",
                parse_mode='Markdown'
            )
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        if target_user_id in root_users:
            message = await update.message.reply_text("❌ *Нельзя добавить root пользователя как админа!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        if target_user_id in admins:
            message = await update.message.reply_text(f"⚠️ *Пользователь @{username} уже является админом!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        admins[target_user_id] = {
            'username': username,
            'first_name': target_user_info.get('first_name', 'Unknown')
        }
        
        message = await update.message.reply_text(
            f"✅ *Пользователь @{username} добавлен в админы!*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        logger.error(f"Ошибка добавления админа: {e}")
        message = await update.message.reply_text("❌ *Ошибка добавления админа!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление админа по @username"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            message = await update.message.reply_text("❌ *Только root может удалять админов!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
            
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи @username*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        target = context.args[0]
        
        if not target.startswith('@'):
            message = await update.message.reply_text("❌ *Укажи @username (начинается с @)*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        username = target[1:]
        
        # Ищем админа по username
        target_user_id = None
        for admin_id, admin_info in admins.items():
            if admin_info.get('username') == username:
                target_user_id = admin_id
                break
        
        if not target_user_id:
            message = await update.message.reply_text(f"❌ *Пользователь @{username} не является админом!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        if target_user_id in root_users:
            message = await update.message.reply_text("❌ *Нельзя удалить root пользователя!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        del admins[target_user_id]
        
        message = await update.message.reply_text(
            f"🗑️ *Пользователь @{username} удален из админов!*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        logger.error(f"Ошибка удаления админа: {e}")
        message = await update.message.reply_text("❌ *Ошибка удаления админа!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def get_admins_list():
    if not admins:
        return "📭 Админов нет"
    
    text = ""
    for i, (admin_id, admin_info) in enumerate(admins.items(), 1):
        is_root_user = "👑 " if admin_id in root_users else ""
        username = admin_info.get('username', 'без username')
        first_name = admin_info.get('first_name', 'Unknown')
        
        if username:
            text += f"{i}. {is_root_user}@{username} ({first_name})\n"
        else:
            text += f"{i}. {is_root_user}{first_name} (без username)\n"
    
    return text

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            message = await update.message.reply_text("❌ *Только root может просматривать список админов!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        text = "👥 *СПИСОК АДМИНОВ*\n\n"
        text += await get_admins_list()
        text += f"\n👑 *Root пользователей:* {len(root_users)}"
        text += f"\n🛠️ *Всего админов:* {len(admins)}"
        text += f"\n\n👨‍💻 _Разработано ChikenXa (Данил)_"
        
        message = await update.message.reply_text(text, parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        logger.error(f"Ошибка списка админов: {e}")
        message = await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 8:
            message = await update.message.reply_text(
                "🎯 *Создание капта*\n\n"
                "📋 *Формат:*\n"
                "`/create код название слоты дата время оружие хил роль`\n\n"
                "📝 *Пример:*\n"
                "`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`",
                parse_mode='Markdown'
            )
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event_code = context.args[0]
        name = context.args[1]
        slots = context.args[2]
        date = context.args[3]
        time = context.args[4]
        weapon_type = context.args[5]
        heal = context.args[6]
        role = context.args[7]
        
        user = update.effective_user
        
        if event_code in events:
            message = await update.message.reply_text(f"⚠️ *Капт {event_code} уже существует!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        events[event_code] = {
            'name': name,
            'slots': slots,
            'date': date,
            'time': time,
            'weapon_type': weapon_type,
            'heal': heal,
            'role': role,
            'participants': [],
            'author': user.first_name,
            'author_id': user.id,
            'reminder_sent': False
        }
        
        free_slots = int(slots)
        
        participants_list = "\n👥 *Участники:* пока нет\n"
        
        event_text = (
            f"🎯 *НОВЫЙ КАПТ СОЗДАН!*\n\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"📝 **Название:** {name}\n"
            f"🎫 **Слоты:** {slots}\n"
            f"📅 **Дата:** {date}\n"
            f"⏰ **Время:** {time} МСК\n"
            f"⚔️ **Оружие:** {weapon_type}\n"
            f"❤️ **Хил:** {heal}\n"
            f"🛡️ **Роль:** {role}\n"
            f"👤 **Создатель:** {user.first_name}\n"
            f"👥 **Записано:** 0/{slots}\n"
            f"🎫 **Свободно:** {free_slots} слотов"
            f"{participants_list}\n"
            f"⚡ **Записаться:** `/go {event_code}`\n"
            f"❌ **Выйти:** `/ex {event_code}`"
        )
        
        message = await update.message.reply_text(event_text, parse_mode='Markdown')
        
        # Сохраняем ID сообщения для обновления и закрепляем
        event_messages[event_code] = (message.chat_id, message.message_id)
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
        # Закрепляем сообщение
        await pin_event_message(context.application, message.chat_id, message.message_id)
        
    except Exception as e:
        logger.error(f"Ошибка создания капта: {e}")
        message = await update.message.reply_text("❌ *Ошибка создания капта!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event = events[event_code]
        
        if len(event['participants']) >= int(event['slots']):
            message = await update.message.reply_text("🚫 *Нет свободных слотов!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        user_already_registered = any(participant['user_id'] == user.id for participant in event['participants'])
        if user_already_registered:
            message = await update.message.reply_text("⚠️ *Ты уже в капте!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        # Всегда используем @username если он есть
        if user.username:
            display_name = f"@{user.username}"
        else:
            display_name = user.first_name
        
        participant_data = {
            'user_id': user.id,
            'username': user.username,  # Сохраняем username
            'display_name': display_name,
            'first_name': user.first_name
        }
        event['participants'].append(participant_data)
        
        await update_event_message(context.application, event_code)
        
        message = await update.message.reply_text(
            f"✅ *{display_name} записан в капт!*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка записи!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def ex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event = events[event_code]
        
        participant_index = None
        for i, participant in enumerate(event['participants']):
            if participant['user_id'] == user.id:
                participant_index = i
                break
        
        if participant_index is None:
            message = await update.message.reply_text("⚠️ *Ты не в этом капте!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        removed_participant = event['participants'].pop(participant_index)
        
        # Обновляем сообщение с участниками
        await update_event_message(context.application, event_code)
        
        message = await update.message.reply_text(
            f"❌ *{removed_participant['display_name']} вышел из капта*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка выхода!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def kapt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not events:
            message = await update.message.reply_text("📭 *Активных каптов нет*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        text = "🎯 *АКТИВНЫЕ КАПТЫ*\n\n"
        
        for code, event in events.items():
            free_slots = int(event['slots']) - len(event['participants'])
            
            participants_list = ""
            if event['participants']:
                participants_list = "\n👥 *Участники:*\n"
                for i, participant in enumerate(event['participants'], 1):
                    if participant.get('username'):
                        participants_list += f"{i}. @{participant['username']}\n"
                    else:
                        participants_list += f"{i}. {participant['display_name']}\n"
            else:
                participants_list = "\n👥 *Участники:* пока нет\n"
            
            text += (
                f"🔢 **Код:** `{code}`\n"
                f"🎯 **{event['name']}**\n"
                f"📅 **Когда:** {event['date']} {event['time']} МСК\n"
                f"👥 **Записано:** {len(event['participants'])}/{event['slots']}\n"
                f"🎫 **Свободно:** {free_slots} слотов\n"
                f"⚔️ **Оружие:** {event['weapon_type']}\n"
                f"❤️ **Хил:** {event['heal']}\n"
                f"🛡️ **Роль:** {event['role']}"
                f"{participants_list}\n"
                f"⚡ `/go {code}`  •  ❌ `/ex {code}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
        
        message = await update.message.reply_text(text, parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        if not is_admin(user.id):
            message = await update.message.reply_text("❌ *Нет прав админа!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
            
        if len(context.args) < 2:
            message = await update.message.reply_text("❌ *Формат:* `/kick @username код`", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        username_input = context.args[0]
        event_code = context.args[1]
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event = events[event_code]
        
        participant_index = None
        removed_participant = None
        
        for i, participant in enumerate(event['participants']):
            clean_input = username_input.replace('@', '').lower()
            participant_username = participant['username'] or ""
            participant_display = participant['display_name'].replace('@', '').lower()
            
            if (participant_username.lower() == clean_input) or (participant_display == clean_input):
                participant_index = i
                removed_participant = participant
                break
        
        if participant_index is None:
            message = await update.message.reply_text(f"❌ *Участник {username_input} не найден в капте {event_code}!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event['participants'].pop(participant_index)
        
        # Обновляем сообщение с участниками
        await update_event_message(context.application, event_code)
        
        message = await update.message.reply_text(
            f"🚫 *Участник {removed_participant['display_name']} исключен из капта!*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка кика!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

async def delete_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        if not is_admin(user.id):
            message = await update.message.reply_text("❌ *Нет прав админа!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
            
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        event_code = context.args[0]
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
            return
        
        # Удаляем сообщение капта если оно есть
        if event_code in event_messages:
            try:
                chat_id, message_id = event_messages[event_code]
                await context.bot.delete_message(chat_id, message_id)
            except:
                pass
            del event_messages[event_code]
        
        # Удаляем капт
        del events[event_code]
        
        message = await update.message.reply_text(
            f"🗑️ *Капт {event_code} удален!*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка удаления!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CommandHandler("alogin", admin_login))
    application.add_handler(CommandHandler("root", root_login))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("listadmins", list_admins))
    application.add_handler(CommandHandler("create", create_event))
    application.add_handler(CommandHandler("go", go_command))
    application.add_handler(CommandHandler("ex", ex_command))
    application.add_handler(CommandHandler("kapt", kapt_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("del", delete_event_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password))
    
    # Запускаем планировщик задач
    application.job_queue.run_once(lambda ctx: asyncio.create_task(scheduled_tasks(application)), when=5)
    
    print("🎮 CAPT BOT запущен!")
    print("🛠️ Создатель: ChikenXa")
    print("🔐 Пароль админа: 24680")
    print("👑 Пароль root: 1508")
    print("💬 Сообщения каптов обновляются автоматически!")
    print("📌 Сообщения каптов закрепляются!")
    print("🔔 Напоминания за 30 минут до капта!")
    print("🕐 Ежедневный статус в 14:00 МСК (с закреплением)!")
    print("🌙 Спокойной ночи в 23:59!")
    print("🧹 Очистка сообщений в 6:00!")
    print("🏓 Команда /ping доступна!")
    print("📋 Команда /commands доступна!")
    print("⏰ Московское время: UTC+3 (постоянно)")
    print("🔧 Keep-alive system: ACTIVE (бот будет работать 24/7)")
    
    application.run_polling()

if __name__ == "__main__":
    main()
