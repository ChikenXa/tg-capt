import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
from flask import Flask
import threading
import time

# Веб-сервер для поддержания активности
app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 CAPT BOT is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web, daemon=True).start()

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

async def send_hourly_kapt_status(application):
    """Каждый час с 14:00 до 23:00 отправляем статус каптов"""
    try:
        current_time = get_moscow_time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Выводим отладочную информацию
        logger.info(f"🕐 Проверка ежечасного статуса: {current_hour:02d}:{current_minute:02d} МСК")
        
        # Проверяем время: с 14:00 до 23:00 каждый час в :00 минут
        if 14 <= current_hour <= 23 and current_minute == 0:
            logger.info(f"✅ Отправка ежечасного статуса каптов в {current_hour:02d}:00 МСК")
            
            # Получаем список всех уникальных чатов где есть капты
            unique_chats = set()
            for chat_id, _ in event_messages.values():
                unique_chats.add(chat_id)
            
            for chat_id in unique_chats:
                try:
                    # Используем функцию kapt_command для формирования текста
                    status_text = await generate_kapt_text()
                    
                    if status_text:
                        message = await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"🕐 *ЕЖЕЧАСНЫЙ СТАТУС КАПТОВ* 🕐\n\n{status_text}",
                            parse_mode='Markdown'
                        )
                        # Сохраняем ID сообщения для последующего удаления
                        bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                        logger.info(f"✅ Ежечасный статус отправлен в чат {chat_id}")
                    else:
                        message = await application.bot.send_message(
                            chat_id=chat_id,
                            text="🕐 *ЕЖЕЧАСНЫЙ СТАТУС КАПТОВ* 🕐\n\n📭 *Активных каптов нет*",
                            parse_mode='Markdown'
                        )
                        bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                        logger.info(f"✅ Статус 'нет каптов' отправлен в чат {chat_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки ежечасного статуса в чат {chat_id}: {e}")
        else:
            logger.info(f"⏰ Не время для статуса: {current_hour:02d}:{current_minute:02d} МСК")
                    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ежечасного статуса: {e}")

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
            
            # Ежечасный статус каптов
            await send_hourly_kapt_status(application)
            
            # Спокойной ночи
            await send_good_night(application)
            
            # Очистка сообщений
            await cleanup_old_messages(application)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в планировщике: {e}")
            await asyncio.sleep(60)

# ... остальные функции (start, ping_command, commands, и т.д.) остаются без изменений

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
    print("🕐 Ежечасный статус с 14:00 до 23:00!")
    print("🌙 Спокойной ночи в 23:59!")
    print("🧹 Очистка сообщений в 6:00!")
    print("🏓 Команда /ping доступна!")
    print("⏰ Московское время: UTC+3 (постоянно)")
    
    application.run_polling()

if __name__ == "__main__":
    main()
