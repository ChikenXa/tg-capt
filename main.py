import os
import logging
import json
import random
import asyncio
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread
import time

# ==================== KEEP ALIVE SYSTEM ====================
keep_alive_app = Flask(__name__)

@keep_alive_app.route('/')
def home():
    return "🤖 ДанилBot работает 24/7! 🚀"

@keep_alive_app.route('/health')
def health_check():
    return "✅ OK", 200

def run_keep_alive():
    keep_alive_app.run(host='0.0.0.0', port=8080)

def auto_ping():
    while True:
        try:
            repl_slug = os.environ.get('REPL_SLUG', 'danil-bot')
            repl_owner = os.environ.get('REPL_OWNER', 'user')
            url = f"https://{repl_slug}.{repl_owner}.repl.co"
            requests.get(url, timeout=10)
            print(f"🟢 Пинг: {datetime.now().strftime('%H:%M:%S')}")
        except:
            print(f"⚠️ Пинг не удался: {datetime.now().strftime('%H:%M:%S')}")
        time.sleep(300)

Thread(target=run_keep_alive, daemon=True).start()
Thread(target=auto_ping, daemon=True).start()
print("🔧 Keep-alive система запущена!")
# ==================== END KEEP ALIVE SYSTEM ====================

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN не найден!")
    exit(1)

# Конфигурация особняков
HACK_SCHEDULE = {
    "🏠 Западный особняк": {"day": 2, "hour": 18, "minute": 0},
    "🏠 Северный особняк": {"day": 4, "hour": 18, "minute": 0},
    "⚡ База Паши Пэла": {"day": 5, "hour": 18, "minute": 0},
    "🏠 Центральный особняк": {"day": 6, "hour": 18, "minute": 0},
}

class DanilBot:
    def __init__(self, token: str):
        self.token = token
        self.alliances = self.load_data("alliances")
        self.admin_users = self.load_data("admin_users")
        self.root_users = self.load_data("root_users")
        self.events = self.load_data("events")
        self.alert_chats = set()
        self.waiting_for_password = set()
        self.start_time = time.time()
        self.event_messages = {}
        self.bot_messages = []
        
        # Пароли
        self.ADMIN_PASSWORD = "24680"
        self.ROOT_PASSWORD = "1508"

    def load_data(self, data_type: str):
        """Загрузка данных из файла"""
        try:
            filename = f"{data_type}.json"
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки {data_type}: {e}")
            return {}

    def save_data(self, data_type: str, data):
        """Сохранение данных в файл"""
        try:
            filename = f"{data_type}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения {data_type}: {e}")
            return False

    def is_admin(self, user_id: int) -> bool:
        """Проверка прав админа (root тоже админы)"""
        return str(user_id) in self.admin_users or str(user_id) in self.root_users

    def is_root(self, user_id: int) -> bool:
        """Проверка root прав"""
        return str(user_id) in self.root_users

    def generate_alliance_code(self):
        """Генерация кода союза"""
        while True:
            code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
            if not any(alliance.get('code') == code for alliance in self.alliances.values()):
                return code

    def get_moscow_time(self):
        """Получить московское время"""
        return datetime.utcnow() + timedelta(hours=3)

    # ==================== КРАСИВЫЕ КОМАНДЫ ====================
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню"""
        user = update.effective_user
        self.alert_chats.add(update.effective_chat.id)
        
        welcome_text = (
            "✨ <b>🤖 ДАНИЛБОТ АКТИВИРОВАН</b> ✨\n\n"
            
            "🕐 <b>АВТОМАТИЧЕСКИЕ ФУНКЦИИ:</b>\n"
            "├ 🌅 <b>10:00</b> - Утренняя сводка\n"
            "├ 📢 <b>17:30</b> - Напоминание об особе\n" 
            "├ 🚨 <b>18:00</b> - Оповещения о особах\n"
            "├ 📍 <b>14:00</b> - Ежедневные капты\n"
            "├ 🌙 <b>23:00</b> - Ночной режим\n"
            "└ 🧹 <b>06:00</b> - Очистка системы\n\n"
            
            "🎯 <b>ОСНОВНЫЕ КОМАНДЫ:</b>\n"
            "├ /help - Все команды\n"
            "├ /hacks - Расписание особ\n"
            "├ /next - Ближайшая особа\n"
            "├ /alliances - Список союзов\n"
            "├ /kapt - Активные капты\n"
            "├ /create - Создать капт\n"
            "├ /pong - Проверка работы\n"
            "└ /admin - Админ-панель\n\n"
            
            "🔒 <b>Бот работает только в группах!</b>\n\n"
            "👨‍💻 <b>Разработано Данилом</b> | @ChikenXa"
        )
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Помощь по командам"""
        help_text = (
            "📚 <b>ПОМОЩЬ ПО КОМАНДАМ</b>\n\n"
            
            "🎮 <b>ОСНОВНЫЕ КОМАНДЫ:</b>\n"
            "├ /start - Главное меню\n"
            "├ /help - Эта справка\n" 
            "├ /pong - Проверка работы\n"
            "├ /hacks - Расписание особняков\n"
            "├ /next - Ближайшая особа\n"
            "├ /alliances - Список союзов\n"
            "└ /kapt - Активные капты\n\n"
            
            "⚔️ <b>СИСТЕМА КАПТОВ:</b>\n"
            "└ /create код название слоты дата время оружие хил роль\n"
            "  📝 <i>Пример: /create 1 Рейд 5 20.11 21:30 Лук Да Защита</i>\n\n"
            
            "🛡️ <b>АДМИН СИСТЕМА:</b>\n"
            "├ /admin - Админ-панель\n"
            "├ /add_alliance Название - Добавить союз\n"
            "├ /remove_alliance КОД - Удалить союз\n"
            "├ /clear_alliances - Очистить союзы\n"
            "├ /del код - Удалить капт\n"
            "├ /admin_stats - Статистика\n"
            "├ /admin_list - Список админов\n"
            "├ /test_alert - Тест оповещение\n"
            "└ /reload - Перезагрузить данные\n\n"
            
            "👑 <b>ROOT КОМАНДЫ:</b>\n"
            "├ /add_admin @username - Добавить админа\n"
            "└ /remove_admin @username - Удалить админа\n\n"
            
            "🔔 <b>АВТО-ОПОВЕЩЕНИЯ:</b>\n"
            "└ См. расписание в /start\n\n"
            
            "💡 <b>Для помощи:</b> @ChikenXa"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def pong(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка работы бота"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
            
            start_time = time.time()
            message = await update.message.reply_text("🏓 <b>Проверка связи...</b>", parse_mode=ParseMode.HTML)
            end_time = time.time()
            
            ping_time = round((end_time - start_time) * 1000, 2)
            uptime = time.time() - self.start_time
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            minutes = int((uptime % 3600) // 60)
            
            pong_text = (
                f"✅ <b>СИСТЕМА РАБОТАЕТ</b>\n\n"
                f"⚡ <b>Пинг:</b> {ping_time} мс\n"
                f"⏱️ <b>Аптайм:</b> {days}д {hours}ч {minutes}м\n"
                f"👥 <b>Чатов:</b> {len(self.alert_chats)}\n"
                f"🤝 <b>Союзов:</b> {len(self.alliances)}\n"
                f"🎯 <b>Каптов:</b> {len(self.events)}\n\n"
                f"🕐 <b>Время МСК:</b> {self.get_moscow_time().strftime('%H:%M:%S')}"
            )
            
            await message.edit_text(pong_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в pong: {e}")

    # ==================== СИСТЕМА КАПТОВ ====================
    
    async def create_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создать капт"""
        try:
            if len(context.args) < 8:
                help_text = (
                    "🎯 <b>СОЗДАНИЕ КАПТА</b>\n\n"
                    "📋 <b>Формат команды:</b>\n"
                    "<code>/create код название слоты дата время оружие хил роль</code>\n\n"
                    "📝 <b>Пример:</b>\n"
                    "<code>/create 1 Рейд 5 20.11 21:30 Лук Да Защита</code>\n\n"
                    "🔍 <b>Параметры:</b>\n"
                    "├ <b>код</b> - уникальный номер капта\n"
                    "├ <b>название</b> - название события\n" 
                    "├ <b>слоты</b> - количество участников\n"
                    "├ <b>дата</b> - в формате ДД.ММ\n"
                    "├ <b>время</b> - в формате ЧЧ:ММ\n"
                    "├ <b>оружие</b> - тип оружия\n"
                    "├ <b>хил</b> - наличие лечения\n"
                    "└ <b>роль</b> - основная роль\n"
                )
                message = await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
                self.bot_messages.append((message.chat_id, message.message_id, time.time()))
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
            
            if event_code in self.events:
                message = await update.message.reply_text(
                    f"⚠️ <b>Капт {event_code} уже существует!</b>", 
                    parse_mode=ParseMode.HTML
                )
                self.bot_messages.append((message.chat_id, message.message_id, time.time()))
                return
            
            self.events[event_code] = {
                'name': name,
                'slots': slots,
                'date': date,
                'time': time_str,
                'weapon_type': weapon_type,
                'heal': heal,
                'role': role,
                'author': user.first_name,
                'author_id': user.id,
                'created_at': datetime.now().isoformat()
            }
            
            event_text = (
                f"🎯 <b>НОВЫЙ КАПТ СОЗДАН!</b>\n\n"
                f"🔢 <b>Код:</b> <code>{event_code}</code>\n"
                f"📝 <b>Название:</b> {name}\n"
                f"🎫 <b>Слоты:</b> {slots}\n"
                f"📅 <b>Дата:</b> {date}\n"
                f"⏰ <b>Время:</b> {time_str} МСК\n"
                f"⚔️ <b>Оружие:</b> {weapon_type}\n"
                f"❤️ <b>Хил:</b> {heal}\n"
                f"🛡️ <b>Роль:</b> {role}\n"
                f"👤 <b>Создатель:</b> {user.first_name}\n\n"
                f"💡 <i>Система записи отключена</i>\n"
                f"📞 <i>Связывайтесь с создателем напрямую</i>"
            )
            
            message = await update.message.reply_text(event_text, parse_mode=ParseMode.HTML)
            
            # Сохраняем ID сообщения
            self.event_messages[event_code] = (message.chat_id, message.message_id)
            self.bot_messages.append((message.chat_id, message.message_id, time.time()))
            
            # Закрепляем сообщение
            await self.pin_event_message(context.application, message.chat_id, message.message_id)
            
            self.save_data("events", self.events)
            
        except Exception as e:
            logger.error(f"Ошибка создания капта: {e}")
            message = await update.message.reply_text("❌ <b>Ошибка создания капта!</b>", parse_mode=ParseMode.HTML)
            self.bot_messages.append((message.chat_id, message.message_id, time.time()))

    async def kapt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все капты"""
        try:
            if not self.events:
                message = await update.message.reply_text(
                    "📭 <b>Активных каптов нет</b>\n\n"
                    "💡 <i>Создайте первый капт командой /create</i>", 
                    parse_mode=ParseMode.HTML
                )
                self.bot_messages.append((message.chat_id, message.message_id, time.time()))
                return
            
            text = "🎯 <b>АКТИВНЫЕ КАПТЫ</b>\n\n"
            
            for code, event in self.events.items():
                text += (
                    f"🔢 <b>Код:</b> <code>{code}</code>\n"
                    f"🎯 <b>{event['name']}</b>\n"
                    f"📅 <b>Когда:</b> {event['date']} {event['time']} МСК\n"
                    f"🎫 <b>Слоты:</b> {event['slots']}\n"
                    f"⚔️ <b>Оружие:</b> {event['weapon_type']}\n"
                    f"❤️ <b>Хил:</b> {event['heal']}\n"
                    f"🛡️ <b>Роль:</b> {event['role']}\n"
                    f"👤 <b>Создатель:</b> {event['author']}\n"
                    f"────────────────────\n\n"
                )
            
            message = await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            self.bot_messages.append((message.chat_id, message.message_id, time.time()))
            
        except Exception as e:
            message = await update.message.reply_text("❌ <b>Ошибка!</b>", parse_mode=ParseMode.HTML)
            self.bot_messages.append((message.chat_id, message.message_id, time.time()))

    # ==================== СИСТЕМА ОСОБНЯКОВ ====================
    
    async def show_hacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать расписание особняков"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
            
            schedule_text = "📅 <b>РАСПИСАНИЕ ОСОБНЯКОВ</b>\n\n"
            
            days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            
            for location, schedule in HACK_SCHEDULE.items():
                day_name = days[schedule["day"]]
                schedule_text += f"🏰 <b>{location}</b>\n   📅 {day_name} - {schedule['hour']:02d}:{schedule['minute']:02d}\n\n"
            
            await update.message.reply_text(schedule_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в show_hacks: {e}")

    async def next_hack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ближайшая особа"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
            
            closest = self.get_next_hack()
            
            if closest:
                next_text = (
                    f"🎯 <b>БЛИЖАЙШАЯ ОСОБА</b>\n\n"
                    f"🏰 <b>{closest['location']}</b>\n"
                    f"📅 <b>Когда:</b> {closest['when']}\n"
                    f"⏱️ <b>Осталось:</b> {closest['time_left']}\n\n"
                    f"💡 <i>Следующая особа через {closest['time_left']}</i>"
                )
            else:
                next_text = "❌ <b>Не удалось определить ближайшую особу</b>"
            
            await update.message.reply_text(next_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в next_hack: {e}")

    def get_next_hack(self):
        """Получить ближайшую особу"""
        now = self.get_moscow_time()
        closest = None
        
        for location, schedule in HACK_SCHEDULE.items():
            days_ahead = schedule["day"] - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            
            next_date = now + timedelta(days=days_ahead)
            next_time = next_date.replace(
                hour=schedule["hour"], 
                minute=schedule["minute"], 
                second=0, 
                microsecond=0
            )
            
            if not closest or next_time < closest['time']:
                time_left = next_time - now
                hours_left = time_left.total_seconds() // 3600
                minutes_left = (time_left.total_seconds() % 3600) // 60
                
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                day_name = days[next_time.weekday()]
                
                closest = {
                    'location': location,
                    'time': next_time,
                    'when': f"{day_name} {next_time.strftime('%d.%m.%Y %H:%M')}",
                    'time_left': f"{int(hours_left)}ч {int(minutes_left)}м"
                }
        
        return closest

    # ==================== СИСТЕМА СОЮЗОВ ====================
    
    async def show_alliances(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать союзы"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
            
            if not self.alliances:
                await update.message.reply_text(
                    "🤝 <b>Активных союзов нет</b>\n\n"
                    "💡 <i>Добавьте первый союз через админ-панель</i>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            alliances_text = "🤝 <b>АКТИВНЫЕ СОЮЗЫ</b>\n\n"
            
            for alliance_data in self.alliances.values():
                code = alliance_data.get('code', 'N/A')
                name = alliance_data.get('name', 'Без названия')
                created = alliance_data.get('created', 'N/A')
                
                alliances_text += f"✅ <b>{name}</b>\n"
                alliances_text += f"   🔐 <b>Код:</b> <code>{code}</code>\n"
                alliances_text += f"   📅 <b>Создан:</b> {created}\n\n"
            
            await update.message.reply_text(alliances_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в show_alliances: {e}")

    # ==================== УЛУЧШЕННАЯ АДМИН СИСТЕМА ====================
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Админ-панель"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Админ-панель работает только в группах!")
                return
            
            user_id = update.effective_user.id
            
            if self.is_admin(user_id):
                await self.show_admin_panel(update)
            else:
                self.waiting_for_password.add(user_id)
                await update.message.reply_text(
                    "🔐 <b>ДОСТУП К АДМИН-ПАНЕЛИ</b>\n\n"
                    "📝 Введите пароль для доступа:",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Ошибка в admin_panel: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик сообщений с паролем"""
        try:
            if update.effective_chat.type == 'private':
                return
                
            if not update.message or not update.message.text:
                return
                
            user_id = update.effective_user.id
            text = update.message.text.strip()
            
            if user_id in self.waiting_for_password:
                if text == self.ADMIN_PASSWORD:
                    self.waiting_for_password.discard(user_id)
                    self.admin_users[str(user_id)] = {
                        'username': update.effective_user.username or "Нет username",
                        'first_name': update.effective_user.first_name or "Неизвестно",
                        'added_date': datetime.now().strftime('%d.%m.%Y %H:%M')
                    }
                    self.save_data("admin_users", self.admin_users)
                    
                    await update.message.reply_text("✅ <b>Доступ к админ-панели предоставлен!</b>", parse_mode=ParseMode.HTML)
                    await self.show_admin_panel(update)
                elif text == self.ROOT_PASSWORD:
                    self.waiting_for_password.discard(user_id)
                    self.root_users[str(user_id)] = {
                        'username': update.effective_user.username or "Нет username",
                        'first_name': update.effective_user.first_name or "Неизвестно",
                        'added_date': datetime.now().strftime('%d.%m.%Y %H:%M')
                    }
                    self.admin_users[str(user_id)] = self.root_users[str(user_id)]
                    self.save_data("root_users", self.root_users)
                    self.save_data("admin_users", self.admin_users)
                    
                    await update.message.reply_text("👑 <b>ROOT доступ предоставлен!</b>", parse_mode=ParseMode.HTML)
                    await self.show_admin_panel(update)
                else:
                    self.waiting_for_password.discard(user_id)
                    await update.message.reply_text("❌ <b>Неверный пароль!</b>", parse_mode=ParseMode.HTML)
                    
        except Exception as e:
            logger.error(f"Ошибка в handle_message: {e}")

    async def show_admin_panel(self, update: Update):
        """Показать админ-панель"""
        try:
            user_id = update.effective_user.id
            is_root_user = self.is_root(user_id)
            
            admin_text = "🛠️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
            
            if is_root_user:
                admin_text += "👑 <b>ROOT-доступ активирован</b>\n\n"
            
            admin_text += (
                "⚙️ <b>КОМАНДЫ УПРАВЛЕНИЯ:</b>\n"
                "├ /add_alliance Название - Добавить союз\n"
                "├ /remove_alliance КОД - Удалить союз\n"
                "├ /clear_alliances - Очистить все союзы\n"
                "├ /del код - Удалить капт\n"
                "├ /admin_stats - Статистика бота\n"
                "├ /admin_list - Список админов\n"
                "├ /test_alert - Тест оповещение\n"
                "└ /reload - Перезагрузить данные\n"
            )
            
            if is_root_user:
                admin_text += (
                    "\n👑 <b>ROOT КОМАНДЫ:</b>\n"
                    "├ /add_admin @username - Добавить админа\n"
                    "└ /remove_admin @username - Удалить админа\n"
                )
            
            await update.message.reply_text(admin_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в show_admin_panel: {e}")

    # ==================== ROOT КОМАНДЫ ====================
    
    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить админа (только root)"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            # ТОЛЬКО root может добавлять админов
            if not self.is_root(update.effective_user.id):
                await update.message.reply_text("❌ <b>Только root может добавлять админов!</b>", parse_mode=ParseMode.HTML)
                return
            
            if not context.args:
                await update.message.reply_text(
                    "📝 <b>Использование:</b>\n"
                    "<code>/add_admin @username</code>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            target = context.args[0]
            
            if not target.startswith('@'):
                await update.message.reply_text(
                    "❌ <b>Укажите @username (начинается с @)</b>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            username = target[1:]  # Убираем @
            
            # Ищем пользователя по username
            target_user_id = None
            target_user_info = None
            
            # Проверяем в каптах
            for event in self.events.values():
                for participant in event.get('participants', []):
                    if participant.get('username') == username:
                        target_user_id = participant['user_id']
                        target_user_info = participant
                        break
                if target_user_id:
                    break
            
            if not target_user_id:
                await update.message.reply_text(
                    f"❌ <b>Пользователь @{username} не найден!</b>\n\n"
                    f"💡 <i>Попросите человека написать боту любое сообщение</i>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            if target_user_id in self.root_users:
                await update.message.reply_text("❌ <b>Нельзя добавить root пользователя как админа!</b>", parse_mode=ParseMode.HTML)
                return
            
            if target_user_id in self.admin_users:
                await update.message.reply_text(f"⚠️ <b>Пользователь @{username} уже является админом!</b>", parse_mode=ParseMode.HTML)
                return
            
            self.admin_users[target_user_id] = {
                'username': username,
                'first_name': target_user_info.get('first_name', 'Unknown'),
                'added_by': update.effective_user.first_name,
                'added_date': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
            self.save_data("admin_users", self.admin_users)
            
            await update.message.reply_text(
                f"✅ <b>Пользователь @{username} добавлен в админы!</b>", 
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка добавления админа: {e}")
            await update.message.reply_text("❌ <b>Ошибка добавления админа!</b>", parse_mode=ParseMode.HTML)

    async def remove_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить админа (только root)"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            # ТОЛЬКО root может удалять админов
            if not self.is_root(update.effective_user.id):
                await update.message.reply_text("❌ <b>Только root может удалять админов!</b>", parse_mode=ParseMode.HTML)
                return
            
            if not context.args:
                await update.message.reply_text(
                    "📝 <b>Использование:</b>\n"
                    "<code>/remove_admin @username</code>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            target = context.args[0]
            
            if not target.startswith('@'):
                await update.message.reply_text(
                    "❌ <b>Укажите @username (начинается с @)</b>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            username = target[1:]
            
            # Ищем админа по username
            target_user_id = None
            for admin_id, admin_info in self.admin_users.items():
                if admin_info.get('username') == username:
                    target_user_id = admin_id
                    break
            
            if not target_user_id:
                await update.message.reply_text(f"❌ <b>Пользователь @{username} не является админом!</b>", parse_mode=ParseMode.HTML)
                return
            
            if target_user_id in self.root_users:
                await update.message.reply_text("❌ <b>Нельзя удалить root пользователя!</b>", parse_mode=ParseMode.HTML)
                return
            
            del self.admin_users[target_user_id]
            self.save_data("admin_users", self.admin_users)
            
            await update.message.reply_text(
                f"🗑️ <b>Пользователь @{username} удален из админов!</b>", 
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Ошибка удаления админа: {e}")
            await update.message.reply_text("❌ <b>Ошибка удаления админа!</b>", parse_mode=ParseMode.HTML)

    # ==================== АДМИН КОМАНДЫ ====================
    
    async def add_alliance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить союз"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            if not context.args:
                await update.message.reply_text(
                    "📝 <b>Использование:</b>\n"
                    "<code>/add_alliance Название союза</code>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            alliance_name = " ".join(context.args)
            alliance_code = self.generate_alliance_code()
            
            self.alliances[f"alliance_{int(time.time())}"] = {
                'name': alliance_name,
                'code': alliance_code,
                'created': datetime.now().strftime('%d.%m.%Y %H:%M'),
                'created_by': update.effective_user.first_name
            }
            
            self.save_data("alliances", self.alliances)
            
            success_text = (
                f"✅ <b>СОЮЗ ДОБАВЛЕН!</b>\n\n"
                f"🎯 <b>Название:</b> {alliance_name}\n"
                f"🔐 <b>Код:</b> <code>{alliance_code}</code>\n\n"
                f"💡 <i>Код можно использовать для идентификации</i>"
            )
            
            await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в add_alliance: {e}")

    async def remove_alliance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить союз"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            if not context.args:
                await update.message.reply_text(
                    "📝 <b>Использование:</b>\n"
                    "<code>/remove_alliance КОД</code>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            target_code = context.args[0].upper()
            
            for alliance_id, alliance_data in self.alliances.items():
                if alliance_data.get('code') == target_code:
                    alliance_name = alliance_data.get('name', 'Без названия')
                    del self.alliances[alliance_id]
                    self.save_data("alliances", self.alliances)
                    await update.message.reply_text(
                        f"✅ <b>СОЮЗ УДАЛЕН!</b>\n\n"
                        f"🗑️ <b>{alliance_name}</b> (<code>{target_code}</code>)", 
                        parse_mode=ParseMode.HTML
                    )
                    return
            
            await update.message.reply_text(f"❌ <b>Союз с кодом '{target_code}' не найден</b>", parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в remove_alliance: {e}")

    async def clear_alliances(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистить все союзы"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            count = len(self.alliances)
            self.alliances = {}
            self.save_data("alliances", self.alliances)
            
            await update.message.reply_text(
                f"🗑️ <b>УДАЛЕНО {count} СОЮЗОВ!</b>", 
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка в clear_alliances: {e}")

    async def delete_event_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить капт"""
        try:
            user = update.effective_user
            
            if not self.is_admin(user.id):
                await update.message.reply_text("❌ <b>Нет прав админа!</b>", parse_mode=ParseMode.HTML)
                return
                
            if not context.args:
                await update.message.reply_text(
                    "📝 <b>Использование:</b>\n"
                    "<code>/del код_капта</code>", 
                    parse_mode=ParseMode.HTML
                )
                return
            
            event_code = context.args[0]
            
            if event_code not in self.events:
                await update.message.reply_text("❌ <b>Капт не найден!</b>", parse_mode=ParseMode.HTML)
                return
            
            event_name = self.events[event_code]['name']
            
            # Удаляем сообщение капта если оно есть
            if event_code in self.event_messages:
                try:
                    chat_id, message_id = self.event_messages[event_code]
                    await context.bot.delete_message(chat_id, message_id)
                except:
                    pass
                del self.event_messages[event_code]
            
            # Удаляем капт
            del self.events[event_code]
            self.save_data("events", self.events)
            
            await update.message.reply_text(
                f"🗑️ <b>КАПТ УДАЛЕН!</b>\n\n"
                f"🎯 <b>{event_name}</b> (<code>{event_code}</code>)", 
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text("❌ <b>Ошибка удаления!</b>", parse_mode=ParseMode.HTML)

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика бота"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            uptime = time.time() - self.start_time
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            minutes = int((uptime % 3600) // 60)
            
            stats_text = (
                "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
                f"⏱️ <b>Аптайм:</b> {days}д {hours}ч {minutes}м\n"
                f"🤝 <b>Союзов:</b> {len(self.alliances)}\n"
                f"🎯 <b>Каптов:</b> {len(self.events)}\n"
                f"👥 <b>Админов:</b> {len(self.admin_users)}\n"
                f"👑 <b>Root:</b> {len(self.root_users)}\n"
                f"💬 <b>Чатов:</b> {len(self.alert_chats)}\n\n"
                f"🕐 <b>Время МСК:</b> {self.get_moscow_time().strftime('%H:%M:%S')}"
            )
            
            await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в admin_stats: {e}")

    async def admin_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Список админов"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            if not self.admin_users:
                await update.message.reply_text("👥 <b>Список администраторов пуст</b>", parse_mode=ParseMode.HTML)
                return
            
            admin_list = "👥 <b>АДМИНИСТРАТОРЫ</b>\n\n"
            
            for user_id, user_data in self.admin_users.items():
                username = user_data.get('username', 'Нет username')
                first_name = user_data.get('first_name', 'Неизвестно')
                added_date = user_data.get('added_date', 'N/A')
                is_root = "👑 " if str(user_id) in self.root_users else "🛠️ "
                
                admin_list += f"{is_root}<b>{first_name}</b>\n"
                admin_list += f"   📧 @{username}\n"
                admin_list += f"   🆔 ID: {user_id}\n"
                admin_list += f"   📅 {added_date}\n\n"
            
            admin_list += f"📈 <b>Всего:</b> {len(self.admin_users)} администраторов"
            
            await update.message.reply_text(admin_list, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в admin_list: {e}")

    async def test_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Тестовое оповещение"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            test_text = (
                "🔔 <b>ТЕСТОВОЕ ОПОВЕЩЕНИЕ</b>\n\n"
                "✅ <b>Система работает корректно</b>\n"
                "📡 <b>Все каналы связи активны</b>\n\n"
                "💡 <i>Это тестовое сообщение</i>"
            )
            
            await update.message.reply_text(test_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка в test_alert: {e}")

    async def reload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перезагрузить данные"""
        try:
            if update.effective_chat.type == 'private':
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
                
            if not self.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ <b>Доступ запрещен!</b>", parse_mode=ParseMode.HTML)
                return
            
            self.alliances = self.load_data("alliances")
            self.admin_users = self.load_data("admin_users")
            self.root_users = self.load_data("root_users")
            self.events = self.load_data("events")
            
            await update.message.reply_text(
                "🔄 <b>ДАННЫЕ ПЕРЕЗАГРУЖЕНЫ!</b>\n\n"
                "✅ <b>Все системы обновлены</b>", 
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка в reload: {e}")

    async def pin_event_message(self, application, chat_id, message_id):
        """Закрепить сообщение с каптом"""
        try:
            await application.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=message_id,
                disable_notification=True
            )
            logger.info(f"Сообщение {message_id} закреплено в чате {chat_id}")
        except Exception as e:
            logger.warning(f"Не удалось закрепить сообщение: {e}")

    # ==================== АВТОМАТИЧЕСКИЕ ОПОВЕЩЕНИЯ ====================
    
    async def scheduled_tasks(self, application):
        """Планировщик задач"""
        while True:
            try:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
                now = self.get_moscow_time()
                
                # Утреннее оповещение в 10:00
                if now.hour == 10 and now.minute == 0:
                    await self.send_morning_alert(application)
                
                # Напоминание об особе в 17:30
                if now.hour == 17 and now.minute == 30:
                    await self.send_hack_reminder(application)
                
                # Ежедневные капты в 14:00
                if now.hour == 14 and now.minute == 0:
                    await self.send_daily_kapt_status(application)
                
                # Ночной режим в 23:00
                if now.hour == 23 and now.minute == 0:
                    await self.send_good_night(application)
                
                # Очистка системы в 06:00
                if now.hour == 6 and now.minute == 0:
                    await self.cleanup_system(application)
                
                # Оповещения о особах в 18:00
                for location, schedule in HACK_SCHEDULE.items():
                    if (now.weekday() == schedule["day"] and 
                        now.hour == schedule["hour"] and 
                        now.minute == schedule["minute"]):
                        await self.send_hack_alert(application, location)
                
                # Авто-сохранение данных каждые 10 минут
                if now.minute % 10 == 0:
                    self.save_data("alliances", self.alliances)
                    self.save_data("admin_users", self.admin_users)
                    self.save_data("root_users", self.root_users)
                    self.save_data("events", self.events)
                    
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")

    async def send_morning_alert(self, application):
        """Утреннее оповещение в 10:00"""
        try:
            now = self.get_moscow_time()
            
            alert_text = (
                "🌅 <b>ДОБРОЕ УТРО!</b>\n\n"
                "📊 <b>СВОДКА НА СЕГОДНЯ:</b>\n"
            )
            
            # Проверяем сегодняшние особы
            today_hacks = []
            for location, schedule in HACK_SCHEDULE.items():
                if schedule["day"] == now.weekday():
                    today_hacks.append(f"🎯 {location} - {schedule['hour']:02d}:{schedule['minute']:02d}")
            
            if today_hacks:
                alert_text += "🔓 <b>Сегодня особы:</b>\n" + "\n".join(today_hacks)
            else:
                alert_text += "✅ <b>Сегодня особы нет</b>\n"
            
            alert_text += "\n🤝 <b>АКТИВНЫЕ СОЮЗЫ:</b>\n"
            
            if self.alliances:
                for alliance_data in self.alliances.values():
                    alert_text += f"🔹 {alliance_data['name']} ({alliance_data['code']})\n"
            else:
                alert_text += "❌ <b>Нет активных союзов</b>\n"
            
            # Отправляем во все активные чаты
            for chat_id in self.alert_chats:
                try:
                    await application.bot.send_message(chat_id=chat_id, text=alert_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Ошибка отправки в чат {chat_id}: {e}")
                    self.alert_chats.discard(chat_id)
            
            logger.info("🌅 Утреннее оповещение отправлено")
                
        except Exception as e:
            logger.error(f"Ошибка отправки утреннего оповещения: {e}")

    async def send_hack_reminder(self, application):
        """Напоминание об особе в 17:30"""
        try:
            now = self.get_moscow_time()
            
            # Проверяем сегодняшние особы
            today_hacks = []
            for location, schedule in HACK_SCHEDULE.items():
                if schedule["day"] == now.weekday():
                    today_hacks.append(location)
            
            if today_hacks:
                for location in today_hacks:
                    alert_text = (
                        "📢 <b>НАПОМИНАНИЕ ОБ ОСОБЕ!</b>\n\n"
                        f"🎯 <b>ЧЕРЕЗ 30 МИНУТ:</b> {location}\n"
                        f"⏰ <b>Время:</b> 18:00 МСК\n\n"
                        f"🔔 <b>Калл {location}!</b>\n"
                        f"💂 <b>Готовьтесь к защите!</b>"
                    )
                    
                    # Отправляем во все активные чаты
                    for chat_id in self.alert_chats:
                        try:
                            await application.bot.send_message(chat_id=chat_id, text=alert_text, parse_mode=ParseMode.HTML)
                        except Exception as e:
                            logger.error(f"Ошибка отправки в чат {chat_id}: {e}")
                            self.alert_chats.discard(chat_id)
                
                logger.info("📢 Напоминание об особе отправлено")
                
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")

    async def send_hack_alert(self, application, location: str):
        """Оповещение о особы в 18:00"""
        try:
            now = self.get_moscow_time()
            
            alert_text = (
                "🚨 <b>СРОЧНОЕ ОПОВЕЩЕНИЕ!</b>\n\n"
                f"🔓 <b>ОСОБА:</b> {location}\n"
                f"⏰ <b>Время:</b> {now.strftime('%H:%M %d.%m.%Y')}\n\n"
                f"🔔 <b>Калл {location}!</b>\n"
                "💂 <b>Требуется помощь!</b>"
            )
            
            # Отправляем во все активные чаты
            for chat_id in self.alert_chats:
                try:
                    await application.bot.send_message(chat_id=chat_id, text=alert_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Ошибка отправки в чат {chat_id}: {e}")
                    self.alert_chats.discard(chat_id)
            
            logger.info(f"🚨 Оповещение о особы {location} отправлено")
                
        except Exception as e:
            logger.error(f"Ошибка отправки оповещения о особы: {e}")

    async def send_daily_kapt_status(self, application):
        """Ежедневные капты в 14:00"""
        try:
            now = self.get_moscow_time()
            
            if not self.events:
                text = (
                    "🕐 <b>ЕЖЕДНЕВНЫЙ СТАТУС КАПТОВ</b>\n\n"
                    "📭 <b>Активных каптов нет</b>\n\n"
                    "💡 <i>Создайте первый капт командой /create</i>"
                )
            else:
                text = "🕐 <b>ЕЖЕДНЕВНЫЙ СТАТУС КАПТОВ</b>\n\n"
                
                for code, event in self.events.items():
                    text += (
                        f"🔢 <b>Код:</b> <code>{code}</code>\n"
                        f"🎯 <b>{event['name']}</b>\n"
                        f"📅 <b>Когда:</b> {event['date']} {event['time']} МСК\n"
                        f"🎫 <b>Слоты:</b> {event['slots']}\n"
                        f"⚔️ <b>Оружие:</b> {event['weapon_type']}\n"
                        f"❤️ <b>Хил:</b> {event['heal']}\n"
                        f"🛡️ <b>Роль:</b> {event['role']}\n"
                        f"👤 <b>Создатель:</b> {event['author']}\n"
                        f"────────────────────\n\n"
                    )
            
            # Отправляем во все активные чаты
            for chat_id in self.alert_chats:
                try:
                    message = await application.bot.send_message(
                        chat_id=chat_id, 
                        text=text, 
                        parse_mode=ParseMode.HTML
                    )
                    # Закрепляем сообщение
                    await self.pin_event_message(application, chat_id, message.message_id)
                    self.bot_messages.append((message.chat_id, message.message_id, time.time()))
                except Exception as e:
                    logger.error(f"Ошибка отправки в чат {chat_id}: {e}")
                    self.alert_chats.discard(chat_id)
            
            logger.info("🕐 Ежедневные капты отправлены и закреплены")
                
        except Exception as e:
            logger.error(f"Ошибка отправки ежедневных каптов: {e}")

    async def send_good_night(self, application):
        """Ночной режим в 23:00"""
        try:
            now = self.get_moscow_time()
            
            good_night_text = (
                "🌙 <b>СИСТЕМА ПЕРЕХОДИТ В НОЧНОЙ РЕЖИМ</b> 🌙\n\n"
                "🕰️ <b>Время:</b> 23:00 МСК\n"
                "💤 <b>Все капты на сегодня завершены!</b>\n"
                "🌜 <b>Спокойной ночи! Всем хорошо выспаться!</b>\n"
                "🖥️ <b>Сервера работают в фоновом режиме...</b>\n"
                "🧹 <b>Утренняя очистка в 6:00 МСК</b>\n\n"
                "👨‍💻 <b>Разработано Данилом</b> | @ChikenXa"
            )
            
            # Отправляем во все активные чаты
            for chat_id in self.alert_chats:
                try:
                    message = await application.bot.send_message(
                        chat_id=chat_id, 
                        text=good_night_text, 
                        parse_mode=ParseMode.HTML
                    )
                    self.bot_messages.append((message.chat_id, message.message_id, time.time()))
                except Exception as e:
                    logger.error(f"Ошибка отправки в чат {chat_id}: {e}")
                    self.alert_chats.discard(chat_id)
            
            logger.info("🌙 Ночной режим активирован")
                
        except Exception as e:
            logger.error(f"Ошибка отправки ночного режима: {e}")

    async def cleanup_system(self, application):
        """Очистка системы в 06:00"""
        try:
            now = self.get_moscow_time()
            
            # Эффектная очистка системы
            cleanup_text = (
                "🧹 <b>ЗАПУСК СИСТЕМЫ ОЧИСТКИ</b> 🧹\n\n"
                "🔍 <b>Сканирование базы данных...</b>"
            )
            
            # Отправляем во все активные чаты
            for chat_id in self.alert_chats:
                try:
                    # Отправляем начальное сообщение
                    status_message = await application.bot.send_message(
                        chat_id=chat_id, 
                        text=cleanup_text, 
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Ждем немного для эффекта
                    await asyncio.sleep(2)
                    
                    # Обновляем сообщение
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=(
                            "🧹 <b>ЗАПУСК СИСТЕМЫ ОЧИСТКИ</b> 🧹\n\n"
                            "✅ <b>База данных просканирована</b>\n"
                            "🔍 <b>Поиск устаревших сообщений...</b>"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Считаем сообщения для удаления
                    messages_to_delete = []
                    current_timestamp = time.time()
                    
                    for msg_chat_id, message_id, timestamp in self.bot_messages[:]:
                        if msg_chat_id == chat_id and current_timestamp - timestamp > 3600:  # старше 1 часа
                            messages_to_delete.append((message_id, timestamp))
                    
                    # Обновляем с количеством найденных сообщений
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=(
                            "🧹 <b>ЗАПУСК СИСТЕМЫ ОЧИСТКИ</b> 🧹\n\n"
                            "✅ <b>База данных просканирована</b>\n"
                            "✅ <b>Найдено устаревших сообщений</b>\n"
                            f"📊 <b>Обнаружено:</b> {len(messages_to_delete)} сообщений\n"
                            "🗑️ <b>Начинаю очистку...</b>"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Процесс удаления
                    deleted_count = 0
                    for message_id, timestamp in messages_to_delete:
                        try:
                            await application.bot.delete_message(chat_id, message_id)
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")
                    
                    # Удаляем обработанные сообщения из списка
                    for message_id, timestamp in messages_to_delete:
                        for msg in self.bot_messages[:]:
                            if msg[0] == chat_id and msg[1] == message_id:
                                self.bot_messages.remove(msg)
                                break
                    
                    # Очищаем завершенные капты
                    current_date = now.strftime("%d.%m")
                    events_to_remove = []
                    
                    for event_code, event in self.events.items():
                        event_date = event['date']
                        try:
                            event_day, event_month = event_date.split('.')
                            current_day, current_month = current_date.split('.')
                            
                            # Если капт прошел (дата раньше текущей)
                            if (int(current_month) > int(event_month)) or \
                               (int(current_month) == int(event_month) and int(current_day) > int(event_day)):
                                events_to_remove.append(event_code)
                        except:
                            pass
                    
                    # Удаляем капты
                    for event_code in events_to_remove:
                        if event_code in self.event_messages:
                            del self.event_messages[event_code]
                        if event_code in self.events:
                            del self.events[event_code]
                    
                    # Финальное сообщение
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=(
                            "🧹 <b>СИСТЕМА ОЧИСТКИ ЗАВЕРШИЛА РАБОТУ</b> 🧹\n\n"
                            "📊 <b>ОТЧЕТ О ВЫПОЛНЕНИИ:</b>\n"
                            f"✅ <b>Удалено сообщений:</b> {deleted_count}\n"
                            f"✅ <b>Очищено каптов:</b> {len(events_to_remove)}\n"
                            f"✅ <b>Активных каптов:</b> {len(self.events)}\n"
                            f"📝 <b>Сообщений в памяти:</b> {len(self.bot_messages)}\n\n"
                            "🎯 <b>СИСТЕМА ГОТОВА К РАБОТЕ</b> 🎯\n\n"
                            "👨‍💻 <b>Разработано Данилом</b> | @ChikenXa"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Сохраняем финальное сообщение для следующей очистки
                    self.bot_messages.append((status_message.chat_id, status_message.message_id, time.time()))
                    
                    # Сохраняем данные
                    self.save_data("events", self.events)
                    
                except Exception as e:
                    logger.error(f"Ошибка очистки в чате {chat_id}: {e}")
            
            logger.info("🧹 Очистка системы завершена")
                
        except Exception as e:
            logger.error(f"Ошибка очистки системы: {e}")

    # ==================== НАСТРОЙКА ОБРАБОТЧИКОВ ====================
    
    def setup_handlers(self, application):
        """Настройка обработчиков"""
        # Основные команды
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("pong", self.pong))
        application.add_handler(CommandHandler("hacks", self.show_hacks))
        application.add_handler(CommandHandler("alliances", self.show_alliances))
        application.add_handler(CommandHandler("next", self.next_hack))
        application.add_handler(CommandHandler("kapt", self.kapt_command))
        application.add_handler(CommandHandler("create", self.create_event))
        application.add_handler(CommandHandler("admin", self.admin_panel))
        
        # Админ-команды
        application.add_handler(CommandHandler("add_alliance", self.add_alliance))
        application.add_handler(CommandHandler("remove_alliance", self.remove_alliance))
        application.add_handler(CommandHandler("clear_alliances", self.clear_alliances))
        application.add_handler(CommandHandler("del", self.delete_event_command))
        application.add_handler(CommandHandler("admin_stats", self.admin_stats))
        application.add_handler(CommandHandler("admin_list", self.admin_list))
        application.add_handler(CommandHandler("test_alert", self.test_alert))
        application.add_handler(CommandHandler("reload", self.reload))
        
        # Root команды
        application.add_handler(CommandHandler("add_admin", self.add_admin))
        application.add_handler(CommandHandler("remove_admin", self.remove_admin))
        
        # Обработчик сообщений с паролем
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Обработчик ошибок
        application.add_error_handler(self.error_handler)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        try:
            logger.error(f"Exception while handling an update: {context.error}")
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(self.token).build()
        self.setup_handlers(application)
        
        # Запускаем планировщик задач
        application.job_queue.run_once(lambda ctx: asyncio.create_task(self.scheduled_tasks(application)), when=5)
        
        print("✨ " + "="*50)
        print("🤖 ДАНИЛБOT ЗАПУЩЕН!")
        print("✨ " + "="*50)
        print("🎯 СИСТЕМА КАПТОВ: Активирована")
        print("🏰 СИСТЕМА ОСОБНЯКОВ: Активирована")
        print("🤝 СИСТЕМА СОЮЗОВ: Активирована")
        print("🛠️ АДМИН-СИСТЕМА: Готова")
        print("👑 ROOT-СИСТЕМА: Активирована")
        print("🔔 АВТО-ОПОВЕЩЕНИЯ: 10:00, 17:30, 18:00, 14:00, 23:00, 06:00")
        print("🔐 ПАРОЛЬ АДМИНА: 24680")
        print("👑 ПАРОЛЬ ROOT: 1508")
        print("🔧 KEEP-ALIVE: Активен")
        print("💬 РЕЖИМ: Только группы")
        print("👨‍💻 РАЗРАБОТЧИК: Данил | @ChikenXa")
        print("✨ " + "="*50)
        
        application.run_polling()

# Запуск бота
if __name__ == "__main__":
    bot = DanilBot(BOT_TOKEN)
    bot.run()
