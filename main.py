import os
import logging
import asyncio
from datetime import datetime, timedelta
import pytz
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Проверка наличия токена
if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN не найден в переменных окружения!")
    logging.info("💡 Добавьте BOT_TOKEN в Environment Variables на Render")
    exit(1)

# Хранилище данных
events = {}
admins = set()
bot_messages = []  # Храним ID сообщений бота
pinned_messages = {}  # Храним закрепленные сообщения по кодам событий

# Московский часовой пояс
moscow_tz = pytz.timezone('Europe/Moscow')

async def cleanup_old_messages(application):
    """Очистка старых сообщений бота в 6:00 по МСК"""
    while True:
        try:
            now = datetime.now(moscow_tz)
            
            # Если сейчас 6:00 утра по МСК
            if now.hour == 6 and now.minute == 0:
                logger.info("🕕 Начинаю очистку сообщений...")
                
                # Удаляем все сообщения бота (кроме закрепленных)
                messages_to_delete = [msg for msg in bot_messages if msg not in pinned_messages.values()]
                
                for chat_id, message_id in messages_to_delete:
                    try:
                        await application.bot.delete_message(chat_id, message_id)
                        logger.info(f"🗑️ Удалено сообщение {message_id} в чате {chat_id}")
                        await asyncio.sleep(0.1)  # Небольшая задержка чтобы не превысить лимиты
                    except Exception as e:
                        logger.error(f"❌ Ошибка удаления сообщения {message_id}: {e}")
                
                # Очищаем список сообщений (кроме закрепленных)
                bot_messages.clear()
                for pinned_msg in pinned_messages.values():
                    bot_messages.append(pinned_msg)
                
                # Очищаем события предыдущего дня
                events_to_delete = []
                for code, event in events.items():
                    try:
                        event_date = datetime.strptime(event['date'], '%d.%m').replace(year=now.year)
                        if event_date.date() < now.date():
                            events_to_delete.append(code)
                    except:
                        events_to_delete.append(code)
                
                for code in events_to_delete:
                    del events[code]
                    if code in pinned_messages:
                        del pinned_messages[code]
                    logger.info(f"🗑️ Удалено событие {code}")
                
                logger.info("✅ Очистка завершена")
                
                # Ждем 1 минуту чтобы не запускать несколько раз в 6:00
                await asyncio.sleep(60)
            else:
                # Проверяем каждую минуту
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в cleanup_old_messages: {e}")
            await asyncio.sleep(60)

async def pin_event_message(application, chat_id, message_id, event_code):
    """Закрепляем сообщение о событии и сохраняем его"""
    try:
        await application.bot.pin_chat_message(chat_id, message_id)
        pinned_messages[event_code] = (chat_id, message_id)
        bot_messages.append((chat_id, message_id))
        logger.info(f"📌 Закреплено сообщение для события {event_code}")
    except Exception as e:
        logger.error(f"❌ Ошибка закрепления сообщения: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = await update.message.reply_text(
        f"👋 *Привет, {user.first_name}!*\n\n"
        f"🎮 *CAPT BOT* - твой помощник для организации каптов\n\n"
        f"📱 *Основные команды:*\n"
        f"• `/commands` - все команды\n"
        f"• `/create` - создать капт\n"
        f"• `/kapt` - список каптов\n"
        f"• `/go [код]` - записаться\n"
        f"• `/ex [код]` - выйти\n\n"
        f"⚡ *Быстрый старт:*\n"
        f"`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`\n"
        f"`/go 1` - записаться",
        parse_mode='Markdown'
    )
    bot_messages.append((message.chat_id, message.message_id))

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in admins
    
    text = "📋 *СПИСОК КОМАНД*\n\n"
    text += "👥 *Для всех:*\n"
    text += "• `/start` - начать работу\n"
    text += "• `/commands` - этот список\n"
    text += "• `/kapt` - активные капты\n"
    text += "• `/go [код]` - записаться\n"
    text += "• `/ex [код]` - выйти\n\n"
    text += "🎯 *Создание капта:*\n"
    text += "• `/create код название слоты дата время оружие хил роль`\n"
    text += "_Пример: /create 1 Рейд 5 20.11 21:30 Лук Да Защита_\n\n"
    
    if is_admin:
        text += "🛠️ *Админ команды:*\n"
        text += "• `/alogin пароль` - войти как админ\n"
        text += "• `/kick @user код` - кикнуть игрока\n"
        text += "• `/del код` - удалить капт\n"
        text += "• `/aclean` - очистить все капты\n\n"
    
    message = await update.message.reply_text(text, parse_mode='Markdown')
    bot_messages.append((message.chat_id, message.message_id))

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("🔐 *Требуется пароль*", parse_mode='Markdown')
            return
        
        password = context.args[0]
        user = update.effective_user
        
        if password == "1512":
            admins.add(user.id)
            message = await update.message.reply_text(
                f"✅ *Добро пожаловать в админ-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
            bot_messages.append((message.chat_id, message.message_id))
        else:
            message = await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка входа!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))

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
            bot_messages.append((message.chat_id, message.message_id))
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
            bot_messages.append((message.chat_id, message.message_id))
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
            'created_at': datetime.now(moscow_tz)
        }
        
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
            f"👤 **Создатель:** {user.first_name}\n\n"
            f"⚡ **Записаться:** `/go {event_code}`\n"
            f"❌ **Выйти:** `/ex {event_code}`"
        )
        
        message = await update.message.reply_text(event_text, parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))
        
        # Закрепляем сообщение о создании события
        await pin_event_message(application, message.chat_id, message.message_id, event_code)
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка создания капта!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        event = events[event_code]
        
        if len(event['participants']) >= int(event['slots']):
            message = await update.message.reply_text("🚫 *Нет свободных слотов!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        # Проверяем, не записан ли уже пользователь
        user_already_registered = any(participant['user_id'] == user.id for participant in event['participants'])
        if user_already_registered:
            message = await update.message.reply_text("⚠️ *Ты уже в капте!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        # Добавляем пользователя с username
        participant_data = {
            'user_id': user.id,
            'username': f"@{user.username}" if user.username else user.first_name,
            'first_name': user.first_name
        }
        event['participants'].append(participant_data)
        free_slots = int(event['slots']) - len(event['participants'])
        
        message = await update.message.reply_text(
            f"✅ *{user.first_name} записан в капт!*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка записи!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))

async def ex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        event = events[event_code]
        
        # Ищем участника по user_id
        participant_index = None
        for i, participant in enumerate(event['participants']):
            if participant['user_id'] == user.id:
                participant_index = i
                break
        
        if participant_index is None:
            message = await update.message.reply_text("⚠️ *Ты не в этом капте!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        # Удаляем участника
        removed_participant = event['participants'].pop(participant_index)
        free_slots = int(event['slots']) - len(event['participants'])
        
        message = await update.message.reply_text(
            f"❌ *{user.first_name} вышел из капта*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка выхода!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))

async def kapt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not events:
            message = await update.message.reply_text("📭 *Активных каптов нет*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        text = "🎯 *АКТИВНЫЕ КАПТЫ*\n\n"
        
        for code, event in events.items():
            free_slots = int(event['slots']) - len(event['participants'])
            
            # Формируем список участников с @username
            participants_list = ""
            if event['participants']:
                participants_list = "\n👥 *Участники:*\n"
                for i, participant in enumerate(event['participants'], 1):
                    participants_list += f"{i}. {participant['username']}\n"
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
        bot_messages.append((message.chat_id, message.message_id))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))

async def delete_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление события (только для админов или создателя)"""
    try:
        if not context.args:
            message = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            message = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        event = events[event_code]
        
        # Проверяем права: админ или создатель
        if not (is_admin(user.id) or event['author_id'] == user.id):
            message = await update.message.reply_text("❌ *Нет прав для удаления!*", parse_mode='Markdown')
            bot_messages.append((message.chat_id, message.message_id))
            return
        
        # Открепляем сообщение если оно закреплено
        if event_code in pinned_messages:
            chat_id, message_id = pinned_messages[event_code]
            try:
                await application.bot.unpin_chat_message(chat_id, message_id)
            except:
                pass
            del pinned_messages[event_code]
        
        # Удаляем событие
        del events[event_code]
        
        message = await update.message.reply_text(
            f"🗑️ *Капт {event_code} удален!*",
            parse_mode='Markdown'
        )
        bot_messages.append((message.chat_id, message.message_id))
        
    except Exception as e:
        message = await update.message.reply_text("❌ *Ошибка удаления!*", parse_mode='Markdown')
        bot_messages.append((message.chat_id, message.message_id))

def is_admin(user_id):
    return user_id in admins

# Глобальная переменная для application
application = None

def main():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CommandHandler("alogin", admin_login))
    application.add_handler(CommandHandler("create", create_event))
    application.add_handler(CommandHandler("go", go_command))
    application.add_handler(CommandHandler("ex", ex_command))
    application.add_handler(CommandHandler("kapt", kapt_command))
    application.add_handler(CommandHandler("del", delete_event_command))
    
    # Запускаем очистку сообщений в фоне
    application.job_queue.run_once(
        lambda context: asyncio.create_task(cleanup_old_messages(application)), 
        when=0
    )
    
    print("🎮 CAPT BOT запущен на Render!")
    print("🛠️ Создатель: ChikenXa")
    print("⏰ Автоочистка в 6:00 по МСК активна")
    
    application.run_polling()

if __name__ == "__main__":
    main()
