import os
import shutil
import asyncio
from datetime import datetime, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.error import TelegramError, RetryAfter
from telegram.constants import ParseMode

# ================== НАСТРОЙКИ ==================
TOKEN = "8350316731:AAFJHJhnXJZCETz9F1opdT8v9BECxNk_FQY"
ADMIN_ID = 268936036
USERS_FILE = "users.txt"
DATA_FILE = "registrations.txt"
SEGMENTS_FILE = "segments.txt"
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# ================== СОСТОЯНИЯ ==================
user_state = {}
admin_state = {}

# ================== УТИЛИТЫ ==================
def backup_file(file_path):
    if os.path.exists(file_path):
        base = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(file_path, os.path.join(BACKUP_DIR, f"{timestamp}_{base}"))

def add_user(user_id: int):
    users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f:
            users = set(f.read().splitlines())
    if str(user_id) not in users:
        users.add(str(user_id))
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(users) + "\n")
        backup_file(USERS_FILE)
        add_user_to_segment(user_id, "new")

def add_user_to_segment(user_id: int, segment: str):
    segment = segment.lower()
    lines = []
    if os.path.exists(SEGMENTS_FILE):
        with open(SEGMENTS_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    entry = f"{user_id}|{segment}"
    if entry not in lines:
        lines.append(entry)
        with open(SEGMENTS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        backup_file(SEGMENTS_FILE)

def get_users_by_segment(segment: str):
    segment = segment.lower()
    if not os.path.exists(SEGMENTS_FILE):
        return []
    with open(SEGMENTS_FILE, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return [line.split("|")[0] for line in lines if line.split("|")[1] == segment]

async def send_photo_or_text(bot, chat_id, text, image=None, admin_id=None):
    try:
        if image:
            if not image.startswith("http"):
                path = os.path.join(MEDIA_DIR, image)
                if os.path.exists(path):
                    with open(path, "rb") as photo_file:
                        await bot.send_photo(chat_id=chat_id, photo=photo_file, caption=text, parse_mode=ParseMode.HTML)
                else:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
                    if admin_id:
                        await bot.send_message(chat_id=admin_id, text=f"⚠ Файл {path} не найден")
                return
            else:
                await bot.send_photo(chat_id=chat_id, photo=image, caption=text, parse_mode=ParseMode.HTML)
                return
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await send_photo_or_text(bot, chat_id, text, image, admin_id)
    except TelegramError as e:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("errors.txt", "a", encoding="utf-8") as f:
            f.write(f"{now} | {chat_id} | {e}\n")
        if admin_id:
            await bot.send_message(chat_id=admin_id, text=f"❌ Ошибка отправки пользователю {chat_id}:\n{e}")

# ================== РЕГИСТРАЦИЯ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    add_user(user_id)
    text = f"{first_name}, добро пожаловать в бот! Отправьте свой контакт."
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📲 Отправить имя и телефон", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(text, reply_markup=keyboard)
    user_state[user_id] = "WAIT_CONTACT"

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_state.get(user_id) != "WAIT_CONTACT":
        return
    contact = update.message.contact
    name, phone = contact.first_name, contact.phone_number
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name} | {phone}\n")
    backup_file(DATA_FILE)
    add_user(user_id)
    await update.message.reply_text("Спасибо! Вы зарегистрированы!")
    user_state[user_id] = "DONE"

async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID: return
    await update.message.reply_text("Пожалуйста, нажмите кнопку для отправки контакта ☝️")

# ================== РАССЫЛКИ ==================
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Использование: /sendall имя_картинки текст")
        return
    raw = update.message.text.partition(" ")[2]
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    image = None
    text = "\n".join(lines)
    if lines and lines[0].lower().endswith((".jpg",".png",".jpeg",".gif")):
        image = lines[0]; text = "\n".join(lines[1:])
    try:
        with open(USERS_FILE, encoding="utf-8") as f: users=f.read().splitlines()
    except FileNotFoundError:
        await update.message.reply_text("Нет пользователей")
        return
    sent=failed=0
    for u in users:
        try:
            await send_photo_or_text(context.bot,int(u),text,image,admin_id=update.effective_user.id)
            sent+=1; await asyncio.sleep(0.05)
        except: failed+=1
    await update.message.reply_text(f"✅ Отправлено: {sent}\nОшибок: {failed}")

async def send_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args)<2:
        await update.message.reply_text("Использование: /send user_id текст")
        return
    user_id = context.args[0]
    text = update.message.text.partition(" ")[2].partition(" ")[2]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    image=None
    if lines and lines[0].lower().endswith((".jpg",".png",".jpeg",".gif")):
        image=lines[0]; text="\n".join(lines[1:])
    try:
        await send_photo_or_text(context.bot,int(user_id),text,image,admin_id=update.effective_user.id)
        await update.message.reply_text(f"✅ Сообщение отправлено {user_id}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))
    app.add_handler(CommandHandler("sendall", send_all))
    app.add_handler(CommandHandler("send", send_user))
    app.run_polling()

if __name__ == "__main__":
    main()
