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

# ================== СОСТОЯНИЯ ==================
user_state = {}
admin_state = {}

# ================== ФУНКЦИИ ==================
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
    users = [line.split("|")[0] for line in lines if line.split("|")[1] == segment]
    return users

async def send_photo_or_text(bot, chat_id, text, image=None, admin_id=None):
    try:
        if image:
            if not image.startswith("http"):
                image_path = os.path.join(MEDIA_DIR, image)
                if os.path.exists(image_path):
                    with open(image_path, "rb") as photo_file:
                        await bot.send_photo(chat_id=chat_id, photo=photo_file, caption=text, parse_mode=ParseMode.HTML)
                else:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
                    if admin_id:
                        await bot.send_message(chat_id=admin_id, text=f"⚠ Файл {image_path} не найден")
                return
            else:
                await bot.send_photo(chat_id=chat_id, photo=image, caption=text, parse_mode=ParseMode.HTML)
                return
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await send_photo_or_text(bot, chat_id, text, image, admin_id)
    except TelegramError as e:
        if admin_id:
            await bot.send_message(chat_id=admin_id, text=f"❌ Ошибка отправки пользователю {chat_id}:\n{e}")
        with open("errors.txt", "a", encoding="utf-8") as f:
            f.write(f"{chat_id} | {e}\n")

# ================== РЕГИСТРАЦИЯ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    add_user(user_id)
    text = (
        f"{first_name}, добро пожаловать в бот SMI 👋\n\n"
        "Он поможет вам зарегистрироваться на вебинар и получить подарок 🎁\n\n"
        "Чтобы завершить регистрацию, оставьте ваш номер телефона по кнопке ниже 👇🏻"
    )
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📲 Отправить имя и телефон", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(text, reply_markup=keyboard)
    user_state[user_id] = "WAIT_CONTACT"

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_state.get(user_id) != "WAIT_CONTACT":
        return
    contact = update.message.contact
    name = contact.first_name
    phone = contact.phone_number
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name} | {phone}\n")
    add_user(user_id)
    add_user_to_segment(user_id, "new")
    await update.message.reply_text("Спасибо! Регистрируем вас...")
    text = (
        f"{name}, поздравляю! 🎉\n\n"
        "Вы успешно зарегистрированы на вебинар.\n\n"
        "📍На эфире вас ждёт:\n"
        "— обзор российского и американского рынков\n"
        "— актуальная информация по инвестициям\n"
        "— и бонус 🎁"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎁 ЗАБРАТЬ ПОДАРОК", url="https://t.me/+a163cq-juqRjMzMy")]]
    )
    photo_path = "webinar.jpg"
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    user_state[user_id] = "DONE"

async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        return
    await update.message.reply_text("Пожалуйста, нажмите кнопку для отправки контакта ☝️")

# ================== РАССЫЛКИ ==================
# (Здесь вставляем все функции send_all, send_user, send_segment, schedule_send, delayed_send как в твоём коде)
# Они остаются без изменений

# ================== СЕГМЕНТЫ ==================
# (Функции add_segment и show_segment остаются без изменений)

# ================== АДМИН-ПАНЕЛЬ ==================
# (Функции admin_panel и admin_button_handler остаются без изменений)

# ================== ОБРАБОТКА ТЕКСТА АДМИНА ==================
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    admin_id = update.effective_user.id
    if admin_id not in admin_state or admin_state[admin_id]["action"] is None:
        return

    action = admin_state[admin_id]["action"]
    data = admin_state[admin_id]["data"]
    text = update.message.text.strip()

    def split_image_and_text(raw_text: str):
        parts = raw_text.split(maxsplit=1)
        if parts and parts[0].lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            image = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            return image, message
        return None, raw_text

    if action == "sendall":
        image, message_text = split_image_and_text(text)
        context.args = [image, message_text] if image else [message_text]
        update.message.text = "/sendall"
        await send_all(update, context)
        admin_state[admin_id] = {"action": None, "data": {}}

    elif action == "send":
        if "user_id" not in data:
            data["user_id"] = text
            await update.message.reply_text("Введите имя картинки (если есть) и текст:")
        else:
            image, message_text = split_image_and_text(text)
            context.args = [data["user_id"], image, message_text] if image else [data["user_id"], message_text]
            update.message.text = "/send"
            await send_user(update, context)
            admin_state[admin_id] = {"action": None, "data": {}}

    elif action == "sendsegment":
        if "segment" not in data:
            data["segment"] = text
            await update.message.reply_text("Введите имя картинки (если есть) и текст:")
        else:
            image, message_text = split_image_and_text(text)
            context.args = [data["segment"], image, message_text] if image else [data["segment"], message_text]
            update.message.text = "/sendsegment"
            await send_segment(update, context)
            admin_state[admin_id] = {"action": None, "data": {}}

    elif action == "schedule":
        if "time" not in data:
            data["time"] = text
            await update.message.reply_text("Введите имя картинки (если есть) и текст:")
        else:
            image, message_text = split_image_and_text(text)
            context.args = [data["time"], image, message_text] if image else [data["time"], message_text]
            update.message.text = "/schedule"
            await schedule_send(update, context)
            admin_state[admin_id] = {"action": None, "data": {}}

    elif action == "addsegment":
        if "user_id" not in data:
            data["user_id"] = text
            await update.message.reply_text("Введите название сегмента:")
        else:
            context.args = [data["user_id"], text]
            await add_segment(update, context)
            admin_state[admin_id] = {"action": None, "data": {}}

    elif action == "showsegment":
        context.args = [text]
        await show_segment(update, context)
        admin_state[admin_id] = {"action": None, "data": {}}

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    app.add_handler(CommandHandler("sendall", send_all))
    app.add_handler(CommandHandler("send", send_user))
    app.add_handler(CommandHandler("sendsegment", send_segment))
    app.add_handler(CommandHandler("schedule", schedule_send))
    app.add_handler(CommandHandler("addsegment", add_segment))
    app.add_handler(CommandHandler("showsegment", show_segment))

    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(
        filters.Regex(r"^(✅ Рассылка всем|📬 Персональная рассылка|🏷 Рассылка сегменту|⏰ Отложенная рассылка|➕ Добавить в сегмент|📄 Показать сегмент)$"),
        admin_button_handler
    ))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    app.run_polling()


if __name__ == "__main__":
    main()
