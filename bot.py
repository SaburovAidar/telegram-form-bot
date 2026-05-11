import logging
import requests
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)
from telegram.constants import ChatAction
from config import BOT_TOKEN, CHARACTER_NAME, CHARACTER_DESCRIPTION, CHARACTER_IMAGE_URL, APPS_SCRIPT_URL

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_IDS = [7984349049, 8485739966]
ADMIN_ENTER_USER, ADMIN_CHOOSE_SERVICE, ADMIN_CHOOSE_STATUS = range(3)

user_statuses = {}
source_stats = {}

STATUSES = [
    ("📥 Документы приняты в работу", "accepted"),
    ("⚙️ Документы оформляются", "processing"),
    ("📝 Проводятся экзамены", "exams"),
    ("📦 Документ отправлен", "sent"),
    ("🏛 Ожидается добавление в Госуслуги", "gosuslugi"),
    ("✅ Готово", "done"),
]
STATUS_PROGRESS = {
    "accepted":   "▓░░░░░ 10%",
    "processing": "▓▓▓░░░ 40%",
    "exams":      "▓▓▓▓░░ 60%",
    "sent":       "▓▓▓▓▓░ 80%",
    "gosuslugi":  "▓▓▓▓▓▓ 95%",
    "done":       "▓▓▓▓▓▓ 100% ✅",
}
STATUS_LABELS = {s[1]: s[0] for s in STATUSES}

SERVICES_LIST = [
    "🪪 Водительские удостоверения",
    "🚜 Тракторные права",
    "📄 СТС",
    "📋 ПТС",
    "🏫 Документы автошколы",
    "🏥 Медицинская справка",
    "🎓 Диплом",
]

SERVICE_PHOTOS = {
    "s_vu":      "https://i.postimg.cc/65wrGwPB/1.png",
    "s_traktor": "https://i.postimg.cc/wMzmJc07/traktor.png",
    "s_sts":     "https://i.postimg.cc/DyjSyTkw/sts.png",
    "s_avto":    "https://i.postimg.cc/ZqyBMDQR/Avtoskola.jpg",
    "s_med":     "https://i.postimg.cc/90cDzXQv/Med.jpg",
}

SERVICE_TEXTS = {
    "s_vu": (
        "🪪 *Водительские удостоверения*\n"
        "━━━━━━━━━━━━━━━━\n"
        "⏱ Срок: *от 7 до 14 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт\n› Прописка\n› Фото 3×4\n› Фото подписи\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
    "s_traktor": (
        "🚜 *Тракторные права*\n"
        "━━━━━━━━━━━━━━━━\n"
        "📋 Категории: *A • B • C • D • E • F*\n"
        "⏱ Срок: *до 15 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт\n› Прописка\n› Фото 3×4\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
    "s_sts": (
        "📄 *СТС — Свидетельство о регистрации ТС*\n"
        "━━━━━━━━━━━━━━━━\n"
        "⏱ Срок: *от 5 до 10 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт владельца\n› ПТС автомобиля\n"
        "› Договор купли-продажи\n› Полис ОСАГО\n"
        "› Квитанция госпошлины\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
    "s_pts": (
        "📋 *ПТС — Паспорт транспортного средства*\n"
        "━━━━━━━━━━━━━━━━\n"
        "⏱ Срок: *от 7 до 14 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт владельца\n› Прописка\n"
        "› VIN номер автомобиля\n"
        "› Документ о праве собственности\n"
        "› Полис ОСАГО\n› Диагностическая карта\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
    "s_avto": (
        "🏫 *Документы автошколы*\n"
        "━━━━━━━━━━━━━━━━\n"
        "⏱ Срок: *от 5 до 10 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт\n› Прописка\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
    "s_med": (
        "🏥 *Медицинские справки*\n"
        "━━━━━━━━━━━━━━━━\n"
        "⏱ Срок: *от 1 до 3 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт\n› Прописка\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
    "s_diplom": (
        "🎓 *Дипломы | Высшее • Среднее образование*\n"
        "━━━━━━━━━━━━━━━━\n"
        "⏱ Срок: *от 7 до 14 дней*\n\n"
        "📎 *Необходимые документы:*\n"
        "› Паспорт\n› Прописка\n› СНИЛС\n› Фото 3×4\n"
        "━━━━━━━━━━━━━━━━\n"
        "📱 @OlegSergeevichGibdd"
    ),
}

GREETINGS = [
    "👋 Рад видеть тебя, {name}!",
    "🤝 Привет, {name}! Обращайся — помогу!",
    "🚔 {name}, добро пожаловать!",
    "💼 Здравствуй, {name}! Готов помочь.",
    "⚡ {name}, на связи Олег Сергеевич!",
]

def get_greeting(name):
    hour = datetime.now().hour
    if 5 <= hour < 12:
        time_g = "Доброе утро"
    elif 12 <= hour < 18:
        time_g = "Добрый день"
    elif 18 <= hour < 23:
        time_g = "Добрый вечер"
    else:
        time_g = "Доброй ночи"
    phrase = random.choice(GREETINGS).format(name=name)
    return f"{phrase}\n_{time_g}!_"


def save_user(tg_id, username, first_name, last_name, ref_by=None, source=None):
    try:
        requests.post(APPS_SCRIPT_URL, json={
            "tg_id": str(tg_id),
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "ref_by": str(ref_by) if ref_by else "",
            "source": source or "",
        }, timeout=10)
    except Exception as e:
        print(f"Sheets error: {e}")


def load_sources_from_sheet():
    try:
        r = requests.get(APPS_SCRIPT_URL + "?action=sources", timeout=15)
        data = r.json()
        for src, ids in data.items():
            source_stats[src] = ids
        print(f"Loaded {len(source_stats)} sources from sheet")
    except Exception as e:
        print(f"Load sources error: {e}")


def save_source_to_sheet(source, tg_id):
    try:
        requests.post(APPS_SCRIPT_URL, json={
            "action": "add_source",
            "source": source,
            "tg_id": str(tg_id),
        }, timeout=10)
    except Exception as e:
        print(f"Save source error: {e}")


def ensure_source_exists(source):
    if source not in source_stats:
        source_stats[source] = []


def get_subscribers():
    try:
        r = requests.get(APPS_SCRIPT_URL + "?action=list", timeout=15)
        return r.json()
    except Exception as e:
        print(f"Get subs error: {e}")
        return []


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Услуги", callback_data="services"),
         InlineKeyboardButton("📊 Мой статус", callback_data="my_status")],
        [InlineKeyboardButton("📞 Связаться", callback_data="contact"),
         InlineKeyboardButton("⭐ Отзывы", callback_data="reviews")],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data="referral")],
    ])


def order_kb(back="services"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Оформить сейчас", url="https://t.me/OlegSergeevichGibdd")],
        [InlineKeyboardButton("◀️ Назад", callback_data=back)],
    ])


async def send_service(query, key):
    text = SERVICE_TEXTS.get(key, "")
    kb = order_kb()
    photo = SERVICE_PHOTOS.get(key)
    if photo:
        try:
            import telegram
            await query.edit_message_media(
                media=telegram.InputMediaPhoto(media=photo, caption=text, parse_mode="Markdown"),
                reply_markup=kb,
            )
            return
        except:
            pass
    try:
        await query.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=kb)
    except:
        await query.edit_message_text(text=text, parse_mode="Markdown", reply_markup=kb)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_by = None

    if context.args:
        arg = context.args[0]
        if arg.startswith("SRC_"):
            source = arg.replace("SRC_", "")
            ensure_source_exists(source)
            if str(user.id) not in source_stats[source]:
                source_stats[source].append(str(user.id))
                save_source_to_sheet(source, user.id)
        elif arg.startswith("REF_"):
            try:
                ref_by = int(arg.replace("REF_", ""))
                if ref_by != user.id:
                    try:
                        await context.bot.send_message(
                            chat_id=ref_by,
                            text=(
                                "🎉 По вашей реферальной ссылке пришёл "
                                f"{user.first_name} (@{user.username or 'без username'})!\n\n"
                                "Когда он оформит заказ — вы получите кешбэк *5000₽* 💰"
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
                                    "🔗 *Реферал!*\n"
                                    f"Пришёл: {user.first_name} (@{user.username or '—'}) | `{user.id}`\n"
                                    f"Пригласил: `{ref_by}`"
                                ),
                                parse_mode="Markdown",
                            )
                        except:
                            pass
            except:
                pass

    save_user(user.id, user.username or "", user.first_name or "", user.last_name or "", ref_by, source if context.args and context.args[0].startswith("SRC_") else None)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    if context.job_queue:
        jobs = context.job_queue.get_jobs_by_name(f"reminder_{user.id}")
        if not jobs:
            context.job_queue.run_once(
                reminder_job,
                when=timedelta(days=1),
                data={"chat_id": user.id, "name": user.first_name},
                name=f"reminder_{user.id}",
            )

    greeting = get_greeting(user.first_name)
    caption = (
        f"{greeting}\n\n"
        f"Я *{CHARACTER_NAME}*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{CHARACTER_DESCRIPTION}\n"
        "━━━━━━━━━━━━━━━━\n"
        "Выберите что вас интересует 👇"
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


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    try:
        await context.bot.send_message(
            chat_id=d["chat_id"],
            text=(
                f"👋 {d['name']}, добрый день!\n"
                "━━━━━━━━━━━━━━━━\n"
                "Напоминаем — оформление документов\n"
                "занимает от 7 дней.\n\n"
                "⚡ Успейте подать заявку сейчас!\n"
                "━━━━━━━━━━━━━━━━\n"
                "📱 @OlegSergeevichGibdd"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Оформить сейчас", url="https://t.me/OlegSergeevichGibdd")]
            ])
        )
    except Exception as e:
        print(f"Reminder error: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "back":
        greeting = get_greeting(user.first_name)
        caption = (
            f"{greeting}\n\n"
            f"Я *{CHARACTER_NAME}*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"{CHARACTER_DESCRIPTION}\n"
            "━━━━━━━━━━━━━━━━\n"
            "Выберите что вас интересует 👇"
        )
        try:
            import telegram
            await query.edit_message_media(
                media=telegram.InputMediaPhoto(
                    media=CHARACTER_IMAGE_URL, caption=caption, parse_mode="Markdown"
                ),
                reply_markup=main_menu(),
            )
        except:
            try:
                await query.edit_message_caption(caption=caption, parse_mode="Markdown", reply_markup=main_menu())
            except:
                pass

    elif query.data == "services":
        kb = [
            [InlineKeyboardButton("🪪 Водительские удостоверения", callback_data="s_vu")],
            [InlineKeyboardButton("🚜 Тракторные права", callback_data="s_traktor")],
            [InlineKeyboardButton("📄 СТС", callback_data="s_sts"),
             InlineKeyboardButton("📋 ПТС", callback_data="s_pts")],
            [InlineKeyboardButton("🏫 Документы автошколы", callback_data="s_avto")],
            [InlineKeyboardButton("🏥 Медицинские справки", callback_data="s_med")],
            [InlineKeyboardButton("🎓 Дипломы | Высшее / Среднее", callback_data="s_diplom")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back")],
        ]
        await query.edit_message_caption(
            caption="📋 *Услуги Олега Сергеевича*\n━━━━━━━━━━━━━━━━\nВыберите интересующую услугу:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif query.data in SERVICE_TEXTS:
        await send_service(query, query.data)

    elif query.data == "my_status":
        uid = str(user.id)
        if uid in user_statuses:
            s = user_statuses[uid]
            status_text = STATUS_LABELS.get(s["status"], s["status"])
            progress = STATUS_PROGRESS.get(s["status"], "")
            await query.edit_message_caption(
                caption=(
                    "📊 *Статус вашей заявки*\n"
                    "━━━━━━━━━━━━━━━━\n"
                    f"🗂 Услуга: {s['service']}\n"
                    f"📌 Статус: {status_text}\n"
                    f"📶 Прогресс: `{progress}`\n"
                    f"🕐 Обновлено: {s['updated']}\n"
                    "━━━━━━━━━━━━━━━━"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]),
            )
        else:
            await query.edit_message_caption(
                caption=(
                    "📊 *Статус заявки*\n"
                    "━━━━━━━━━━━━━━━━\n"
                    "У вас пока нет активных заявок.\n\n"
                    "Оформите заявку — и здесь появится статус!\n"
                    "━━━━━━━━━━━━━━━━\n"
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
            caption=(
                "📞 *Связаться*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Напишите напрямую — отвечаем быстро!\n\n"
                "⚡ Среднее время ответа: *до 15 минут*\n"
                "━━━━━━━━━━━━━━━━"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Написать Олегу Сергеевичу", url="https://t.me/OlegSergeevichGibdd")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back")],
            ]),
        )

    elif query.data == "reviews":
        await query.edit_message_caption(
            caption=(
                "⭐ *Отзывы клиентов*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Скоро здесь появятся отзывы.\n\n"
                "📱 @OlegSergeevichGibdd\n"
                "━━━━━━━━━━━━━━━━"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]),
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=REF_{user.id}"
        await query.edit_message_caption(
            caption=(
                "👥 *Пригласить друга*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Поделитесь ссылкой с другом!\n\n"
                "💰 Когда он оформит заказ —\n"
                "вы получите *кешбэк 5000₽*\n"
                "━━━━━━━━━━━━━━━━\n"
                f"🔗 Ваша ссылка:\n`{ref_link}`"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]]),
        )


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа.")
        return ConversationHandler.END

    kb = [
        [InlineKeyboardButton("📊 Статус клиента", callback_data="adm_status"),
         InlineKeyboardButton("📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton("👥 Подписчики", callback_data="adm_subs"),
         InlineKeyboardButton("📈 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton("🔗 Ссылки", callback_data="adm_links")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="adm_close")],
    ]
    await update.message.reply_text(
        "👮 *Админ панель*\n"
        "━━━━━━━━━━━━━━━━\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return ADMIN_ENTER_USER


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "adm_close":
        await query.edit_message_text("✅ Панель закрыта.")
        return ConversationHandler.END

    elif query.data == "adm_status":
        await query.edit_message_text("👤 Введите ID клиента (числовой):\n\n/cancel — отмена")
        context.user_data["admin_action"] = "status"
        return ADMIN_ENTER_USER

    elif query.data == "adm_broadcast":
        await query.edit_message_text(
            "📢 *Рассылка*\n\nНапишите текст сообщения:\n\n/cancel — отмена",
            parse_mode="Markdown",
        )
        context.user_data["admin_action"] = "broadcast"
        return ADMIN_ENTER_USER

    elif query.data == "adm_links":
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        if not source_stats:
            await query.edit_message_text(
                "🔗 *Ссылки для отслеживания*\n"
                "━━━━━━━━━━━━━━━━\n"
                "Ссылок пока нет.\n\n"
                "Введите название источника\n"
                "(например: instagram, vk, kanal):\n\n"
                "/cancel — отмена",
                parse_mode="Markdown",
            )
        else:
            text = "🔗 *Ссылки и статистика*\n━━━━━━━━━━━━━━━━\n"
            for src, ids in source_stats.items():
                link = f"t.me/{bot_username}?start=SRC_{src}"
                text += f"📌 *{src}*: {len(ids)} чел.\n`{link}`\n\n"
            text += "━━━━━━━━━━━━━━━━\nВведите название для новой ссылки:\n\n/cancel — отмена"
            await query.edit_message_text(text[:4000], parse_mode="Markdown")
        context.user_data["admin_action"] = "create_link"
        return ADMIN_ENTER_USER

    elif query.data.startswith("adm_link_view_"):
        src = query.data.replace("adm_link_view_", "")
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start=SRC_{src}"
        count = len(source_stats.get(src, []))
        kb = [
            [InlineKeyboardButton("◀️ К ссылкам", callback_data="adm_links")],
        ]
        await query.edit_message_text(
            "📌 *" + src + "*\n━━━━━━━━━━━━━━━━\n👥 Переходов: *" + str(count) + "* чел.\n\n🔗 Ссылка:\n`" + link + "`\n━━━━━━━━━━━━━━━━\n_Скопируйте и разместите где нужно_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return ADMIN_ENTER_USER

    elif query.data == "adm_subs":
        subs = get_subscribers()
        total = len(subs)
        text = f"👥 *Подписчики: {total}*\n━━━━━━━━━━━━━━━━\n"
        for i, sub in enumerate(subs[:30], 1):
            username = f"@{sub['username']}" if sub.get('username') else "—"
            name = (sub.get('first_name', '') + " " + sub.get('last_name', '')).strip() or "—"
            text += f"{i}. {name} | {username} | `{sub.get('tg_id', '')}`\n"
        if total > 30:
            text += f"\n_...и ещё {total - 30}. Смотри таблицу._"
        await query.edit_message_text(text[:4000], parse_mode="Markdown")
        return ConversationHandler.END

    elif query.data == "adm_stats":
        subs = get_subscribers()
        total = len(subs)
        active = len(user_statuses)
        src_text = ""
        for src, ids in source_stats.items():
            src_text += f"  › {src}: {len(ids)} чел.\n"
        await query.edit_message_text(
            "📈 *Статистика*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👥 Подписчиков: *{total}*\n"
            f"📊 Активных заявок: *{active}*\n"
            f"🔗 Источников: *{len(source_stats)}*\n"
            f"{src_text}"
            "━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
        )
        return ConversationHandler.END


async def admin_enter_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("admin_action")

    if action == "create_link":
        source_name = update.message.text.strip().lower().replace(" ", "_")
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        link = f"https://t.me/{bot_username}?start=SRC_{source_name}"
        count = len(source_stats.get(source_name, []))
        await update.message.reply_text(
            "✅ *Ссылка создана!*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"📌 Источник: *{source_name}*\n"
            f"👥 Переходов: *{count}*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🔗 Ваша ссылка:\n`{link}`\n\n"
            "_Скопируйте и разместите где нужно_",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    elif action == "broadcast":
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
                    text="📢 *Сообщение от Олега Сергеевича:*\n━━━━━━━━━━━━━━━━\n" + text,
                    parse_mode="Markdown",
                )
                success += 1
            except:
                fail += 1
        await update.message.reply_text(
            f"✅ *Рассылка завершена!*\n\n📨 Отправлено: {success}\n❌ Не доставлено: {fail}",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    else:
        context.user_data["target"] = update.message.text.strip().replace("@", "")
        kb = [[InlineKeyboardButton(s, callback_data=f"admsvc_{i}")] for i, s in enumerate(SERVICES_LIST)]
        kb.append([InlineKeyboardButton("❌ Отмена", callback_data="adm_close")])
        await update.message.reply_text(
            f"✅ Клиент: *{context.user_data['target']}*\n\nВыберите услугу:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return ADMIN_CHOOSE_SERVICE


async def admin_choose_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "adm_close":
        await query.edit_message_text("✅ Отменено.")
        return ConversationHandler.END
    idx = int(query.data.replace("admsvc_", ""))
    context.user_data["service"] = SERVICES_LIST[idx]
    kb = [[InlineKeyboardButton(label, callback_data=f"admsts_{code}")] for label, code in STATUSES]
    kb.append([InlineKeyboardButton("❌ Отмена", callback_data="adm_close")])
    await query.edit_message_text(
        f"🗂 Услуга: *{context.user_data['service']}*\n\nВыберите статус:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return ADMIN_CHOOSE_STATUS


async def admin_choose_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "adm_close":
        await query.edit_message_text("✅ Отменено.")
        return ConversationHandler.END
    code = query.data.replace("admsts_", "")
    label = STATUS_LABELS.get(code, code)
    progress = STATUS_PROGRESS.get(code, "")
    target = context.user_data["target"]
    service = context.user_data["service"]

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
                "🚔 *Олег Сергеевич сообщает:*\n"
                "━━━━━━━━━━━━━━━━\n"
                f"🗂 Услуга: {service}\n"
                f"📌 Статус: {label}\n"
                f"📶 Прогресс: `{progress}`\n"
                "━━━━━━━━━━━━━━━━\n"
                "По вопросам: @OlegSergeevichGibdd"
            ),
            parse_mode="Markdown",
        )
        notify = "✅ Клиент уведомлён!"
    except Exception as e:
        notify = f"⚠️ Не удалось уведомить: {e}"

    await query.edit_message_text(
        "✅ *Готово!*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👤 Клиент: `{target}`\n"
        f"🗂 Услуга: {service}\n"
        f"📌 Статус: {label}\n"
        f"📶 `{progress}`\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{notify}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа.")
        return
    subs = get_subscribers()
    total = len(subs)
    text = f"📊 *Подписчики: {total}*\n━━━━━━━━━━━━━━━━\n"
    for i, sub in enumerate(subs[:50], 1):
        username = f"@{sub['username']}" if sub.get('username') else "—"
        name = (sub.get('first_name', '') + " " + sub.get('last_name', '')).strip() or "—"
        text += f"{i}. {name} | {username} | `{sub.get('tg_id', '')}`\n"
    if total > 50:
        text += f"\n_...и ещё {total - 50}._"
    await update.message.reply_text(text[:4000], parse_mode="Markdown")


async def services_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🪪 Водительские удостоверения", callback_data="s_vu")],
        [InlineKeyboardButton("🚜 Тракторные права", callback_data="s_traktor")],
        [InlineKeyboardButton("📄 СТС", callback_data="s_sts"),
         InlineKeyboardButton("📋 ПТС", callback_data="s_pts")],
        [InlineKeyboardButton("🏫 Документы автошколы", callback_data="s_avto")],
        [InlineKeyboardButton("🏥 Медицинские справки", callback_data="s_med")],
        [InlineKeyboardButton("🎓 Дипломы | Высшее / Среднее", callback_data="s_diplom")],
    ]
    await update.message.reply_text(
        "📋 *Услуги Олега Сергеевича*\n━━━━━━━━━━━━━━━━\nВыберите услугу:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Связаться*\n━━━━━━━━━━━━━━━━\nОтвечаем быстро! ⚡",
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
        progress = STATUS_PROGRESS.get(s["status"], "")
        await update.message.reply_text(
            "📊 *Статус заявки*\n━━━━━━━━━━━━━━━━\n"
            f"🗂 Услуга: {s['service']}\n"
            f"📌 Статус: {status_text}\n"
            f"📶 `{progress}`\n"
            f"🕐 {s['updated']}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("📊 Активных заявок нет.\n\n📱 @OlegSergeevichGibdd")


async def post_init(app):
    load_sources_from_sheet()
    await app.bot.set_my_commands([
        BotCommand("start", "🏠 Главное меню"),
        BotCommand("status", "📊 Мой статус"),
        BotCommand("services", "📋 Услуги"),
        BotCommand("contact", "📞 Связаться"),
    ])
    from telegram import BotCommandScopeChat
    for admin_id in ADMIN_IDS:
        try:
            await app.bot.set_my_commands([
                BotCommand("start", "🏠 Главное меню"),
                BotCommand("status", "📊 Мой статус"),
                BotCommand("services", "📋 Услуги"),
                BotCommand("contact", "📞 Связаться"),
                BotCommand("admin", "👮 Админ панель"),
                BotCommand("stats", "📈 Статистика"),
            ], scope=BotCommandScopeChat(chat_id=admin_id))
        except:
            pass


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_start),
            CallbackQueryHandler(admin_panel_handler, pattern="^adm_"),
        ],
        states={
            ADMIN_ENTER_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_enter_user),
                CallbackQueryHandler(admin_panel_handler, pattern="^adm_"),
            ],
            ADMIN_CHOOSE_SERVICE: [
                CallbackQueryHandler(admin_choose_service, pattern="^admsvc_"),
                CallbackQueryHandler(admin_choose_service, pattern="^adm_close"),
            ],
            ADMIN_CHOOSE_STATUS: [
                CallbackQueryHandler(admin_choose_status, pattern="^admsts_"),
                CallbackQueryHandler(admin_choose_status, pattern="^adm_close"),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("services", services_cmd))
    app.add_handler(CommandHandler("contact", contact_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущено ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
