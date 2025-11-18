import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from flask import Flask
import threading

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
    logging.error("❌ BOT_TOKEN не найден!")
    exit(1)

events = {}
admins = set()
root_users = set()
ADMIN_PASSWORD = "24680"
ROOT_PASSWORD = "1508"

# Для хранения ID сообщений бота
bot_messages = []

# Московское время (UTC+3)
MOSCOW_UTC_OFFSET = 3

def get_moscow_time():
    """Получаем московское время"""
    return datetime.utcnow() + timedelta(hours=MOSCOW_UTC_OFFSET)

async def cleanup_bot_messages(application):
    """Автоочистка сообщений бота в 6:00 по МСК"""
    while True:
        try:
            now = get_moscow_time()
            
            # Если сейчас 6:00 утра по МСК
            if now.hour == 6 and now.minute == 0:
                logger.info("🕕 Начинаю автоочистку сообщений бота...")
                
                # Отправляем сообщение о начале очистки
                cleanup_msg = await application.bot.send_message(
                    chat_id=list(events.keys())[0] if events else None,  # Отправляем в первый доступный чат
                    text="🔄 *Автоочистка сообщений бота*\n\n"
                         "⏰ *Время:* 6:00 по МСК\n"
                         "👨‍💻 *Создатель:* ChikenXa\n"
                         "🗑️ *Удаляю все сообщения бота...*",
                    parse_mode='Markdown'
                )
                
                deleted_count = 0
                # Удаляем все сообщения бота
                for chat_id, message_id in bot_messages:
                    try:
                        await application.bot.delete_message(chat_id, message_id)
                        deleted_count += 1
                        await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты
                    except Exception as e:
                        logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")
                
                # Очищаем список сообщений
                bot_messages.clear()
                
                # Отправляем сообщение о завершении очистки
                await application.bot.send_message(
                    chat_id=cleanup_msg.chat_id,
                    text=f"✅ *Автоочистка завершена!*\n\n"
                         f"🗑️ *Удалено сообщений:* {deleted_count}\n"
                         f"⏰ *Время:* 6:00 по МСК\n"
                         f"👨‍💻 *Создатель:* ChikenXa\n\n"
                         f"_Следующая очистка завтра в 6:00_",
                    parse_mode='Markdown'
                )
                
                # Удаляем сообщение о начале очистки
                await cleanup_msg.delete()
                
                logger.info(f"✅ Автоочистка завершена. Удалено сообщений: {deleted_count}")
                
                # Ждем 1 минуту чтобы не запускать несколько раз в 6:00
                await asyncio.sleep(60)
            else:
                # Проверяем каждую минуту
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в автоочистке: {e}")
            await asyncio.sleep(60)

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход как админ"""
    try:
        if not context.args:
            msg = await update.message.reply_text("🔐 *Введите пароль:* `/alogin пароль`", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        password = context.args[0]
        user = update.effective_user
        
        if password == ADMIN_PASSWORD:
            admins.add(user.id)
            msg = await update.message.reply_text(
                f"✅ *Добро пожаловать в админ-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
            bot_messages.append((msg.chat_id, msg.message_id))
        else:
            msg = await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка входа!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def root_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход как root"""
    try:
        if not context.args:
            msg = await update.message.reply_text("👑 *Введите пароль:* `/root пароль`", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        password = context.args[0]
        user = update.effective_user
        
        if password == ROOT_PASSWORD:
            root_users.add(user.id)
            admins.add(user.id)
            msg = await update.message.reply_text(
                f"👑 *Добро пожаловать в root-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
            bot_messages.append((msg.chat_id, msg.message_id))
        else:
            msg = await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка входа!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = await update.message.reply_text(
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
    bot_messages.append((msg.chat_id, msg.message_id))

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in admins
    is_root = user.id in root_users
    
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
    
    if is_admin or is_root:
        text += "🛠️ *Админ команды:*\n"
        text += "• `/alogin пароль` - войти как админ\n"
        text += "• `/kick @username код` - кикнуть игрока\n"
        text += "• `/del код` - удалить капт\n\n"
    
    if is_root:
        text += "👑 *Root команды:*\n"
        text += "• `/root пароль` - войти как root\n"
        text += "• `/addadmin user_id` - добавить админа\n"
        text += "• `/removeadmin user_id` - удалить админа\n"
        text += "• `/listadmins` - список админов\n\n"
    
    msg = await update.message.reply_text(text, parse_mode='Markdown')
    bot_messages.append((msg.chat_id, msg.message_id))

async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 8:
            msg = await update.message.reply_text(
                "🎯 *Создание капта*\n\n"
                "📋 *Формат:*\n"
                "`/create код название слоты дата время оружие хил роль`\n\n"
                "📝 *Пример:*\n"
                "`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`",
                parse_mode='Markdown'
            )
            bot_messages.append((msg.chat_id, msg.message_id))
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
            msg = await update.message.reply_text(f"⚠️ *Капт {event_code} уже существует!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
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
            'author_id': user.id
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
        
        msg = await update.message.reply_text(event_text, parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))
        
        try:
            await msg.pin()
        except:
            pass
        
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка создания капта!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            msg = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event = events[event_code]
        
        if len(event['participants']) >= int(event['slots']):
            msg = await update.message.reply_text("🚫 *Нет свободных слотов!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        user_already_registered = any(participant['user_id'] == user.id for participant in event['participants'])
        if user_already_registered:
            msg = await update.message.reply_text("⚠️ *Ты уже в капте!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        if user.username:
            display_name = f"@{user.username}"
        else:
            display_name = user.first_name
        
        participant_data = {
            'user_id': user.id,
            'username': user.username,
            'display_name': display_name,
            'first_name': user.first_name
        }
        event['participants'].append(participant_data)
        free_slots = int(event['slots']) - len(event['participants'])
        
        msg = await update.message.reply_text(
            f"✅ *{display_name} записан в капт!*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка записи!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def ex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            msg = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event = events[event_code]
        
        participant_index = None
        for i, participant in enumerate(event['participants']):
            if participant['user_id'] == user.id:
                participant_index = i
                break
        
        if participant_index is None:
            msg = await update.message.reply_text("⚠️ *Ты не в этом капте!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        removed_participant = event['participants'].pop(participant_index)
        free_slots = int(event['slots']) - len(event['participants'])
        
        msg = await update.message.reply_text(
            f"❌ *{removed_participant['display_name']} вышел из капта*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка выхода!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def kapt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not events:
            msg = await update.message.reply_text("📭 *Активных каптов нет*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        text = "🎯 *АКТИВНЫЕ КАПТЫ*\n\n"
        
        for code, event in events.items():
            free_slots = int(event['slots']) - len(event['participants'])
            
            participants_list = ""
            if event['participants']:
                participants_list = "\n👥 *Участники:*\n"
                for i, participant in enumerate(event['participants'], 1):
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
        
        msg = await update.message.reply_text(text, parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        if not is_admin(user.id):
            msg = await update.message.reply_text("❌ *Нет прав админа!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
            
        if len(context.args) < 2:
            msg = await update.message.reply_text("❌ *Формат:* `/kick @username код`", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        username_input = context.args[0]
        event_code = context.args[1]
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
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
            msg = await update.message.reply_text(f"❌ *Участник {username_input} не найден в капте {event_code}!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event['participants'].pop(participant_index)
        free_slots = int(event['slots']) - len(event['participants'])
        
        msg = await update.message.reply_text(
            f"🚫 *Участник {removed_participant['display_name']} исключен из капта!*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка кика!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def delete_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
        if not is_admin(user.id):
            msg = await update.message.reply_text("❌ *Нет прав админа!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
            
        if not context.args:
            msg = await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code = context.args[0]
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        del events[event_code]
        
        msg = await update.message.reply_text(
            f"🗑️ *Капт {event_code} удален!*",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except Exception as e:
        msg = await update.message.reply_text("❌ *Ошибка удаления!*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

def is_admin(user_id):
    return user_id in admins

def is_root(user_id):
    return user_id in root_users

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем хэндлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CommandHandler("alogin", admin_login))
    application.add_handler(CommandHandler("root", root_login))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("create", create_event))
    application.add_handler(CommandHandler("go", go_command))
    application.add_handler(CommandHandler("ex", ex_command))
    application.add_handler(CommandHandler("kapt", kapt_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("del", delete_event_command))
    
    # Запускаем автоочистку сообщений
    application.job_queue.run_once(
        lambda context: asyncio.create_task(cleanup_bot_messages(application)), 
        when=0
    )
    
    print("🎮 CAPT BOT запущен!")
    print("🛠️ Создатель: ChikenXa")
    print("🔐 Пароль админа: 24680")
    print("👑 Пароль root: 1508")
    print("⏰ Автоочистка сообщений в 6:00 по МСК активна")
    print("👨‍💻 Создатель: ChikenXa")
    
    application.run_polling()

if __name__ == "__main__":
    main()
