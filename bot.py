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
from telegram.error import TelegramError
from telegram.constants import ParseMode
import asyncio
import os

TOKEN = "8350316731:AAFJHJhnXJZCETz9F1opdT8v9BECxNk_FQY"  # замените на свой токен
USERS_FILE = "users.txt"
DATA_FILE = "registrations.txt"
ADMIN_ID = 268936036  # ваш Telegram ID

# ===== пути =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "media")

# Хранилище состояний пользователей
user_state = {}

# ----------------- ФУНКЦИИ -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.message.from_user.first_name

    # сохраняем user_id
    with open(USERS_FILE, "a+", encoding="utf-8") as f:
        f.seek(0)
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(f"{user_id}\n")

    text = (
        f"{first_name}, добро пожаловать в бот SMI 👋\n\n"
        "Он поможет вам зарегистрироваться на вебинар\n"
        "«Инструменты инвестиций в 2026 году» и получить подарок – Инструкцию для новичков "
        "\"Как открыть счет для торгов и правильно выбрать платформу/банк\" 🎁\n\n"
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

    # Сохраняем в файл
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name} | {phone}\n")

    # Сохраняем user_id ещё раз
    with open(USERS_FILE, "a+", encoding="utf-8") as f:
        f.seek(0)
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(f"{user_id}\n")

    await update.message.reply_text("Спасибо! Регистрируем вас...")

    text = (
        f"{name}, поздравляю! 🎉\n\n"
        "Вы успешно зарегистрированы на вебинар\n"
        "10 февраля в 19:00\n"
        "«Инструменты инвестиций в 2026 году»\n"
        "Фондовые рынки и как на них зарабатывать в России и США\n\n"
        "📍На эфире вас ждёт:\n"
        "— обзор российского и американского инвестиционных рынков\n"
        "— роль и ситуация с рублем в 2026 году\n"
        "— что происходит с процентной ставкой в США\n"
        "— разбор конкретных акций и причин их роста\n"
        "— и приятный бонус, который раскроем уже в эфире 😉\n\n"
        "Переходите в закрытый канал вебинара —\n"
        "там мы будем делиться всеми новостями и именно туда пришлём ссылку на эфир 👇"
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
    await update.message.reply_text("Пожалуйста, нажмите кнопку для отправки контакта ☝️")


# ----------------- ФУНКЦИЯ ОТПРАВКИ ТЕКСТА/КАРТИНКИ -----------------
async def send_photo_or_text(bot, chat_id, text, image=None, admin_id=None):
    try:
        if image:
            # URL
            if image.startswith("http"):
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image,
                    caption=text,
                    parse_mode=ParseMode.HTML
                )
                return

            # Локальный файл
            image_path = os.path.join(MEDIA_DIR, image)

            if not os.path.exists(image_path):
                if admin_id:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"⚠ Картинка не найдена:\n{image_path}"
                    )
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
                return

            with open(image_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode=ParseMode.HTML
                )

        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML
            )

    except TelegramError as e:
        if admin_id:
            await bot.send_message(
                chat_id=admin_id,
                text=f"❌ Ошибка отправки:\n{e}"
            )



# ----------------- РАССЫЛКА ВСЕМ -----------------
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❗ Использование:\n/sendall текст рассылки с абзацами и HTML")
        return

    text = update.message.text.partition(" ")[2]  # весь текст после команды /sendall

    lines = [line.strip() for line in text.splitlines() if line.strip()]
image = None

if lines and lines[0].lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
    image = lines[0]
    text = "\n".join(lines[1:])
else:
    text = "\n".join(lines)


    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            users = f.read().splitlines()
    except FileNotFoundError:
        await update.message.reply_text("Нет зарегистрированных пользователей")
        return

    sent = 0
    failed = 0

    for user_id in users:
        try:
            await send_photo_or_text(context.bot, int(user_id), text, image, admin_id=update.effective_user.id)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1

    await update.message.reply_text(f"✅ Рассылка завершена\nОтправлено: {sent}\nОшибок: {failed}")


# ----------------- ПЕРСОНАЛЬНОЕ СООБЩЕНИЕ -----------------
async def send_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❗ Использование:\n/send <user_id> <текст с абзацами и HTML>")
        return

    user_id = context.args[0]

    text = update.message.text.partition(" ")[2]  # весь текст после команды
    text = text.partition(" ")[2]  # весь текст после user_id

   lines = [line.strip() for line in text.splitlines() if line.strip()]
image = None

if lines and lines[0].lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
    image = lines[0]
    text = "\n".join(lines[1:])
else:
    text = "\n".join(lines)


    try:
        chat = await context.bot.get_chat(int(user_id))
        full_name = f"{chat.first_name} {chat.last_name or ''}".strip()
        personalized_text = f"Привет, {full_name}!\n\n{text}"

        await send_photo_or_text(context.bot, int(user_id), personalized_text, image, admin_id=update.effective_user.id)
        await update.message.reply_text(f"✅ Сообщение отправлено пользователю {user_id}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Не удалось отправить сообщение: {e}")


# ----------------- MAIN -----------------
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
