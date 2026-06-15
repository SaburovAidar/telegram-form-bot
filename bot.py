import logging
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)
from config import TOKEN, ADMIN_ID, ADMIN_IDS

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ENTER, CHOOSE_SVC, CHOOSE_STS = range(3)

# ─── Хранилище ───────────────────────────────────────────────
waiting_users = set()
subscribers = {}    # {tg_id: {username, name, date, source}}
applications = []   # [{name, tg_id, username, text, time, service}]
source_stats = {}   # {source: [tg_ids]}
analytics = {}      # {action: count}
user_analytics = {} # {tg_id: {action: count}}
user_statuses = {}  # {tg_id: {status, service, updated}}

BANNER_URL = "https://i.postimg.cc/TYvHHdHz/image.png"
DIV = "─────────────────────"

# ─── Статусы ─────────────────────────────────────────────────
STATUSES = [
    ("📥 Заявка принята",      "received"),
    ("🔍 Изучается юристом",   "review"),
    ("⚙️ В работе",            "inwork"),
    ("📞 Ожидайте звонка",     "calling"),
    ("✅ Вопрос решён",        "done"),
]
STATUS_LABELS = {code: label for label, code in STATUSES}
STATUS_PROGRESS = {
    "received": "▰▱▱▱▱  20%",
    "review":   "▰▰▱▱▱  40%",
    "inwork":   "▰▰▰▱▱  60%",
    "calling":  "▰▰▰▰▱  80%",
    "done":     "▰▰▰▰▰ 100% ✅",
}

# ─── Тексты ──────────────────────────────────────────────────
WELCOME_TEXT = (
    "🏛  *Единый Юридический Центр Поддержки*\n"
    + DIV + "\n"
    "Приветствуем вас! Наша команда квалифицированных юристов готова оказать профессиональную правовую помощь в самых сложных жизненных ситуациях.\n\n"
    "🔒 *Конфиденциальность · Оперативность · Индивидуальный подход*\n"
    + DIV + "\n"
    "Выберите интересующий вас раздел 👇"
)

MILITARY_TEXT = (
    "🪖  *ВОЕННОЕ ПРАВО*\n"
    + DIV + "\n"
    "Выберите категорию вопроса:"
)

CIVIL_TEXT = (
    "🏛  *ГРАЖДАНСКОЕ ПРАВО*\n"
    + DIV + "\n"
    "Выберите категорию вопроса:"
)

CONSULT_TEXT = (
    "📞  *Оформление заявки*\n"
    + DIV + "\n"
    "Чтобы юрист максимально быстро изучил вашу проблему, отправьте в *одном сообщении*:\n\n"
    "👤  *Ваше имя:*\n"
    "📱  *Контактный телефон:*\n"
    "📝  *Описание ситуации:*\n\n"
    "После отправки дежурный специалист свяжется с вами в течение *15 минут*.\n"
    + DIV
)

SERVICES_INFO = {
    "mil_payouts": (
        "💰  *Выплаты и компенсации*\n"
        + DIV + "\n"
        "• Оспаривание отказов в выплатах при ранениях или травмах\n"
        "• Задержки или неполные начисления денежного довольствия\n"
        "• Страховые выплаты и компенсации членам семей\n"
        "• Помощь в сборе и подаче необходимых документов\n"
        + DIV
    ),
    "mil_family": (
        "👨‍👩‍👧  *Помощь семьям военнослужащих*\n"
        + DIV + "\n"
        "• Юридическая помощь в получении льгот и пособий\n"
        "• Представительство в госорганах по жилищным вопросам\n"
        "• Консультации по кредитным каникулам для семей участников БД\n"
        + DIV
    ),
    "mil_delay": (
        "📋  *Отсрочка и категория годности*\n"
        + DIV + "\n"
        "• Анализ медицинских документов для изменения категории годности (ВВК)\n"
        "• Обжалование незаконных решений о призыве или мобилизации\n"
        "• Юридические основания для получения законной отсрочки\n"
        + DIV
    ),
    "mil_veteran": (
        "📄  *Статус ветерана*\n"
        + DIV + "\n"
        "• Помощь в оформлении удостоверения Ветерана Боевых Действий (ВБД)\n"
        "• Разрешение споров при отсутствии или утере документов\n"
        "• Консультирование по полному пакету ветеранских льгот и выплат\n"
        + DIV
    ),
    "civ_migration": (
        "📄  *ВНЖ и гражданство*\n"
        + DIV + "\n"
        "• Подготовка и аудит документов для получения ВНЖ / ПМЖ\n"
        "• Сопровождение процедуры получения гражданства «под ключ»\n"
        "• Снятие запретов на въезд, обжалование решений миграционных служб\n"
        + DIV
    ),
    "civ_auto": (
        "🚘  *Водительское удостоверение и ДТП*\n"
        + DIV + "\n"
        "• Помощь при угрозе лишения или для возврата водительского удостоверения\n"
        "• Споры со страховыми компаниями (ОСАГО/КАСКО)\n"
        "• Независимая экспертиза и представительство в суде после ДТП\n"
        + DIV
    ),
    "civ_edu": (
        "🎓  *Документы об образовании*\n"
        + DIV + "\n"
        "• Помощь в нострификации иностранных дипломов и аттестатов\n"
        "• Разрешение споров с учебными заведениями\n"
        "• Восстановление утерянных документов об образовании\n"
        + DIV
    ),
    "civ_fraud": (
        "⚖️  *Защита от мошенничества*\n"
        + DIV + "\n"
        "• Защита прав пострадавших от интернет-мошенников\n"
        "• Отмена незаконно оформленных кредитов и микрозаймов\n"
        "• Составление заявлений в полицию, прокуратуру и суд\n"
        + DIV
    ),
}

SERVICE_NAMES = {
    "mil_payouts": "💰 Выплаты и компенсации",
    "mil_family":  "👨‍👩‍👧 Помощь семьям",
    "mil_delay":   "📋 Отсрочка и ВВК",
    "mil_veteran": "📄 Статус ветерана",
    "civ_migration": "📄 ВНЖ и гражданство",
    "civ_auto":    "🚘 Водительские права / ДТП",
    "civ_edu":     "🎓 Документы об образовании",
    "civ_fraud":   "⚖️ Защита от мошенничества",
}

ACTION_NAMES = {
    "menu_military": "🪖 Военное право",
    "menu_civil":    "🏛 Гражданское право",
    "consult":       "📞 Консультация",
    "mil_payouts":   "💰 Выплаты",
    "mil_family":    "👨‍👩‍👧 Семьи военных",
    "mil_delay":     "📋 Отсрочка",
    "mil_veteran":   "📄 Статус ветерана",
    "civ_migration": "📄 ВНЖ/Гражданство",
    "civ_auto":      "🚘 Права/ДТП",
    "civ_edu":       "🎓 Образование",
    "civ_fraud":     "⚖️ Мошенничество",
}

# ─── Утилиты ─────────────────────────────────────────────────
def track(action, uid=None):
    analytics[action] = analytics.get(action, 0) + 1
    if uid:
        u = str(uid)
        if u not in user_analytics:
            user_analytics[u] = {}
        user_analytics[u][action] = user_analytics[u].get(action, 0) + 1

def register_user(user, source=None):
    uid = str(user.id)
    if uid not in subscribers:
        subscribers[uid] = {
            "username": user.username or "",
            "name": (user.first_name or "") + " " + (user.last_name or ""),
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "source": source or "",
        }

def get_hour_greeting():
    h = datetime.now().hour
    if 5 <= h < 12: return "🌅 Доброе утро"
    if 12 <= h < 18: return "☀️ Добрый день"
    if 18 <= h < 23: return "🌆 Добрый вечер"
    return "🌙 Доброй ночи"

# ─── Клавиатуры ──────────────────────────────────────────────
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖  Военные вопросы",    callback_data="menu_military")],
        [InlineKeyboardButton("🏛  Гражданские вопросы", callback_data="menu_civil")],
        [InlineKeyboardButton("📞  Срочная консультация", callback_data="consult")],
    ])

def military_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰  Выплаты и компенсации",  callback_data="srv_mil_payouts")],
        [InlineKeyboardButton("👨‍👩‍👧  Помощь семьям",            callback_data="srv_mil_family")],
        [InlineKeyboardButton("📋  Отсрочка и ВВК",          callback_data="srv_mil_delay")],
        [InlineKeyboardButton("📄  Статус ветерана",          callback_data="srv_mil_veteran")],
        [InlineKeyboardButton("⬅️  Назад в меню",             callback_data="home")],
    ])

def civil_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄  ВНЖ и гражданство",        callback_data="srv_civ_migration")],
        [InlineKeyboardButton("🚘  Водительские права / ДТП", callback_data="srv_civ_auto")],
        [InlineKeyboardButton("🎓  Документы об образовании", callback_data="srv_civ_edu")],
        [InlineKeyboardButton("⚖️  Защита от мошенников",     callback_data="srv_civ_fraud")],
        [InlineKeyboardButton("⬅️  Назад в меню",             callback_data="home")],
    ])

def service_kb(back):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯  Оформить заявку",   callback_data="consult")],
        [InlineKeyboardButton("⬅️  Другой вопрос",     callback_data=back)],
    ])

def cancel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌  Отменить",  callback_data="home")],
    ])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝  Заявки",        callback_data="a_apps"),
         InlineKeyboardButton("📢  Рассылка",      callback_data="a_broadcast")],
        [InlineKeyboardButton("👥  Подписчики",    callback_data="a_subs"),
         InlineKeyboardButton("📈  Статистика",    callback_data="a_stats")],
        [InlineKeyboardButton("🔗  Ссылки",        callback_data="a_links"),
         InlineKeyboardButton("📊  Статус клиента", callback_data="a_status")],
        [InlineKeyboardButton("❌  Закрыть",       callback_data="a_close")],
    ])

# ─── /start ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    source = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("SRC_"):
            source = arg[4:]
            if source not in source_stats:
                source_stats[source] = []
            uid = str(user.id)
            if uid not in source_stats[source]:
                source_stats[source].append(uid)
        elif arg.startswith("REF_"):
            source = "ref_" + arg[4:]

    register_user(user, source)
    waiting_users.discard(user.id)

    greeting = get_hour_greeting()
    caption = greeting + "!\n\n" + WELCOME_TEXT

    await update.message.reply_photo(
        photo=BANNER_URL,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=main_kb(),
    )

# ─── Кнопки ──────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    track(data, user.id)
    register_user(user)

    if data == "home":
        waiting_users.discard(user.id)
        greeting = get_hour_greeting()
        await query.edit_message_caption(
            caption=greeting + "!\n\n" + WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=main_kb(),
        )

    elif data == "menu_military":
        await query.edit_message_caption(
            caption=MILITARY_TEXT, parse_mode="Markdown", reply_markup=military_kb())

    elif data == "menu_civil":
        await query.edit_message_caption(
            caption=CIVIL_TEXT, parse_mode="Markdown", reply_markup=civil_kb())

    elif data.startswith("srv_"):
        key = data[4:]
        text = SERVICES_INFO.get(key, "Информация обновляется...")
        back = "menu_military" if key.startswith("mil_") else "menu_civil"
        track(key, user.id)
        await query.edit_message_caption(
            caption=text, parse_mode="Markdown", reply_markup=service_kb(back))

    elif data == "consult":
        waiting_users.add(user.id)
        context.user_data["consult_service"] = "Не указана"
        await query.edit_message_caption(
            caption=CONSULT_TEXT, parse_mode="Markdown", reply_markup=cancel_kb())

# ─── Приём заявки ────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    if uid not in waiting_users:
        await update.message.reply_text(
            "Используйте меню бота для навигации 👇",
            reply_markup=main_kb())
        return

    service = context.user_data.get("consult_service", "Не указана")
    app_data = {
        "name": (user.first_name or "") + " " + (user.last_name or ""),
        "tg_id": str(uid),
        "username": user.username or "",
        "text": update.message.text,
        "service": service,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    applications.append(app_data)

    admin_text = (
        "🔔  *НОВАЯ ЗАЯВКА*\n"
        + DIV + "\n"
        "👤  Клиент: " + app_data["name"] + "\n"
        "🆔  ID: `" + app_data["tg_id"] + "`\n"
        "📛  @" + (app_data["username"] or "нет username") + "\n"
        "🕐  " + app_data["time"] + "\n"
        + DIV + "\n"
        "📝  *Текст заявки:*\n" + update.message.text
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

    await update.message.reply_text(
        "✅  *Заявка принята!*\n"
        + DIV + "\n"
        "Наш ведущий специалист уже изучает информацию.\n"
        "Мы свяжемся с вами в ближайшее время.\n"
        + DIV + "\n"
        "Среднее время ответа: *15 минут* ⚡",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏛  В главное меню", callback_data="home")
        ]]))

    waiting_users.discard(uid)

# ─── Админ ───────────────────────────────────────────────────
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Нет доступа.")
        return ConversationHandler.END
    await update.message.reply_text(
        "👮  *Админ панель*\n" + DIV + "\nВыберите действие:",
        parse_mode="Markdown", reply_markup=admin_kb())
    return ENTER

async def admin_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "a_close":
        await query.edit_message_text("✅ Закрыто.")
        return ConversationHandler.END

    elif query.data == "a_apps":
        if not applications:
            await query.edit_message_text(
                "📝 Заявок пока нет.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="a_close")]]))
            return ENTER
        text = "📝  *Заявки*\n" + DIV + "\n"
        for i, a in enumerate(applications[-20:][::-1], 1):
            uname = "@" + a["username"] if a["username"] else "—"
            text += (str(i) + ".  " + a["name"] + "  |  " + uname + "\n"
                     "    " + a["time"] + "\n"
                     "    " + a["text"][:80] + ("..." if len(a["text"]) > 80 else "") + "\n\n")
        await query.edit_message_text(
            text[:4000], parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="a_close")]]))
        return ENTER

    elif query.data == "a_broadcast":
        await query.edit_message_text(
            "📢  *Рассылка*\n" + DIV + "\nОтправьте фото или /skip (без фото)\n\n/cancel — отмена",
            parse_mode="Markdown")
        context.user_data["act"] = "bcast_photo"
        return ENTER

    elif query.data == "a_subs":
        await show_subs_page(query, 0)
        return ENTER

    elif query.data.startswith("a_pg_"):
        await show_subs_page(query, int(query.data[5:]))
        return ENTER

    elif query.data.startswith("a_usr_"):
        await show_user(query, query.data[6:])
        return ENTER

    elif query.data.startswith("a_set_"):
        tg_id = query.data[6:]
        context.user_data["target"] = tg_id
        kb = [[InlineKeyboardButton(label, callback_data="a_svc_" + str(i))]
              for i, (label, _) in enumerate(STATUSES)]
        kb.append([InlineKeyboardButton("❌ Отмена", callback_data="a_close")])
        await query.edit_message_text(
            "Выберите статус для " + tg_id + ":",
            reply_markup=InlineKeyboardMarkup(kb))
        return CHOOSE_STS

    elif query.data == "a_links":
        bot_info = await context.bot.get_me()
        kb = [[InlineKeyboardButton("📌 " + src + " — " + str(len(ids)) + " чел.", callback_data="a_lv_" + src)]
              for src, ids in source_stats.items()]
        kb.append([InlineKeyboardButton("➕ Создать ссылку", callback_data="a_link_new")])
        kb.append([InlineKeyboardButton("◀️ Назад", callback_data="a_close")])
        text = "🔗  *Ссылки*\n" + DIV + "\n"
        text += "Ссылок пока нет." if not source_stats else "Всего: *" + str(len(source_stats)) + "*"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return ENTER

    elif query.data == "a_link_new":
        await query.edit_message_text(
            "➕  Введите название источника:\n(vk, tg, insta...)\n\n/cancel — отмена")
        context.user_data["act"] = "new_link"
        return ENTER

    elif query.data.startswith("a_lv_"):
        src = query.data[5:]
        bot_info = await context.bot.get_me()
        link = "https://t.me/" + bot_info.username + "?start=SRC_" + src
        count = len(source_stats.get(src, []))
        await query.edit_message_text(
            "📌  *" + src + "*\n" + DIV + "\n"
            "👥  Переходов: *" + str(count) + "* чел.\n\n"
            "🔗  Ссылка:\n`" + link + "`\n" + DIV,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К ссылкам", callback_data="a_links")]]))
        return ENTER

    elif query.data == "a_status":
        await query.edit_message_text(
            "👤  Введите числовой ID клиента:\n\n/cancel — отмена")
        context.user_data["act"] = "status"
        return ENTER

    elif query.data == "a_stats":
        total = len(subscribers)
        sorted_a = sorted(analytics.items(), key=lambda x: x[1], reverse=True)
        a_text = "".join("  › " + ACTION_NAMES.get(k, k) + ": " + str(v) + "\n" for k, v in sorted_a[:10])
        src_text = "".join("  › " + s + ": " + str(len(ids)) + " чел.\n" for s, ids in source_stats.items())
        await query.edit_message_text(
            "📈  *Статистика*\n" + DIV + "\n"
            "👥  Подписчиков: *" + str(total) + "*\n"
            "📝  Заявок: *" + str(len(applications)) + "*\n"
            + DIV + "\n"
            "🔥  *Топ действий:*\n" + (a_text or "  Нет данных\n") +
            DIV + "\n"
            "🔗  *Источники:*\n" + (src_text or "  Нет данных\n") + DIV,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="a_close")]]))
        return ENTER


async def show_subs_page(query, page=0):
    subs = list(subscribers.items())
    total = len(subs)
    per = 10
    pages = max(1, (total + per - 1) // per)
    page = max(0, min(page, pages - 1))
    chunk = subs[page*per:(page+1)*per]

    text = "👥  Подписчики: " + str(total) + "\n" + DIV + "\n"
    kb = []
    for tg_id, data in chunk:
        name = data["name"].strip() or "—"
        uname = "@" + data["username"] if data["username"] else "—"
        text += name + "  |  " + uname + "\n"
        kb.append([InlineKeyboardButton(name[:20] + " | " + uname[:15], callback_data="a_usr_" + tg_id)])

    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀️", callback_data="a_pg_" + str(page-1)))
    nav.append(InlineKeyboardButton(str(page+1) + "/" + str(pages), callback_data="a_pg_" + str(page)))
    if page < pages-1: nav.append(InlineKeyboardButton("▶️", callback_data="a_pg_" + str(page+1)))
    kb.append(nav)
    kb.append([InlineKeyboardButton("◀️ В меню", callback_data="a_close")])
    await query.edit_message_text(text + DIV, reply_markup=InlineKeyboardMarkup(kb))


async def show_user(query, tg_id):
    sub = subscribers.get(tg_id)
    if not sub:
        await query.edit_message_text("❌ Не найден.")
        return
    name = sub["name"].strip() or "—"
    uname = "@" + sub["username"] if sub["username"] else "—"
    source = sub.get("source", "") or "—"
    status = user_statuses.get(tg_id, {})
    status_text = STATUS_LABELS.get(status.get("status", ""), "Нет статуса")

    user_apps = [a for a in applications if a["tg_id"] == tg_id]
    apps_text = ""
    for a in user_apps[-3:]:
        apps_text += "  › " + a["time"] + ": " + a["text"][:50] + "\n"

    acts = user_analytics.get(tg_id, {})
    a_text = "".join("  › " + ACTION_NAMES.get(k, k) + ": " + str(v) + " раз\n"
                     for k, v in sorted(acts.items(), key=lambda x: x[1], reverse=True)[:6]) if acts else "  Нет данных\n"

    kb = []
    if sub["username"]:
        kb.append([InlineKeyboardButton("✍️ Написать", url="https://t.me/" + sub["username"])])
    kb.append([InlineKeyboardButton("📊 Изменить статус", callback_data="a_set_" + tg_id)])
    kb.append([InlineKeyboardButton("◀️ Назад", callback_data="a_subs")])

    await query.edit_message_text(
        "👤  " + name + "  |  " + uname + "\n" + DIV + "\n"
        "ID: " + tg_id + "\n"
        "Дата: " + sub.get("date", "—") + "\n"
        "Источник: " + source + "\n"
        "Статус: " + status_text + "\n"
        + DIV + "\n"
        "📝  Заявки (" + str(len(user_apps)) + "):\n" + (apps_text or "  Нет заявок\n") +
        DIV + "\n"
        "Активность:\n" + a_text + DIV,
        reply_markup=InlineKeyboardMarkup(kb))


async def admin_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    act = context.user_data.get("act", "")
    text = update.message.text or ""

    if act == "bcast_photo":
        if update.message.photo:
            context.user_data["bcast_photo"] = update.message.photo[-1].file_id
            await update.message.reply_text("✅ Фото получено! Напишите текст:\n\n/cancel — отмена")
        else:
            await update.message.reply_text("📝 Напишите текст рассылки:\n\n/cancel — отмена")
        context.user_data["act"] = "bcast_text"
        return ENTER

    elif act == "bcast_text":
        photo = context.user_data.pop("bcast_photo", None)
        subs = list(subscribers.keys())
        if not subs:
            await update.message.reply_text("❌ Нет подписчиков.")
            return ConversationHandler.END
        msg = await update.message.reply_text("📤 Отправляю " + str(len(subs)) + " подписчикам...")
        ok = fail = 0
        for tg_id in subs:
            try:
                if photo:
                    await context.bot.send_photo(chat_id=int(tg_id), photo=photo,
                        caption="📢  *Сообщение от Юридического Центра:*\n" + DIV + "\n" + text,
                        parse_mode="Markdown")
                else:
                    await context.bot.send_message(chat_id=int(tg_id),
                        text="📢  *Сообщение от Юридического Центра:*\n" + DIV + "\n" + text,
                        parse_mode="Markdown")
                ok += 1
            except: fail += 1
        await msg.edit_text("✅ Готово!\n\n📨 Отправлено: " + str(ok) + "\n❌ Не доставлено: " + str(fail))
        return ConversationHandler.END

    elif act == "new_link":
        src = text.strip().lower().replace(" ", "_")
        if src not in source_stats: source_stats[src] = []
        bot_info = await context.bot.get_me()
        link = "https://t.me/" + bot_info.username + "?start=SRC_" + src
        await update.message.reply_text(
            "✅  *Ссылка создана!*\n" + DIV + "\n"
            "Источник: *" + src + "*\n"
            "Переходов: *0*\n" + DIV + "\n`" + link + "`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ К ссылкам", callback_data="a_links")]]))
        return ConversationHandler.END

    elif act == "status":
        context.user_data["target"] = text.strip()
        kb = [[InlineKeyboardButton(label, callback_data="a_svc_" + str(i))]
              for i, (label, _) in enumerate(STATUSES)]
        kb.append([InlineKeyboardButton("❌ Отмена", callback_data="a_close")])
        await update.message.reply_text(
            "Клиент: *" + text.strip() + "*\n\nВыберите статус:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return CHOOSE_STS

    return ENTER


async def admin_sts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "a_close":
        await query.edit_message_text("✅ Отменено.")
        return ConversationHandler.END
    idx = int(query.data[6:])
    label, code = STATUSES[idx]
    prog = STATUS_PROGRESS.get(code, "")
    target = context.user_data.get("target", "")
    user_statuses[target] = {"status": code, "updated": datetime.now().strftime("%d.%m.%Y %H:%M")}
    try:
        await context.bot.send_message(chat_id=int(target),
            text=("🏛  *Юридический Центр сообщает:*\n" + DIV + "\n"
                  "📌  Статус: " + label + "\n"
                  "📶  Прогресс: " + prog + "\n" + DIV + "\n"
                  "По вопросам обращайтесь через бота."),
            parse_mode="Markdown")
        notify = "✅ Клиент уведомлён!"
    except Exception as e:
        notify = "⚠️ Не удалось: " + str(e)
    await query.edit_message_text(
        "✅  Готово!\n" + DIV + "\nКлиент: " + target + "\nСтатус: " + label + "\n" + DIV + "\n" + notify)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("act") == "bcast_photo":
        context.user_data.pop("bcast_photo", None)
        context.user_data["act"] = "bcast_text"
        await update.message.reply_text("📝 Без фото. Напишите текст:\n\n/cancel — отмена")
        return ENTER
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END


async def post_init(app):
    await app.bot.set_my_commands([BotCommand("start", "Главное меню")])
    from telegram import BotCommandScopeChat
    for aid in ADMIN_IDS:
        try:
            await app.bot.set_my_commands([
                BotCommand("start", "Главное меню"),
                BotCommand("admin", "Админ панель"),
            ], scope=BotCommandScopeChat(chat_id=aid))
        except: pass


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_cmd),
            CallbackQueryHandler(admin_btn, pattern="^a_"),
        ],
        states={
            ENTER: [
                MessageHandler(filters.PHOTO, admin_enter),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_enter),
                CallbackQueryHandler(admin_btn, pattern="^a_"),
            ],
            CHOOSE_STS: [
                CallbackQueryHandler(admin_sts, pattern="^a_svc_"),
                CallbackQueryHandler(admin_sts, pattern="^a_close"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("skip", skip),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Юр бот запущен ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
