from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TOKEN, ADMIN_ID

waiting_users = set()


WELCOME = """
⚖️ ЮРИДИЧЕСКИЙ ЦЕНТР ПОДДЕРЖКИ

🪖 Помощь военнослужащим
🏛 Помощь гражданским
📞 Консультации специалистов

Выберите раздел ниже:
"""


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 Военные вопросы", callback_data="military")],
        [InlineKeyboardButton("🏛 Гражданские вопросы", callback_data="civil")],
        [InlineKeyboardButton("📞 Получить консультацию", callback_data="consult")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME,
        reply_markup=main_menu()
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "home":
        await query.edit_message_text(
            WELCOME,
            reply_markup=main_menu()
        )

    elif query.data == "military":
        await query.edit_message_text(
            """
🪖 ВОЕННЫЕ ВОПРОСЫ

💰 Выплаты и компенсации
👨‍👩‍👧 Помощь семьям военнослужащих
📋 Отсрочка и категория годности
📄 Статус ветерана

Для связи нажмите «Консультация».
""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Консультация", callback_data="consult")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="home")]
            ])
        )

    elif query.data == "civil":
        await query.edit_message_text(
            """
🏛 ГРАЖДАНСКИЕ ВОПРОСЫ

📄 ВНЖ и гражданство
🚘 Водительское удостоверение
🎓 Документы об образовании
⚖️ Защита от мошенничества

Для связи нажмите «Консультация».
""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Консультация", callback_data="consult")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="home")]
            ])
        )

    elif query.data == "consult":
        waiting_users.add(query.from_user.id)

        await query.edit_message_text(
            """
📞 ОТПРАВКА ЗАЯВКИ

Напишите одним сообщением:

Имя:
Телефон:
Описание ситуации:

Сообщение будет отправлено специалисту.
"""
        )


async def application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in waiting_users:
        return

    user = update.effective_user

    text = f"""
🔥 НОВАЯ ЗАЯВКА

👤 {user.full_name}
🆔 {user.id}
📛 @{user.username}

-------------------

{update.message.text}
"""

    await context.bot.send_message(
        ADMIN_ID,
        text
    )

    await update.message.reply_text(
        "✅ Заявка отправлена. Ожидайте ответа специалиста."
    )

    waiting_users.remove(user_id)


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            application
        )
    )

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
