import logging
import requests
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)
from config import BOT_TOKEN, CHARACTER_NAME, CHARACTER_DESCRIPTION, CHARACTER_IMAGE_URL, APPS_SCRIPT_URL

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_IDS = [7984349049, 8485739966]

# Состояния
ADMIN_ENTER_USER, ADMIN_CHOOSE_SERVICE, ADMIN_CHOOSE_STATUS = range(3)
BROADCAST_MSG = 10

user_statuses = {}

STATUSES = [
    ("📥 Документы приняты в работу", "accepted"),
    ("⚙️ Документы оформляются", "processing"),
    ("📝 Проводятся экзамены", "exams"),
    ("📦 Документ отправлен", "sent"),
    ("🏛 Ожидается добавление в Госуслуги", "gosuslugi"),
    ("✅ Готово", "done"),
]
STATUS_LABELS = {s[1]: s[0] for s in STATUSES}

SERVICES_LIST = [
    "🪪 Водительские удостоверения",
    "📄 СТС",
    "📋 ПТС",
    "🏫 Документы автошколы",
    "🏥 Медицинская справка",
    "🎓 Диплом",
]


def save_user(tg_id, username, first_name, last_name, ref_by=None):
    try:
        requests.post(APPS_SCRIPT_URL, json={
            "tg_id": str(tg_id),
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "ref_by": str(ref_by) if ref_by else "",
        }, timeout=10)
    except Exception as e:
        print(f"Sheets error: {e}")


def get_subscribers():
    try:
        r = requests.get(APPS_SCRIPT_URL + "?action=list", timeout=10)
        return r.json()
    except Exception as e:
        print(f"Get subs error: {e}")
        return []


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Услуги", callback_data="services")],
        [InlineKeyboardButton("📊 Мой статус", callback_data="my_status")],
        [InlineKeyboardButton("📞 Связаться", callback_data="contact")],
        [InlineKeyboardButton("⭐ Отзывы", callback_data="reviews")],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data="referral")],
    ])


def order_kb(back="services"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Оформить сейчас", url="https://t.me/OlegSergeevichGibdd")],
        [InlineKeyboardButton("◀️ Назад", callback_data=back)],
    ])


# ── /start ────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_by = None

    if context.args:
        try:
            ref_by = int(context.args[0].replace("REF_", ""))
            if ref_by != user.id:
                try:
                    await context.bot.send_message(
                        chat_id=ref_by,
                        text=(
                            f"🎉 По вашей реферальной ссылке пришёл "
                            f"{user.first_name} (@{user.username or 'без username'})!\n\n"
                            f"Когда он оформит заказ — вы получите кешбэк *5000₽* 💰"
                        ),
                        parse_mode="Markdown",
                    )
                except:
                    pass
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"🔗 *Реферал!*\n"
                                f"Пришёл: {user.first_name} (@{user.username or '—'}) | `{user.id}`\n"
                                f"Пригласил: `{ref_by}`"
                            ),
                            parse_mode="Markdown",
                        )
                    except:
                        pass
        except:
            pass

    save_user(user.id, user.username or "", user.first_name or "", user.last_name or "", ref_by)

    # Напоминание через 1 день
    if context.job_queue:
        context.job_queue.run_once(
            reminder_job,
            when=timedelta(days=1),
            data={"chat_id": user.id, "name": user.first_name},
            name=f"reminder_{user.id}",
        )

    caption = (
        f"👋 Меня зовут *{CHARACTER_NAME}*, приятно познакомиться!\n\n"
        f"{CHARACTER_DESCRIPTION}"
    )
    try:
        await update.message.reply_photo(
            photo=CHARACTER_IMAGE_URL,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
    except:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=main_menu())


# ── Напоминание ───────────────────────────────────────────────
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    try:
        await context.bot.send_message(
            chat_id=d["chat_id"],
            text=(
                f"👋 {d['name']}, добрый день!\n\n"
                "Напоминаем — оформление документов занимает от 7 дней.\n"
                "Успейте подать заявку сейчас! ⚡\n\n"
                "📱 Или напишите напрямую: @OlegSergeevichGibdd"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Оформить сейчас", url="https://t.me/OlegSergeevichGibdd")]
            ])
        )
    except Exception as e:
        print(f"Reminder error: {e}")


# ── Кнопки ───────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "back":
        caption = (
            f"👋 Меня зовут *{CHARACTER_NAME}*, приятно познакомиться!\n\n"
            f"{CHARACTER_DESCRIPTION}"
        )
        await query.edit_message_caption(caption=caption, parse_mode="Markdown", reply_markup=main_menu())

    elif query.data == "services":
        kb = [
            [InlineKeyboardButton("🪪 Водительские удостоверения", callback_data="s_vu")],
            [InlineKeyboardButton("📄 СТС", callback_data="s_sts")],
            [InlineKeyboardButton("📋 ПТС", callback_data="s_pts")],
            [InlineKeyboardButton("🏫 Документы автошколы", callback_data="s_avto")],
            [InlineKeyboardButton("🏥 Медицинские справки", callback_data="s_med")],
            [InlineKeyboardButton("🎓 Дипломы | Высшее • Среднее", callback_data="s_diplom")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back")],
        ]
        await query.edit_message_caption(
            caption="📋 *Услуги Олега Сергеевича*\n\nВыберите интересующую услугу:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif query.data == "s_vu":
        await query.edit_message_caption(
            caption=(
                "🪪 *Водительские удостоверения*\n\n"
                "⏱ Срок оформления: *от 7 до 14 дней*\n\n"
                "📎 *Необходимые документы:*\n"
                "• Паспорт\n• Прописка\n• Фото 3×4\n• Фото подписи\n\n"
                "📱 @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown", reply_markup=order_kb(),
        )

    elif query.data == "s_sts":
        await query.edit_message_caption(
            caption=(
                "📄 *СТС — Свидетельство о регистрации ТС*\n\n"
                "⏱ Срок оформления: *от 5 до 10 дней*\n\n"
                "📎 *Необходимые документы:*\n"
                "• Паспорт владельца\n• ПТС автомобиля\n"
                "• Договор купли-продажи\n• Полис ОСАГО\n"
                "• Квитанция об оплате госпошлины\n\n"
                "📱 @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown", reply_markup=order_kb(),
        )

    elif query.data == "s_pts":
        await query.edit_message_caption(
            caption=(
                "📋 *ПТС — Паспорт транспортного средства*\n\n"
                "⏱ Срок оформления: *от 7 до 14 дней*\n\n"
                "📎 *Необходимые документы:*\n"
                "• Паспорт владельца\n• Прописка\n"
                "• VIN номер автомобиля\n"
                "• Документ о праве собственности\n"
                "• Полис ОСАГО\n• Диагностическая карта\n\n"
                "📱 @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown", reply_markup=order_kb(),
        )

    elif query.data == "s_avto":
        await query.edit_message_caption(
            caption=(
                "🏫 *Документы автошколы*\n\n"
                "⏱ Срок оформления: *от 5 до 10 дней*\n\n"
                "📎 *Необходимые документы:*\n"
                "• Паспорт\n• Прописка\n\n"
                "📱 @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown", reply_markup=order_kb(),
        )

    elif query.data == "s_med":
        await query.edit_message_caption(
            caption=(
                "🏥 *Медицинские справки*\n\n"
                "⏱ Срок оформления: *от 1 до 3 дней*\n\n"
                "📎 *Необходимые документы:*\n"
                "• Паспорт\n• Прописка\n\n"
                "📱 @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown", reply_markup=order_kb(),
        )

    elif query.data == "s_diplom":
        await query.edit_message_caption(
            caption=(
                "🎓 *Дипломы | Высшее • Среднее образование*\n\n"
                "⏱ Срок оформления: *от 7 до 14 дней*\n\n"
                "📎 *Необходимые документы:*\n"
                "• Паспорт\n• Прописка\n• СНИЛС\n• Фото 3×4\n\n"
                "📱 @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown", reply_markup=order_kb(),
        )

    elif query.data == "my_status":
        uid = str(user.id)
        if uid in user_statuses:
            s = user_statuses[uid]
            status_text = STATUS_LABELS.get(s["status"], s["status"])
            await query.edit_message_caption(
                caption=(
                    f"📊 *Статус вашей заявки*\n\n"
                    f"🗂 Услуга: {s['service']}\n"
                    f"📌 Статус: {status_text}\n"
                    f"🕐 Обновлено: {s['updated']}"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]),
            )
        else:
            await query.edit_message_caption(
                caption=(
                    "📊 *Статус заявки*\n\n"
                    "У вас пока нет активных заявок.\n\n"
                    "Оформите заявку — и здесь появится статус!\n\n"
                    "📱 @OlegSergeevichGibdd"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ Оформить сейчас", url="https://t.me/OlegSergeevichGibdd")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="back")],
                ]),
            )

    elif query.data == "contact":
        await query.edit_message_caption(
            caption="📞 *Связаться*\n\nНапишите напрямую — отвечаем быстро! ⚡",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Написать Олегу Сергеевичу", url="https://t.me/OlegSergeevichGibdd")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back")],
            ]),
        )

    elif query.data == "reviews":
        await query.edit_message_caption(
            caption="⭐ *Отзывы*\n\nСкоро здесь появятся отзывы клиентов.\n\n📱 @OlegSergeevichGibdd",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]),
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=REF_{user.id}"
        await query.edit_message_caption(
            caption=(
                "👥 *Пригласить друга*\n\n"
                "Поделитесь ссылкой с другом!\n"
                "Когда он оформит заказ — вы получите *кешбэк 5000₽* 💰\n\n"
                f"🔗 Ваша ссылка:\n`{ref_link}`"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]),
        )


# ── /admin ────────────────────────────────────────────────────
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа.")
        return ConversationHandler.END
    await update.message.reply_text(
        "👮 *Админ панель*\n\nВведите @username или ID клиента:",
        parse_mode="Markdown",
    )
    return ADMIN_ENTER_USER


async def admin_enter_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["target"] = update.message.text.strip().replace("@", "")
    kb = [[InlineKeyboardButton(s, callback_data=f"admsvc_{i}")] for i, s in enumerate(SERVICES_LIST)]
    await update.message.reply_text(
        f"✅ Клиент: *{context.user_data['target']}*\n\nВыберите услугу:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return ADMIN_CHOOSE_SERVICE


async def admin_choose_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("admsvc_", ""))
    context.user_data["service"] = SERVICES_LIST[idx]
    kb = [[InlineKeyboardButton(label, callback_data=f"admsts_{code}")] for label, code in STATUSES]
    await query.edit_message_text(
        f"🗂 Услуга: *{context.user_data['service']}*\n\nВыберите статус:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return ADMIN_CHOOSE_STATUS


async def admin_choose_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.replace("admsts_", "")
    label = STATUS_LABELS.get(code, code)
    target = context.user_data["target"]
    service = context.user_data["service"]

    from datetime import datetime
    user_statuses[target] = {
        "service": service,
        "status": code,
        "updated": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }

    try:
        chat_id = int(target) if target.isdigit() else target
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🚔 *Олег Сергеевич сообщает:*\n\n"
                f"🗂 Услуга: {service}\n"
                f"📌 Ваш статус: {label}\n\n"
                "По вопросам пишите: @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown",
        )
        notify = "✅ Клиент уведомлён!"
    except Exception as e:
        notify = f"⚠️ Не удалось уведомить: {e}"

    await query.edit_message_text(
        f"✅ Готово!\n\n👤 Клиент: {target}\n🗂 Услуга: {service}\n📌 Статус: {label}\n\n{notify}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


# ── /broadcast ────────────────────────────────────────────────
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа.")
        return ConversationHandler.END
    await update.message.reply_text(
        "📢 *Рассылка*\n\nНапишите сообщение которое получат все подписчики.\n\n/cancel — отмена",
        parse_mode="Markdown",
    )
    return BROADCAST_MSG


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    subs = get_subscribers()
    if not subs:
        await update.message.reply_text("❌ Нет подписчиков.")
        return ConversationHandler.END

    await update.message.reply_text(f"📤 Отправляю {len(subs)} подписчикам...")

    success = 0
    fail = 0
    for sub in subs:
        try:
            await context.bot.send_message(
                chat_id=int(sub["tg_id"]),
                text=f"📢 *Сообщение от Олега Сергеевича:*\n\n{text}",
                parse_mode="Markdown",
            )
            success += 1
        except:
            fail += 1

    await update.message.reply_text(
        f"✅ Рассылка завершена!\n\n"
        f"📨 Отправлено: {success}\n"
        f"❌ Не доставлено: {fail}"
    )
    return ConversationHandler.END


# ── /stats ────────────────────────────────────────────────────
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа.")
        return
    subs = get_subscribers()
    if not subs:
        await update.message.reply_text("📊 Подписчиков пока нет.")
        return
    total = len(subs)
    text = f"📊 *Подписчики: {total}*\n\n"
    for i, sub in enumerate(subs[:50], 1):
        username = f"@{sub['username']}" if sub.get('username') else "—"
        name = (sub.get('first_name', '') + " " + sub.get('last_name', '')).strip()
        text += f"{i}. {name} | {username} | `{sub.get('tg_id', '')}`\n"
    if total > 50:
        text += f"\n_...и ещё {total - 50}. Смотри таблицу._"
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Запуск ────────────────────────────────────────────────────
async def post_init(app):
    # Обычные пользователи — только базовые команды
    await app.bot.set_my_commands([
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("status", "📊 Мой статус заявки"),
        BotCommand("services", "📋 Услуги"),
        BotCommand("contact", "📞 Связаться"),
    ])
    # Админы — видят все команды
    from telegram import BotCommandScopeChat
    for admin_id in ADMIN_IDS:
        try:
            await app.bot.set_my_commands([
                BotCommand("start", "🏠 Главное меню"),
                BotCommand("status", "📊 Мой статус заявки"),
                BotCommand("services", "📋 Услуги"),
                BotCommand("contact", "📞 Связаться"),
                BotCommand("admin", "👮 Админ панель"),
                BotCommand("broadcast", "📢 Рассылка"),
                BotCommand("stats", "📈 Статистика"),
            ], scope=BotCommandScopeChat(chat_id=admin_id))
        except:
            pass


async def services_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🪪 Водительские удостоверения", callback_data="s_vu")],
        [InlineKeyboardButton("📄 СТС", callback_data="s_sts")],
        [InlineKeyboardButton("📋 ПТС", callback_data="s_pts")],
        [InlineKeyboardButton("🏫 Документы автошколы", callback_data="s_avto")],
        [InlineKeyboardButton("🏥 Медицинские справки", callback_data="s_med")],
        [InlineKeyboardButton("🎓 Дипломы | Высшее • Среднее", callback_data="s_diplom")],
    ]
    await update.message.reply_text(
        "📋 *Услуги Олега Сергеевича*\n\nВыберите интересующую услугу:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Связаться*\n\nНапишите напрямую — отвечаем быстро! ⚡",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Написать Олегу Сергеевичу", url="https://t.me/OlegSergeevichGibdd")],
        ]),
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid in user_statuses:
        s = user_statuses[uid]
        status_text = STATUS_LABELS.get(s["status"], s["status"])
        await update.message.reply_text(
            f"📊 *Статус вашей заявки*\n\n"
            f"🗂 Услуга: {s['service']}\n"
            f"📌 Статус: {status_text}\n"
            f"🕐 Обновлено: {s['updated']}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "📊 У вас пока нет активных заявок.\n\n📱 @OlegSergeevichGibdd",
        )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_ENTER_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_enter_user)],
            ADMIN_CHOOSE_SERVICE: [CallbackQueryHandler(admin_choose_service, pattern="^admsvc_")],
            ADMIN_CHOOSE_STATUS: [CallbackQueryHandler(admin_choose_status, pattern="^admsts_")],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
    )

    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("services", services_cmd))
    app.add_handler(CommandHandler("contact", contact_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(admin_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущено ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
