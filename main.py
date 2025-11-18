import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Твой токен
BOT_TOKEN = os.environ.get("8186945089:AAHAx_pWrtKBYEh61NSsWtiAEofCeP37tH4")

# Хранилище данных
events = {}
admins = set()

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
        text += "• `/kick @user код` - кикнуть игрока\n"
        text += "• `/del код` - удалить капт\n"
        text += "• `/aclean` - очистить все капты\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("🔐 *Требуется пароль*", parse_mode='Markdown')
            return
        
        password = context.args[0]
        user = update.effective_user
        
        if password == "1512":
            admins.add(user.id)
            await update.message.reply_text(
                f"✅ *Добро пожаловать в админ-панель, {user.first_name}!*",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ *Неверный пароль!*", parse_mode='Markdown')
            
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка входа!*", parse_mode='Markdown')

def is_admin(user_id):
    return user_id in admins

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
        
        await update.message.reply_text(event_text, parse_mode='Markdown')
        
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
        
        if user.first_name in event['participants']:
            await update.message.reply_text("⚠️ *Ты уже в капте!*", parse_mode='Markdown')
            return
        
        event['participants'].append(user.first_name)
        free_slots = int(event['slots']) - len(event['participants'])
        
        await update.message.reply_text(
            f"✅ *{user.first_name} записан в капт!*\n\n"
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
        
        if user.first_name not in event['participants']:
            await update.message.reply_text("⚠️ *Ты не в этом капте!*", parse_mode='Markdown')
            return
        
        event['participants'].remove(user.first_name)
        free_slots = int(event['slots']) - len(event['participants'])
        
        await update.message.reply_text(
            f"❌ *{user.first_name} вышел из капта*\n\n"
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
            
            text += (
                f"🔢 **Код:** `{code}`\n"
                f"🎯 **{event['name']}**\n"
                f"📅 **Когда:** {event['date']} {event['time']} МСК\n"
                f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
                f"🎫 **Свободно:** {free_slots} слотов\n"
                f"⚔️ **Оружие:** {event['weapon_type']}\n"
                f"❤️ **Хил:** {event['heal']}\n"
                f"🛡️ **Роль:** {event['role']}\n\n"
                f"⚡ `/go {code}`  •  ❌ `/ex {code}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text("❌ *Ошибка!*", parse_mode='Markdown')

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CommandHandler("alogin", admin_login))
    application.add_handler(CommandHandler("create", create_event))
    application.add_handler(CommandHandler("go", go_command))
    application.add_handler(CommandHandler("ex", ex_command))
    application.add_handler(CommandHandler("kapt", kapt_command))
    
    print("🎮 CAPT BOT запущен на Railway!")
    print("🛠️ Создатель: ChikenXa")
    
    application.run_polling()

if __name__ == "__main__":
    main()
