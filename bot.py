from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8408634586:AAFC1aIugJxY3jdI1rgYUcTPXU1gozSj5pw"

# Хранилище состояний пользователей
user_state = {}

# Файл для сохранения заявок
DATA_FILE = "registrations.txt"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    first_name = update.message.from_user.first_name

    text = (
        f"{first_name}, добро пожаловать в бот SMI 👋\n\n"
        "Он поможет вам зарегистрироваться на вебинар\n"
        "«Инструменты инвестиций в 2026 году» и получить подарок – Инструкцию для новичков "
        "\"Как открыть счет для торгов и правильно выбрать платформу/банк\" 🎁\n\n"
        "Чтобы завершить регистрацию, нажмите кнопку ниже 👇"
    )

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📲 Отправить имя и телефон", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(text, reply_markup=keyboard)
    user_state[update.effective_user.id] = "WAIT_CONTACT"


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

    # Убираем клавиатуру
    await update.message.reply_text("Спасибо! Регистрируем вас...")

    # Сообщение 2
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

    await update.message.reply_text(text, reply_markup=keyboard)

    user_state[user_id] = "DONE"


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, нажмите кнопку для отправки контакта ☝️")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    app.run_polling()


if __name__ == "__main__":
    main()
