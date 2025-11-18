import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
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

# Запускаем веб-сервер в отдельном потоке
threading.Thread(target=run_web, daemon=True).start()

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
    exit(1)

# Хранилище данных
events = {}
admins = set()
root_users = set()
ADMIN_PASSWORD = "24680"
ROOT_PASSWORD = "1508"

# Для ожидания паролей в ЛС
waiting_for_password = {}  # {user_id: 'admin' или 'root'}

# Московское время (UTC+3)
MOSCOW_UTC_OFFSET = 3

def get_moscow_time():
    return datetime.utcnow() + timedelta(hours=MOSCOW_UTC_OFFSET)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
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
        text += "• `/alogin` - войти как админ\n"
        text += "• `/kick @username код` - кикнуть игрока\n"
        text += "• `/del код` - удалить капт\n\n"
    
    if is_root:
        text += "👑 *Root команды:*\n"
        text += "• `/root` - войти как root\n"
        text += "• `/addadmin @username` - добавить админа\n"
        text += "• `/removeadmin @username` - удалить админа\n"
        text += "• `/listadmins` - список админов\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос пароля админа в ЛС"""
    user = update.effective_user
    
    # Удаляем сообщение с командой
    try:
        await update.message.delete()
    except:
        pass
    
    # Запрашиваем пароль в ЛС
    waiting_for_password[user.id] = 'admin'
    await context.bot.send_message(
        chat_id=user.id,
        text="🔐 *Введите пароль админа:*",
        parse_mode='Markdown'
    )

async def root_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос root пароля в ЛС"""
    user = update.effective_user
    
    # Удаляем сообщение с командой
    try:
        await update.message.delete()
    except:
        pass
    
    # Запрашиваем пароль в ЛС
    waiting_for_password[user.id] = 'root'
    await context.bot.send_message(
        chat_id=user.id,
        text="👑 *Введите root пароль:*",
        parse_mode='Markdown'
    )

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка паролей в ЛС"""
    user = update.effective_user
    password = update.message.text
    
    if user.id not in waiting_for_password:
        return
    
    auth_type = waiting_for_password[user.id]
    
    # Удаляем сообщение с паролем
    try:
        await update.message.delete()
    except:
        pass
    
    if auth_type == 'admin':
        if password == ADMIN_PASSWORD:
            admins.add(user.id)
            await update.message.reply_text(
                f"✅ *Добро пожаловать в админ-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
            logger.info(f"👤 Пользователь {user.first_name} ({user.id}) вошел как админ")
        else:
            await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
    
    elif auth_type == 'root':
        if password == ROOT_PASSWORD:
            root_users.add(user.id)
            admins.add(user.id)
            await update.message.reply_text(
                f"👑 *Добро пожаловать в root-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
            logger.info(f"👑 Пользователь {user.first_name} ({user.id}) вошел как root")
        else:
            await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
    
    # Удаляем из ожидания
    del waiting_for_password[user.id]

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление админа по @username"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            await update.message.reply_text("❌ *Только root может добавлять админов!*", parse_mode='Markdown')
            return
            
        if not context.args:
            await update.message.reply_text("❌ *Укажи @username пользователя*", parse_mode='Markdown')
            return
        
        username_input = context.args[0].replace('@', '')
        
        # В реальном боте нужно найти user_id по username
        # Покажем инструкцию как найти user_id
        await update.message.reply_text(
            f"🔍 *Для добавления админа нужно найти user_id*\n\n"
            f"Username: @{username_input}\n\n"
            f"*Как найти user_id:*\n"
            f"1. Попросите пользователя написать боту\n"
            f"2. Посмотрите user_id в логах\n"
            f"3. Используйте команду: `/addadmin_userid 123456789`",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка добавления админа!*", parse_mode='Markdown')

async def add_admin_userid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление админа по user_id (скрытая команда)"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            await update.message.reply_text("❌ *Только root может добавлять админов!*", parse_mode='Markdown')
            return
            
        if not context.args:
            await update.message.reply_text("❌ *Укажи user_id пользователя*", parse_mode='Markdown')
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ *user_id должен быть числом!*", parse_mode='Markdown')
            return
        
        if target_user_id in root_users:
            await update.message.reply_text("❌ *Нельзя добавить root пользователя как админа!*", parse_mode='Markdown')
            return
        
        admins.add(target_user_id)
        
        await update.message.reply_text(
            f"✅ *Пользователь {target_user_id} добавлен в админы!*",
            parse_mode='Markdown'
        )
        
        logger.info(f"👑 Root {user.first_name} добавил админа {target_user_id}")
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка добавления админа!*", parse_mode='Markdown')

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление админа по @username"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            await update.message.reply_text("❌ *Только root может удалять админов!*", parse_mode='Markdown')
            return
            
        if not context.args:
            await update.message.reply_text("❌ *Укажи @username админа*", parse_mode='Markdown')
            return
        
        username_input = context.args[0].replace('@', '')
        
        await update.message.reply_text(
            f"🔍 *Для удаления админа нужно знать его user_id*\n\n"
            f"Используйте команду: `/removeadmin_userid 123456789`\n\n"
            f"*Список текущих админов:*\n"
            f"{await get_admins_list()}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка удаления админа!*", parse_mode='Markdown')

async def remove_admin_userid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление админа по user_id (скрытая команда)"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            await update.message.reply_text("❌ *Только root может удалять админов!*", parse_mode='Markdown')
            return
            
        if not context.args:
            await update.message.reply_text("❌ *Укажи user_id админа*", parse_mode='Markdown')
            return
        
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ *user_id должен быть числом!*", parse_mode='Markdown')
            return
        
        if target_user_id in root_users:
            await update.message.reply_text("❌ *Нельзя удалить root пользователя!*", parse_mode='Markdown')
            return
        
        if target_user_id not in admins:
            await update.message.reply_text(f"❌ *Пользователь {target_user_id} не является админом!*", parse_mode='Markdown')
            return
        
        admins.remove(target_user_id)
        
        await update.message.reply_text(
            f"🗑️ *Пользователь {target_user_id} удален из админов!*",
            parse_mode='Markdown'
        )
        
        logger.info(f"👑 Root {user.first_name} удалил админа {target_user_id}")
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка удаления админа!*", parse_mode='Markdown')

async def get_admins_list():
    """Получить список админов"""
    if not admins:
        return "📭 Админов нет"
    
    text = ""
    for i, admin_id in enumerate(admins, 1):
        is_root_user = "👑 " if admin_id in root_users else ""
        text += f"{i}. {is_root_user}`{admin_id}`\n"
    
    return text

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список админов"""
    try:
        user = update.effective_user
        
        if not is_root(user.id):
            await update.message.reply_text("❌ *Только root может просматривать список админов!*", parse_mode='Markdown')
            return
        
        text = "👥 *СПИСОК АДМИНОВ*\n\n"
        text += await get_admins_list()
        text += f"\n👑 *Root пользователей:* {len(root_users)}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')

# ... остальные функции (create_event, go_command, ex_command, kapt_command, kick_command, delete_event_command) остаются без изменений ...

async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 8:
            await update.message.reply_text(
                "🎯 *Создание капта*\n\n"
                "📋 *Формат:*\n"
                "`/create код название слоты дата время оружие хил роль`\n\n"
                "📝 *Пример:*\n"
                "`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`",
                parse_mode='Markdown'
            )
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
            await update.message.reply_text(f"⚠️ *Капт {event_code} уже существует!*", parse_mode='Markdown')
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
        
        message = await update.message.reply_text(event_text, parse_mode='Markdown')
        
        # Пытаемся закрепить сообщение
        try:
            await message.pin()
        except Exception as e:
            logger.warning(f"Не удалось закрепить сообщение: {e}")
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка создания капта!*", parse_mode='Markdown')

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            return
        
        event = events[event_code]
        
        if len(event['participants']) >= int(event['slots']):
            await update.message.reply_text("🚫 *Нет свободных слотов!*", parse_mode='Markdown')
            return
        
        user_already_registered = any(participant['user_id'] == user.id for participant in event['participants'])
        if user_already_registered:
            await update.message.reply_text("⚠️ *Ты уже в капте!*", parse_mode='Markdown')
            return
        
        # Получаем username или first_name если username нет
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
        
        await update.message.reply_text(
            f"✅ *{display_name} записан в капт!*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка записи!*", parse_mode='Markdown')

async def ex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            return
        
        event = events[event_code]
        
        participant_index = None
        for i, participant in enumerate(event['participants']):
            if participant['user_id'] == user.id:
                participant_index = i
                break
        
        if participant_index is None:
            await update.message.reply_text("⚠️ *Ты не в этом капте!*", parse_mode='Markdown')
            return
        
        removed_participant = event['participants'].pop(participant_index)
        free_slots = int(event['slots']) - len(event['participants'])
        
        await update.message.reply_text(
            f"❌ *{removed_participant['display_name']} вышел из капта*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка выхода!*", parse_mode='Markdown')

async def kapt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not events:
            await update.message.reply_text("📭 *Активных каптов нет*", parse_mode='Markdown')
            return
        
        text = "🎯 *АКТИВНЫЕ КАПТЫ*\n\n"
        
        for code, event in events.items():
            free_slots = int(event['slots']) - len(event['participants'])
            
            # Формируем список участников с никами
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
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кик участника по нику"""
    try:
        user = update.effective_user
        
        if not is_admin(user.id):
            await update.message.reply_text("❌ *Нет прав админа!*", parse_mode='Markdown')
            return
            
        if len(context.args) < 2:
            await update.message.reply_text("❌ *Формат:* `/kick @username код`", parse_mode='Markdown')
            return
        
        username_input = context.args[0]
        event_code = context.args[1]
        
        if event_code not in events:
            await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            return
        
        event = events[event_code]
        
        # Ищем участника по username (с @ или без)
        participant_index = None
        removed_participant = None
        
        for i, participant in enumerate(event['participants']):
            # Убираем @ из ввода для сравнения
            clean_input = username_input.replace('@', '').lower()
            
            # Проверяем username (без @) или display_name (с @)
            participant_username = participant['username'] or ""
            participant_display = participant['display_name'].replace('@', '').lower()
            
            if (participant_username.lower() == clean_input) or (participant_display == clean_input):
                participant_index = i
                removed_participant = participant
                break
        
        if participant_index is None:
            await update.message.reply_text(f"❌ *Участник {username_input} не найден в капте {event_code}!*", parse_mode='Markdown')
            return
        
        # Удаляем участника
        event['participants'].pop(participant_index)
        free_slots = int(event['slots']) - len(event['participants'])
        
        await update.message.reply_text(
            f"🚫 *Участник {removed_participant['display_name']} исключен из капта!*\n\n"
            f"🎯 **{event['name']}**\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots} слотов",
            parse_mode='Markdown'
        )
        
        logger.info(f"👤 Админ {user.first_name} кикнул {removed_participant['display_name']} из капта {event_code}")
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка кика!*", parse_mode='Markdown')

async def delete_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление капта"""
    try:
        user = update.effective_user
        
        if not is_admin(user.id):
            await update.message.reply_text("❌ *Нет прав админа!*", parse_mode='Markdown')
            return
            
        if not context.args:
            await update.message.reply_text("❌ *Укажи код капта!*", parse_mode='Markdown')
            return
        
        event_code = context.args[0]
        
        if event_code not in events:
            await update.message.reply_text("❌ *Капт не найден!*", parse_mode='Markdown')
            return
        
        # Удаляем капт
        del events[event_code]
        
        await update.message.reply_text(
            f"🗑️ *Капт {event_code} удален!*",
            parse_mode='Markdown'
        )
        
        logger.info(f"👤 Админ {user.first_name} удалил капт {event_code}")
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка удаления!*", parse_mode='Markdown')

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
    application.add_handler(CommandHandler("addadmin_userid", add_admin_userid))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("removeadmin_userid", remove_admin_userid))
    application.add_handler(CommandHandler("listadmins", list_admins))
    application.add_handler(CommandHandler("create", create_event))
    application.add_handler(CommandHandler("go", go_command))
    application.add_handler(CommandHandler("ex", ex_command))
    application.add_handler(CommandHandler("kapt", kapt_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("del", delete_event_command))
    
    # Обработчик паролей в ЛС
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password))
    
    print("🎮 CAPT BOT запущен!")
    print("🛠️ Создатель: ChikenXa")
    print("🔐 Пароль админа: 24680")
    print("👑 Пароль root: 1508")
    print("💬 Пароли теперь запрашиваются в ЛС!")
    
    application.run_polling()

if __name__ == "__main__":
    main()
