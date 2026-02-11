import os
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

user_state = {}
admin_state = {}

# ================== ВСПОМОГАТЕЛЬНЫЕ ==================
def parse_button(text: str):
    if "|button=" in text:
        try:
            main_text, btn_part = text.split("|button=", 1)
            btn_text, btn_url = btn_part.split("|", 1)
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn_text.strip(), url=btn_url.strip())]]
            )
            return main_text.strip(), keyboard
        except:
            return text, None
    return text, None

def add_user(user_id: int):
    users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f:
            users = set(f.read().splitlines())
    if str(user_id) not in users:
        users.add(str(user_id))
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(users) + "\n")

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

def get_users_by_segment(segment: str):
    segment = segment.lower()
    if not os.path.exists(SEGMENTS_FILE):
        return []
    with open(SEGMENTS_FILE, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return [line.split("|")[0] for line in lines if line.split("|")[1] == segment]

async def send_photo_or_text(bot, chat_id, text, image=None, admin_id=None):
    text, keyboard = parse_button(text)
    try:
        if image:
            image_path = os.path.join(MEDIA_DIR, image)
            if os.path.exists(image_path):
                with open(image_path, "rb") as photo:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await send_photo_or_text(bot, chat_id, text, image, admin_id)
    except TelegramError as e:
        if admin_id:
            await bot.send_message(chat_id=admin_id, text=f"Ошибка: {e}")

# ================== РЕГИСТРАЦИЯ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    add_user(user_id)

    text = (
        f"{first_name}, добро пожаловать 👋\n\n"
        "Оставьте номер телефона ниже 👇"
    )

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📲 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(text, reply_markup=keyboard)
    user_state[user_id] = "WAIT_CONTACT"

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact
    name = contact.first_name
    phone = contact.phone_number

    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name} | {phone}\n")

    add_user_to_segment(user_id, "new")

    text = f"{name}, вы зарегистрированы 🎉"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 Подарок", url="https://google.com")]]
    )

    await update.message.reply_text(text, reply_markup=keyboard)

# ================== РАССЫЛКА ВСЕМ ==================
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Использование: /sendall текст")
        return

    first_arg = context.args[0]
    if first_arg.lower().endswith((".jpg", ".png", ".jpeg", ".gif")):
        image = first_arg
        text = " ".join(context.args[1:])
    else:
        image = None
        text = " ".join(context.args)

    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            users = f.read().splitlines()
    except:
        await update.message.reply_text("Нет пользователей")
        return

    for user_id in users:
        await send_photo_or_text(context.bot, int(user_id), text, image)

    await update.message.reply_text("Рассылка завершена ✅")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(CommandHandler("sendall", send_all))

    app.run_polling()

if __name__ == "__main__":
    main()

