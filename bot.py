import os
import json
import logging
from logging.handlers import RotatingFileHandler
import telebot # type: ignore
from telebot import types # type: ignore
from apscheduler.schedulers.background import BackgroundScheduler # type: ignore
from supabase_db import get_proxies
from base64 import b64encode
from datetime import datetime, timedelta
import threading
import time
from dotenv import load_dotenv # type: ignore
from health_server import start_health_server

# Load environment variables
load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_CHAT_IDS = [int(id.strip()) for id in os.environ["GROUP_CHAT_ID"].split(",")]
ADMIN_IDS = [int(id) for id in os.environ["ADMIN_IDS"].split(",")]

# Initialize logging
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("ProxyBot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("logs/bot.log", maxBytes=5*1024*1024, backupCount=2)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize bot with proxy support
proxy_url = os.environ.get('TELEGRAM_PROXY', None)
if proxy_url:
    telebot.apihelper.proxy = {'https': proxy_url}

bot = telebot.TeleBot(BOT_TOKEN)

# Scheduler
scheduler = BackgroundScheduler()
scheduler_started = False

# Admin check decorator
def admin_only(func):
    def wrapper(message):
        if message.from_user.id in ADMIN_IDS:
            func(message)
        else:
            bot.reply_to(message, "❌ You are not authorized to use this command.")
    return wrapper

# Function to read setting.json
def read_settings():
    with open("setting.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Function to write setting.json
def write_settings(data):
    with open("setting.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)



# Function to format proxy links
def format_proxy_links(proxies):
    if not proxies:
        return "No working proxies found."
    message = "🛡️ Proxies:\n"
    for proxy in proxies:
        message += f"[پروکسی مهندس علایی]({proxy})\n"
    return message

# Function to collect and send proxies
def send_updates():
    try:
        proxies = get_proxies(20)  # 20 proxy links for group
        proxy_message = format_proxy_links(proxies)
        current_time = (datetime.now() + timedelta(hours=4)).strftime("%b-%d %H:%M")
        proxy_full_message = f"📢 Update {current_time}\n\n{proxy_message}"
        
        for group_id in GROUP_CHAT_IDS:
            try:
                bot.send_message(chat_id=group_id, text=proxy_full_message, parse_mode='Markdown')
            except Exception as msg_error:
                logger.error(f"Failed to send to group {group_id}: {msg_error}")
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(chat_id=admin_id, text=f"⚠️ Failed to send to group {group_id}. Proxy message: {proxy_full_message}")
                        break
                    except:
                        continue
        logger.info(f"Sent update at {current_time} with {len(proxies)} proxies")
    except Exception as e:
        logger.error(f"Error sending update: {e}")

# Create inline keyboard for private messages
def create_main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🛡️ Get Proxies", callback_data="get_proxies"),
        types.InlineKeyboardButton("🔗 Get Configs", callback_data="get_configs")
    )
    keyboard.add(
        types.InlineKeyboardButton("📊 Status", callback_data="status"),
        types.InlineKeyboardButton("📜 Logs", callback_data="logs")
    )
    keyboard.add(
        types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
    )
    return keyboard

def create_admin_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("▶️ Start Scheduler", callback_data="start_scheduler"),
        types.InlineKeyboardButton("⏹️ Stop Scheduler", callback_data="stop_scheduler")
    )
    keyboard.add(
        types.InlineKeyboardButton("📋 List Channels", callback_data="list_channels"),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_main")
    )
    return keyboard

# Start command with buttons
@bot.message_handler(commands=['start'])
def start_command(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "🚀 Welcome! Choose an option:", reply_markup=create_main_keyboard())
    logger.info(f"User {message.from_user.id} used /start")

# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "get_proxies":
        get_proxy_callback(call)
    elif call.data == "get_configs":
        get_config_callback(call)
    elif call.data == "status":
        status_callback(call)
    elif call.data == "logs":
        logs_callback(call)
    elif call.data == "admin_panel":
        admin_panel_callback(call)
    elif call.data == "start_scheduler":
        start_scheduler_callback(call)
    elif call.data == "stop_scheduler":
        stop_scheduler_callback(call)
    elif call.data == "list_channels":
        list_channels_callback(call)
    elif call.data == "back_main":
        bot.edit_message_text("🚀 Welcome! Choose an option:", call.message.chat.id, call.message.message_id, reply_markup=create_main_keyboard())

def get_proxy_callback(call):
    try:
        proxies = get_proxies(10)  # 10 proxies for private callback
        if not proxies:
            bot.answer_callback_query(call.id, "No working proxies found.")
            return
        proxy_message = format_proxy_links(proxies)
        bot.edit_message_text(proxy_message, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main")))
    except Exception as e:
        bot.answer_callback_query(call.id, "Error getting proxies")

def get_config_callback(call):
    config_message = "برای استفاده از کانفیگ ها از اپلیکیشن TgProx استفاده کنید"
    bot.edit_message_text(config_message, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main")))

def status_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admin only")
        return
    status = "running" if scheduler_started else "stopped"
    last_update = scheduler.get_jobs()[0].next_run_time.strftime("%b-%d %H:%M") if scheduler_started and scheduler.get_jobs() else "N/A"
    response = f"📊 Bot Status: {status}\nNext Update: {last_update}"
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main")))

def logs_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admin only")
        return
    try:
        with open("logs/bot.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-10:]
        log_text = "".join(lines) or "No logs available."
        bot.edit_message_text(f"📜 Recent Logs:\n```\n{log_text}\n```", call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main")))
    except Exception as e:
        bot.answer_callback_query(call.id, "Error reading logs")

def admin_panel_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admin only")
        return
    bot.edit_message_text("⚙️ Admin Panel:", call.message.chat.id, call.message.message_id, reply_markup=create_admin_keyboard())

def start_scheduler_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admin only")
        return
    global scheduler_started
    if not scheduler_started:
        scheduler.add_job(send_updates, "interval", minutes=30)
        if not scheduler.running:
            scheduler.start()
        scheduler_started = True
        bot.answer_callback_query(call.id, "✅ Scheduler started (30 min intervals)")
    else:
        bot.answer_callback_query(call.id, "⚠️ Already running")

def stop_scheduler_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admin only")
        return
    global scheduler_started
    if scheduler_started:
        scheduler.shutdown()
        scheduler_started = False
        bot.answer_callback_query(call.id, "✅ Scheduler stopped")
    else:
        bot.answer_callback_query(call.id, "⚠️ Not running")

def list_channels_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Admin only")
        return
    settings = read_settings()
    proxy_channels = "\n".join(settings["proxy_channels"]) or "None"
    config_channels = "\n".join(settings["config_channels"]) or "None"
    response = f"📚 Proxy Channels:\n{proxy_channels}\n\n📚 Config Channels:\n{config_channels}"
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel")))

# Group commands
@bot.message_handler(commands=['getconfig'])
def get_config_command(message):
    config_message = "برای استفاده از کانفیگ ها از اپلیکیشن TgProx استفاده کنید"
    bot.reply_to(message, config_message)
    logger.info(f"User {message.from_user.id} requested configs in {message.chat.type}")

@bot.message_handler(commands=['getproxy'])
def get_proxy_command(message):
    try:
        if message.chat.type == 'private':
            proxies = get_proxies(10)  # 10 proxies for private
        else:
            proxies = get_proxies(20)  # 20 proxies for groups
            
        if not proxies:
            bot.reply_to(message, "No working proxies found.")
            return
        
        proxy_message = format_proxy_links(proxies)
        bot.reply_to(message, proxy_message, parse_mode='Markdown')
        
        logger.info(f"User {message.from_user.id} requested proxies in {message.chat.type}")
    except Exception as e:
        bot.reply_to(message, "❌ Error getting proxies")
        logger.error(f"Error getting proxies: {e}")

@bot.message_handler(commands=['status'])
@admin_only
def status_command(message):
    status = "running" if scheduler_started else "stopped"
    last_update = scheduler.get_jobs()[0].next_run_time.strftime("%b-%d %H:%M") if scheduler_started and scheduler.get_jobs() else "N/A"
    response = f"📊 Bot Status: {status}\nNext Update: {last_update}"
    bot.reply_to(message, response)
    logger.info(f"Admin {message.from_user.id} checked status")

@bot.message_handler(commands=['logs'])
@admin_only
def logs_command(message):
    try:
        with open("logs/bot.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-10:]
        log_text = "".join(lines) or "No logs available."
        bot.reply_to(message, f"📜 Recent Logs:\n```\n{log_text}\n```", parse_mode='Markdown')
        logger.info(f"Admin {message.from_user.id} viewed logs")
    except Exception as e:
        bot.reply_to(message, f"❌ Error reading logs: {e}")
        logger.error(f"Error reading logs: {e}")

# Main function to start bot
def main():
    logger.info("Bot started")
    
    # Start health server
    health_server = start_health_server()
    logger.info("Health server started")
    
    global scheduler_started
    scheduler.add_job(send_updates, "interval", minutes=30)
    scheduler.start()
    scheduler_started = True
    
    # Send initial message to all groups
    send_updates()
    
    while True:
        try:
            logger.info("Starting bot polling...")
            print("Bot is ready and polling...")
            bot.polling(none_stop=True, interval=1, timeout=20)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            logger.info("Restarting in 5 seconds...")
            time.sleep(5)
    
    scheduler.shutdown()
    logger.info("Bot stopped")

if __name__ == "__main__":
    main()