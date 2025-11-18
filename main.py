import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from flask import Flask
import threading

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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    exit(1)

events = {}
admins = set()
root_users = set()
ADMIN_PASSWORD = "24680"
ROOT_PASSWORD = "1508"

bot_messages = []

MOSCOW_UTC_OFFSET = 3

def get_moscow_time():
    return datetime.utcnow() + timedelta(hours=MOSCOW_UTC_OFFSET)

async def cleanup_bot_messages(application):
    while True:
        try:
            now = get_moscow_time()
            if now.hour == 6 and now.minute == 0:
                logger.info("🕕 Очистка сообщений...")
                
                for chat_id, message_id in bot_messages:
                    try:
                        await application.bot.delete_message(chat_id, message_id)
                        await asyncio.sleep(0.1)
                    except:
                        pass
                
                bot_messages.clear()
                logger.info("✅ Очистка завершена")
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(60)
        except:
            await asyncio.sleep(60)

async def loginadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            msg = await update.message.reply_text("🔐 */loginadmin пароль*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        if context.args[0] == ADMIN_PASSWORD:
            admins.add(update.effective_user.id)
            msg = await update.message.reply_text("✅ *Админ авторизован*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
        else:
            msg = await update.message.reply_text("❌ *Неверный пароль*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def loginroot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            msg = await update.message.reply_text("👑 */loginroot пароль*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        if context.args[0] == ROOT_PASSWORD:
            user_id = update.effective_user.id
            root_users.add(user_id)
            admins.add(user_id)
            msg = await update.message.reply_text("👑 *Root авторизован*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
        else:
            msg = await update.message.reply_text("❌ *Неверный пароль*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "👋 *CAPT BOT*\n\n"
        "📱 *Команды:*\n"
        "• /start - начать\n"
        "• /commands - все команды\n"
        "• /create - создать капт\n"
        "• /kapt - список каптов\n"
        "• /go [код] - записаться\n"
        "• /ex [код] - выйти\n\n"
        "⚡ *Пример:*\n"
        "`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`",
        parse_mode='Markdown'
    )
    bot_messages.append((msg.chat_id, msg.message_id))

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in admins
    is_root = user.id in root_users
    
    text = "📋 *КОМАНДЫ*\n\n"
    text += "👥 *Для всех:*\n"
    text += "• /start - начать\n"
    text += "• /commands - команды\n"
    text += "• /kapt - капты\n"
    text += "• /go [код] - записаться\n"
    text += "• /ex [код] - выйти\n\n"
    text += "🎯 *Создать капт:*\n"
    text += "`/create код название слоты дата время оружие хил роль`\n\n"
    
    if is_admin or is_root:
        text += "🛠️ *Админ:*\n"
        text += "• /loginadmin пароль\n"
        text += "• /kick @user код\n"
        text += "• /del код\n\n"
    
    if is_root:
        text += "👑 *Root:*\n"
        text += "• /loginroot пароль\n"
        text += "• /addadmin user_id\n"
        text += "• /removeadmin user_id\n\n"
    
    msg = await update.message.reply_text(text, parse_mode='Markdown')
    bot_messages.append((msg.chat_id, msg.message_id))

async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 8:
            msg = await update.message.reply_text(
                "🎯 *Создать капт:*\n"
                "`/create код название слоты дата время оружие хил роль`\n\n"
                "📝 *Пример:*\n"
                "`/create 1 Рейд 5 20.11 21:30 Лук Да Защита`",
                parse_mode='Markdown'
            )
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code, name, slots, date, time, weapon, heal, role = context.args[:8]
        user = update.effective_user
        
        if event_code in events:
            msg = await update.message.reply_text(f"⚠️ *Капт {event_code} уже есть*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        events[event_code] = {
            'name': name, 'slots': slots, 'date': date, 'time': time,
            'weapon_type': weapon, 'heal': heal, 'role': role,
            'participants': [], 'author': user.first_name, 'author_id': user.id
        }
        
        event_text = (
            f"🎯 *НОВЫЙ КАПТ!*\n\n"
            f"🔢 **Код:** `{event_code}`\n"
            f"📝 **{name}**\n"
            f"🎫 **Слоты:** {slots}\n"
            f"📅 **Дата:** {date}\n"
            f"⏰ **Время:** {time} МСК\n"
            f"⚔️ **Оружие:** {weapon}\n"
            f"❤️ **Хил:** {heal}\n"
            f"🛡️ **Роль:** {role}\n"
            f"👤 **Создатель:** {user.first_name}\n\n"
            f"⚡ /go {event_code}  ❌ /ex {event_code}"
        )
        
        msg = await update.message.reply_text(event_text, parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))
        
        try:
            await msg.pin()
        except:
            pass
        
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            msg = await update.message.reply_text("❌ *Укажи код*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event = events[event_code]
        
        if len(event['participants']) >= int(event['slots']):
            msg = await update.message.reply_text("🚫 *Нет слотов*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        if any(p['user_id'] == user.id for p in event['participants']):
            msg = await update.message.reply_text("⚠️ *Уже в капте*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        display_name = f"@{user.username}" if user.username else user.first_name
        event['participants'].append({
            'user_id': user.id, 'username': user.username,
            'display_name': display_name, 'first_name': user.first_name
        })
        
        free_slots = int(event['slots']) - len(event['participants'])
        msg = await update.message.reply_text(
            f"✅ *{display_name} записан!*\n\n"
            f"🎯 **{event['name']}**\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots}",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def ex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            msg = await update.message.reply_text("❌ *Укажи код*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code = context.args[0]
        user = update.effective_user
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event = events[event_code]
        participant = next((p for p in event['participants'] if p['user_id'] == user.id), None)
        
        if not participant:
            msg = await update.message.reply_text("⚠️ *Не в капте*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event['participants'] = [p for p in event['participants'] if p['user_id'] != user.id]
        free_slots = int(event['slots']) - len(event['participants'])
        
        msg = await update.message.reply_text(
            f"❌ *{participant['display_name']} вышел*\n\n"
            f"🎯 **{event['name']}**\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots}",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def kapt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not events:
            msg = await update.message.reply_text("📭 *Нет каптов*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        text = "🎯 *КАПТЫ*\n\n"
        for code, event in events.items():
            free_slots = int(event['slots']) - len(event['participants'])
            participants = "\n".join([f"{i}. {p['display_name']}" for i, p in enumerate(event['participants'], 1)])
            
            text += (
                f"🔢 **Код:** `{code}`\n"
                f"🎯 **{event['name']}**\n"
                f"📅 **Когда:** {event['date']} {event['time']} МСК\n"
                f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
                f"🎫 **Свободно:** {free_slots}\n"
            )
            if event['participants']:
                text += f"👥 **Список:**\n{participants}\n"
            text += f"⚡ /go {code}  ❌ /ex {code}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        
        msg = await update.message.reply_text(text, parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            msg = await update.message.reply_text("❌ *Нет прав*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        if len(context.args) < 2:
            msg = await update.message.reply_text("❌ */kick @user код*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        username, event_code = context.args[0].replace('@', ''), context.args[1]
        
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event = events[event_code]
        participant = next((p for p in event['participants'] if p['username'] == username), None)
        
        if not participant:
            msg = await update.message.reply_text("❌ *Игрок не найден*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event['participants'] = [p for p in event['participants'] if p['username'] != username]
        free_slots = int(event['slots']) - len(event['participants'])
        
        msg = await update.message.reply_text(
            f"🚫 *{participant['display_name']} кикнут*\n\n"
            f"👥 **Участники:** {len(event['participants'])}/{event['slots']}\n"
            f"🎫 **Свободно:** {free_slots}",
            parse_mode='Markdown'
        )
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

async def delete_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            msg = await update.message.reply_text("❌ *Нет прав*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        if not context.args:
            msg = await update.message.reply_text("❌ */del код*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        event_code = context.args[0]
        if event_code not in events:
            msg = await update.message.reply_text("❌ *Капт не найден*", parse_mode='Markdown')
            bot_messages.append((msg.chat_id, msg.message_id))
            return
        
        del events[event_code]
        msg = await update.message.reply_text(f"🗑️ *Капт {event_code} удален*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))
        
    except:
        msg = await update.message.reply_text("❌ *Ошибка*", parse_mode='Markdown')
        bot_messages.append((msg.chat_id, msg.message_id))

def is_admin(user_id):
    return user_id in admins

def is_root(user_id):
    return user_id in root_users

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CommandHandler("loginadmin", loginadmin))
    application.add_handler(CommandHandler("loginroot", loginroot))
    application.add_handler(CommandHandler("create", create_event))
    application.add_handler(CommandHandler("go", go_command))
    application.add_handler(CommandHandler("ex", ex_command))
    application.add_handler(CommandHandler("kapt", kapt_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("del", delete_event_command))
    
    application.job_queue.run_once(
        lambda context: asyncio.create_task(cleanup_bot_messages(application)), 
        when=0
    )
    
    print("🎮 CAPT BOT запущен!")
    print("⏰ Очистка в 6:00 по МСК")
    print("🔐 /loginadmin 24680")
    print("👑 /loginroot 1508")
    
    application.run_polling()

if __name__ == "__main__":
    main()
