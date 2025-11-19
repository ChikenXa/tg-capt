import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8186945089:AAHAx_pWrtKBYEh61NSsWtiAEofCeP37tH4"

# Глобальные переменные
events = {}
admins = {}
root_users = {}
ADMIN_PASSWORD = "24680"
ROOT_PASSWORD = "1508"

waiting_for_password = {}
event_messages = {}
bot_messages = []
daily_status_sent = {}
last_participant_count = {}

# Московское время постоянно UTC+3
MOSCOW_UTC_OFFSET = 3

def get_moscow_time():
    """Получаем точное московское время (UTC+3)"""
    return datetime.utcnow() + timedelta(hours=MOSCOW_UTC_OFFSET)

def is_admin(user_id):
    return user_id in admins

def is_root(user_id):
    return user_id in root_users

async def hacker_cleanup_animation(application, chat_id):
    """Хакерская анимация очистки"""
    try:
        # Старт системы
        msg1 = await application.bot.send_message(
            chat_id=chat_id,
            text="```\n🖥️ ЗАПУСК СИСТЕМЫ ОЧИСТКИ...\n```",
            parse_mode='Markdown'
        )
        await asyncio.sleep(1.5)

        # Подключение к базе
        await application.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg1.message_id,
            text="```\n🖥️ СИСТЕМА ОЧИСТКИ АКТИВИРОВАНА\n📡 Подключаюсь к базе данных...\n```",
            parse_mode='Markdown'
        )
        await asyncio.sleep(1.5)

        # Сканирование
        await application.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg1.message_id,
            text="```\n🖥️ СИСТЕМА ОЧИСТКИ АКТИВИРОВАНА\n✅ Подключение к БД установлено\n🔍 Сканирую файловую систему...\n```",
            parse_mode='Markdown'
        )
        await asyncio.sleep(2)

        return msg1

    except Exception as e:
        logger.error(f"Ошибка анимации очистки: {e}")
        return None

async def update_progress(application, chat_id, message_id, step, total_steps, deleted_count, total_to_delete, found_kapts):
    """Обновление прогресса очистки"""
    progress_bar = "█" * int((step / total_steps) * 20) + "░" * (20 - int((step / total_steps) * 20))
    percentage = int((step / total_steps) * 100)
    
    text = (
        f"```\n"
        f"🖥️ СИСТЕМА ОЧИСТКИ - ВЫПОЛНЕНИЕ\n"
        f"📊 Прогресс: [{progress_bar}] {percentage}%\n"
        f"🗑️ Удалено сообщений: {deleted_count}/{total_to_delete}\n"
        f"🎯 Найдено каптов: {found_kapts}\n"
        f"⏰ Время: {get_moscow_time().strftime('%H:%M:%S')}\n"
        f"```"
    )
    
    try:
        await application.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown'
        )
    except:
        pass

async def hacker_cleanup(application):
    """Хакерская очистка системы"""
    try:
        current_time = get_moscow_time()
        logger.info(f"🧹 ХАКЕРСКАЯ ОЧИСТКА: {current_time.strftime('%H:%M')} МСК")

        # Проверяем время: только в 6:00 утра
        if current_time.hour == 6 and current_time.minute == 0:
            logger.info("🚀 ЗАПУСК ХАКЕРСКОЙ ОЧИСТКИ СИСТЕМЫ...")

            # Получаем список всех уникальных чатов
            unique_chats = set()
            for chat_id, _ in event_messages.values():
                unique_chats.add(chat_id)

            total_stats = {
                'messages_deleted': 0,
                'kapts_cleaned': 0,
                'chats_processed': 0
            }

            for chat_id in unique_chats:
                try:
                    total_stats['chats_processed'] += 1
                    
                    # Запускаем хакерскую анимацию
                    status_msg = await hacker_cleanup_animation(application, chat_id)
                    if not status_msg:
                        continue

                    # 🔥 ЭТАП 1: Сканирование сообщений
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text="```\n🖥️ СИСТЕМА ОЧИСТКИ АКТИВИРОВАНА\n✅ Подключение к БД установлено\n🔍 Сканирую файловую систему...\n📊 Анализ кэша сообщений...\n```",
                        parse_mode='Markdown'
                    )
                    await asyncio.sleep(2)

                    # Поиск сообщений для удаления (старше 1 часа)
                    messages_to_delete = []
                    current_timestamp = current_time.timestamp()

                    for msg_chat_id, message_id, timestamp in bot_messages[:]:
                        if msg_chat_id == chat_id and current_timestamp - timestamp > 3600:
                            messages_to_delete.append((message_id, timestamp))

                    # 🔥 ЭТАП 2: Удаление сообщений
                    deleted_count = 0
                    total_to_delete = len(messages_to_delete)
                    
                    if total_to_delete > 0:
                        await application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=status_msg.message_id,
                            text=f"```\n🖥️ СИСТЕМА ОЧИСТКИ - СТАРТ\n📊 Найдено объектов: {total_to_delete}\n🗑️ Инициализация протокола удаления...\n⚡ Подготовка к очистке...\n```",
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(2)

                        # Удаляем сообщения с прогрессом
                        for i, (message_id, timestamp) in enumerate(messages_to_delete):
                            try:
                                await application.bot.delete_message(chat_id, message_id)
                                deleted_count += 1
                                total_stats['messages_deleted'] += 1
                                
                                # Обновляем прогресс каждые 5 сообщений или если это последнее
                                if i % 5 == 0 or i == total_to_delete - 1:
                                    await update_progress(
                                        application, chat_id, status_msg.message_id,
                                        i + 1, total_to_delete, deleted_count, total_to_delete, 0
                                    )
                                    await asyncio.sleep(0.3)
                                    
                            except Exception as e:
                                logger.warning(f"⚠️ Не удалось удалить сообщение {message_id}: {e}")

                    # Удаляем обработанные сообщения из списка
                    for message_id, timestamp in messages_to_delete:
                        for msg in bot_messages[:]:
                            if msg[0] == chat_id and msg[1] == message_id:
                                bot_messages.remove(msg)
                                break

                    # 🔥 ЭТАП 3: Очистка каптов
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text="```\n🖥️ СИСТЕМА ОЧИСТКИ - ЭТАП 2\n✅ Сообщения обработаны\n🎯 Сканирую архив каптов...\n🔍 Поиск устаревших событий...\n```",
                        parse_mode='Markdown'
                    )
                    await asyncio.sleep(2)

                    # Очищаем завершенные капты
                    current_date = current_time.strftime("%d.%m")
                    events_to_remove = []
                    found_kapts = 0

                    for event_code, event in events.items():
                        event_date = event['date']
                        try:
                            event_day, event_month = event_date.split('.')
                            current_day, current_month = current_date.split('.')
                            
                            # Если капт прошел (дата меньше текущей)
                            if (int(current_month) > int(event_month)) or \
                               (int(current_month) == int(event_month) and int(current_day) > int(event_day)):
                                events_to_remove.append(event_code)
                                found_kapts += 1
                        except:
                            pass

                    # Удаляем капты
                    kapts_deleted = 0
                    if events_to_remove:
                        await application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=status_msg.message_id,
                            text=f"```\n🖥️ СИСТЕМА ОЧИСТКИ - ЭТАП 3\n🎯 Найдено каптов: {found_kapts}\n🗑️ Очистка архива событий...\n⚡ Выполняю деинсталляцию...\n```",
                            parse_mode='Markdown'
                        )
                        await asyncio.sleep(2)

                        for i, event_code in enumerate(events_to_remove):
                            if event_code in event_messages:
                                try:
                                    event_chat_id, event_message_id = event_messages[event_code]
                                    if event_chat_id == chat_id:
                                        await application.bot.delete_message(chat_id, event_message_id)
                                        await application.bot.unpin_chat_message(chat_id, event_message_id)
                                        kapts_deleted += 1
                                        total_stats['kapts_cleaned'] += 1
                                except:
                                    pass
                                del event_messages[event_code]
                            del events[event_code]

                    # 🔥 ФИНАЛЬНЫЙ ОТЧЕТ
                    final_text = (
                        f"```\n"
                        f"🖥️ СИСТЕМА ОЧИСТКИ - ЗАВЕРШЕНО\n"
                        f"✅ ОПЕРАЦИЯ УСПЕШНО ВЫПОЛНЕНА\n\n"
                        f"📊 СТАТИСТИКА ВЫПОЛНЕНИЯ:\n"
                        f"├── Удалено сообщений: {deleted_count}\n"
                        f"├── Очищено каптов: {kapts_deleted}\n"
                        f"├── Активных каптов: {len(events)}\n"
                        f"└── Сообщений в памяти: {len(bot_messages)}\n\n"
                        f"🎯 СИСТЕМА ГОТОВА К РАБОТЕ\n"
                        f"⏰ {get_moscow_time().strftime('%d.%m.%Y %H:%M:%S')}\n"
                        f"```\n\n"
                        f"_🛠️ Процесс завершен. Система оптимизирована._"
                    )

                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=final_text,
                        parse_mode='Markdown'
                    )

                    # Сохраняем финальное сообщение
                    bot_messages.append((status_msg.chat_id, status_msg.message_id, current_time.timestamp()))

                    logger.info(f"✅ Хакерская очистка завершена в чате {chat_id}")

                except Exception as e:
                    logger.error(f"❌ Ошибка хакерской очистки в чате {chat_id}: {e}")

            # ИТОГОВАЯ СТАТИСТИКА
            logger.info(f"🎯 ХАКЕРСКАЯ ОЧИСТКА ЗАВЕРШЕНА:")
            logger.info(f"📊 Обработано чатов: {total_stats['chats_processed']}")
            logger.info(f"🗑️ Удалено сообщений: {total_stats['messages_deleted']}")
            logger.info(f"🎯 Очищено каптов: {total_stats['kapts_cleaned']}")
            logger.info(f"⚡ Активных каптов: {len(events)}")

        else:
            logger.info(f"⏰ Не время для очистки: {current_time.strftime('%H:%M')} МСК")

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В ХАКЕРСКОЙ ОЧИСТКЕ: {e}")

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
        
        # Проверяем, изменилось ли количество участников
        current_count = len(event['participants'])
        previous_count = last_participant_count.get(event_code, 0)
        
        if current_count != previous_count:
            last_participant_count[event_code] = current_count
            await resend_and_pin_event_message(application, event_code)
            
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения капта: {e}")

async def resend_and_pin_event_message(application, event_code):
    """Переотправляем и закрепляем сообщение капта при изменении участников"""
    if event_code not in events:
        return
        
    try:
        event = events[event_code]
        old_chat_id, old_message_id = event_messages[event_code]
        
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
        
        # Удаляем старое сообщение
        try:
            await application.bot.delete_message(old_chat_id, old_message_id)
        except:
            pass
            
        # Отправляем новое сообщение
        message = await application.bot.send_message(
            chat_id=old_chat_id,
            text=event_text,
            parse_mode='Markdown'
        )
        
        # Обновляем данные сообщения
        event_messages[event_code] = (message.chat_id, message.message_id)
        bot_messages.append((message.chat_id, message.message_id, get_moscow_time().timestamp()))
        
        # Закрепляем новое сообщение
        await pin_event_message(application, message.chat_id, message.message_id)
        
        logger.info(f"🔄 Сообщение капта {event_code} переотправлено и закреплено")
        
    except Exception as e:
        logger.error(f"❌ Ошибка переотправки сообщения капта: {e}")

async def pin_event_message(application, chat_id, message_id):
    """Закрепляем сообщение с каптом"""
    try:
        await application.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True
        )
        logger.info(f"📌 Сообщение {message_id} закреплено в чате {chat_id}")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось закрепить сообщение: {e}")

async def send_event_reminders(application):
    """Отправляем напоминания за 30 минут до капта"""
    try:
        current_time = get_moscow_time()
        logger.info(f"🔔 Проверка напоминаний: {current_time.strftime('%H:%M')} МСК")

        for event_code, event in events.items():
            try:
                event_date_str = event['date']
                event_time_str = event['time']
                current_year = current_time.year
                event_datetime_str = f"{event_date_str}.{current_year} {event_time_str}"

                try:
                    event_datetime = datetime.strptime(event_datetime_str, "%d.%m.%Y %H:%M")
                except ValueError:
                    continue

                time_diff = event_datetime - current_time
                time_diff_minutes = time_diff.total_seconds() / 60

                if 0 <= time_diff_minutes <= 30:
                    if not event.get('reminder_sent', False):
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

                                if event_code in event_messages:
                                    chat_id, _ = event_messages[event_code]
                                    message = await application.bot.send_message(
                                        chat_id=chat_id,
                                        text=reminder_text,
                                        parse_mode='Markdown'
                                    )
                                    bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                                    logger.info(f"✅ Напоминание для капта {event_code}")

                            event['reminder_sent'] = True

            except Exception as e:
                logger.error(f"❌ Ошибка напоминания для капта {event_code}: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка в функции напоминаний: {e}")

async def send_daily_kapt_status(application):
    """Отправляем статус каптов в 14:00 по МСК"""
    try:
        current_time = get_moscow_time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_date = current_time.strftime("%Y-%m-%d")

        if current_hour == 14 and current_minute == 0:
            logger.info("✅ Отправка ежедневного статуса каптов в 14:00 МСК")

            unique_chats = set()
            for chat_id, _ in event_messages.values():
                unique_chats.add(chat_id)

            for chat_id in unique_chats:
                try:
                    if daily_status_sent.get(chat_id) == current_date:
                        continue

                    status_text = await generate_kapt_text()

                    if status_text:
                        message = await application.bot.send_message(
                            chat_id=chat_id,
                            text=f"🕐 *ЕЖЕДНЕВНЫЙ СТАТУС КАПТОВ* 🕐\n\n{status_text}",
                            parse_mode='Markdown'
                        )
                        await pin_event_message(application, chat_id, message.message_id)
                        bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                        daily_status_sent[chat_id] = current_date
                        logger.info(f"✅ Ежедневный статус отправлен в чат {chat_id}")
                    else:
                        message = await application.bot.send_message(
                            chat_id=chat_id,
                            text="🕐 *ЕЖЕДНЕВНЫЙ СТАТУС КАПТОВ* 🕐\n\n📭 *Активных каптов нет*",
                            parse_mode='Markdown'
                        )
                        bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                        daily_status_sent[chat_id] = current_date

                except Exception as e:
                    logger.error(f"❌ Ошибка отправки статуса в чат {chat_id}: {e}")

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

        if current_time.hour == 23 and current_time.minute == 59:
            logger.info("✅ Отправка спокойной ночи")

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
                    bot_messages.append((message.chat_id, message.message_id, current_time.timestamp()))
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки спокойной ночи в чат {chat_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка отправки спокойной ночи: {e}")

async def scheduled_task_wrapper(context):
    """Обертка для планировщика задач"""
    await scheduled_tasks(context.application)

async def scheduled_tasks(application):
    """Планировщик задач"""
    try:
        current_time = get_moscow_time()
        logger.info(f"🕐 ПЛАНИРОВЩИК: {current_time.strftime('%H:%M')} МСК")

        await send_event_reminders(application)
        await send_daily_kapt_status(application)
        await send_good_night(application)
        await hacker_cleanup(application)  # 🔥 Используем хакерскую очистку

    except Exception as e:
        logger.error(f"❌ Ошибка в планировщике: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = await update.message.reply_text(
        f"👋 *Привет, {user.first_name}!*\n\n"
        f"🎮 *CAPT BOT v2.0* - твой помощник для организации каптов\n\n"
        f"📱 *Основные команды:*\n"
        f"• `/commands` - все команды\n"
        f"• `/ping` - проверить работу бота\n"
        f"• `/create` - создать капт\n"
        f"• `/kapt` - список каптов\n"
        f"• `/go [код]` - записаться\n"
        f"• `/ex [код]` - выйти\n\n"
        f"⚡ *Быстрый старт:*\n"
        f"`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`\n\n"
        f"🔥 *Автоматические функции:*\n"
        f"• Напоминания за 30 минут до капта\n"
        f"• Статус каптов каждый день в 14:00 МСК\n"
        f"• Спокойной ночи в 23:59\n"
        f"• 🧹 ХАКЕРСКАЯ ОЧИСТКА в 6:00\n"
        f"• Авто-обновление сообщений\n\n"
        f"👨‍💻 _Разработано ChikenXa (Данил)_",
        parse_mode='Markdown'
    )
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
    
    text += "🔥 *Автоматические функции:*\n"
    text += "• Напоминания за 30 минут до капта\n"
    text += "• Статус каптов каждый день в 14:00 МСК\n"
    text += "• Спокойной ночи в 23:59\n"
    text += "• 🧹 ХАКЕРСКАЯ ОЧИСТКА в 6:00\n"
    text += "• Авто-обновление сообщений\n\n"
    
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
        time_str = context.args[4]
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
            'time': time_str,
            'weapon_type': weapon_type,
            'heal': heal,
            'role': role,
            'participants': [],
            'author': user.first_name,
            'author_id': user.id,
            'reminder_sent': False
        }

        # Инициализируем счетчик участников
        last_participant_count[event_code] = 0
        
        free_slots = int(slots)
        
        participants_list = "\n👥 *Участники:* пока нет\n"
        
        event_text = (
            f"🎯 *НОВЫЙ КАПТ СОЗДАН!*\n\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"📝 **Название:** {name}\n"
            f"🎫 **Слоты:** {slots}\n"
            f"📅 **Дата:** {date}\n"
            f"⏰ **Время:** {time_str} МСК\n"
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
        
        # Обновляем сообщение (внутри update_event_message будет проверка на изменение участников)
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
        
        # Обновляем сообщение (внутри update_event_message будет проверка на изменение участников)
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
    
    # Запускаем планировщик
    application.job_queue.run_repeating(
        scheduled_task_wrapper,
        interval=30,
        first=10
    )
    
    print("🎮 CAPT BOT v2.0 ЗАПУЩЕН!")
    print("🔥 ХАКЕРСКАЯ ОЧИСТКА АКТИВИРОВАНА")
    print("🛠️ Создатель: ChikenXa")
    print("🔐 Пароль админа: 24680")
    print("👑 Пароль root: 1508")
    print("⏰ Московское время: UTC+3")
    print("🧹 Очистка: 6:00 утра с хакерской анимацией!")
    
    application.run_polling()

if __name__ == "__main__":
    main()
