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

# Хранилище пользователей, ожидающих отправку заявки
waiting_users = set()

# URL баннера
BANNER_URL = "https://i.postimg.cc/zvkY0dn5/image.png"

# --- ТЕКСТОВЫЕ БЛОКИ (КОПИРАЙТИНГ) ---

WELCOME_TEXT = """
🏛 **Единый Юридический Центр Поддержки**

Приветствуем вас! Наша команда квалифицированных юристов готова оказать профессиональную правовую помощь в самых сложных жизненных ситуациях.

🔒 *Гарантируем конфиденциальность, оперативность и индивидуальный подход к каждому делу.*

Выберите интересующий вас раздел ниже:
"""

MILITARY_TEXT = "🪖 **НАПРАВЛЕНИЕ: ВОЕННОЕ ПРАВО**\n\nВыберите конкретную категорию вопроса, чтобы узнать детали:"
CIVIL_TEXT = "🏛 **НАПРАВЛЕНИЕ: ГРАЖДАНСКОЕ ПРАВО**\n\nВыберите конкретную категорию вопроса, чтобы узнать детали:"

CONSULT_TEXT = """
📞 **ОФОРМЛЕНИЕ ЗАЯВКИ НА КОНСУЛЬТАЦИЮ**

Чтобы юрист максимально быстро и подробно изучил вашу проблему, отправьте в **одном сообщении** следующую информацию:

👤 **Ваше Имя:** 📱 **Контактный телефон:** 📝 **Описание ситуации:** (кратко изложите суть вашего вопроса)

После отправки дежурный специалист свяжется с вами в течение 15 минут.
"""

# Описания конкретных услуг
SERVICES_INFO = {
    # Военные
    "mil_payouts": """
💰 **ВЫПЛАТЫ И КОМПЕНСАЦИИ**

Полное юридическое сопровождение по получению положенных выплат:
• Оспаривание отказов в выплатах при ранениях или травмах.
• Задержки или неполные начисления денежного довольствия.
• Страховые выплаты и компенсации членам семей.
• Помощь в сборе и подаче необходимых рапортов и документов.
""",
    "mil_family": """
👨‍👩‍👧 **ПОМОЩЬ СЕМЬЯМ ВОЕННОСЛУЖАЩИХ**

Защита прав и социальных интересов близких родственников:
• Юридическая помощь в получении льгот, субсидий и пособий.
• Представительство в госорганах по вопросам улучшения жилищных условий.
• Консультации по кредитным каникулам и мерам поддержки для семей участников БД.
""",
    "mil_delay": """
📋 **ОТСРОЧКА И КАТЕГОРИЯ ГОДНОСТИ**

Правовая поддержка на всех этапах прохождения комиссий:
• Анализ медицинских документов для изменения категории годности (ВВК).
• Обжалование незаконных решений о призыве или мобилизации.
• Юридические основания для получения законной отсрочки.
""",
    "mil_veteran": """
📄 **СТАТУС ВЕТЕРАНА**

Официальное содействие в признании заслуг и получении статуса:
• Помощь в оформлении удостоверения Ветерана Боевых Действий (ВБД).
• Разрешение споров при отсутствии или утере подтверждающих документов.
• Консультирование по полному пакету ветеранских льгот и выплат.
""",

    # Гражданские
    "civ_migration": """
📄 **ВНЖ И ГРАЖДАНСТВО**

Квалифицированная помощь миграционного юриста:
• Подготовка и аудит документов для получения ВНЖ / ПМЖ.
• Сопровождение процедуры получения гражданства «под ключ».
• Снятие запретов на въезд, обжалование решений миграционных служб.
""",
    "civ_auto": """
🚘 **ВОДИТЕЛЬСКОЕ УДОСТОВЕРЕНИЕ И ДТП**

Защита прав автовладельцев и водителей:
• Помощь при угрозе лишения или для возврата водительского удостоверения.
• Споры со страховыми компаниями (ОСАГО/КАСКО), занижение выплат.
• Независимая экспертиза и представительство в суде после ДТП.
""",
    "civ_edu": """
🎓 **ДОКУМЕНТЫ ОБ ОБРАЗОВАНИИ**

Правовое сопровождение в сфере образования:
• Помощь в нострификации (признании) иностранных дипломов и аттестатов.
• Разрешение споров с учебными заведениями (незаконные отчисления, договоры).
• Восстановление утерянных документов об образовании через архивы и суд.
""",
    "civ_fraud": """
⚖️ **ЗАЩИТА ОТ МОШЕННИЧЕСТВА**

Экстренная юридическая помощь при финансовых угрозах:
• Защита прав пострадавших от интернет-мошенников и финансовых пирамид.
• Отмена незаконно оформленных на ваше имя кредитов и микрозаймов.
• Составление заявлений в полицию, прокуратуру и исковых заявлений в суд.
"""
}


# --- КЛАВИАТУРЫ ---

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 Военные вопросы", callback_data="menu_military")],
        [InlineKeyboardButton("🏛 Гражданские вопросы", callback_data="menu_civil")],
        [InlineKeyboardButton("📞 Срочная консультация", callback_data="consult")]
    ])

def military_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Выплаты и компенсации", callback_data="srv_mil_payouts")],
        [InlineKeyboardButton("👨‍👩‍👧 Помощь семьям", callback_data="srv_mil_family")],
        [InlineKeyboardButton("📋 Отсрочка и ВВК", callback_data="srv_mil_delay")],
        [InlineKeyboardButton("📄 Статус ветерана", callback_data="srv_mil_veteran")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="home")]
    ])

def civil_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 ВНЖ и гражданство", callback_data="srv_civ_migration")],
        [InlineKeyboardButton("🚘 Водительские права / ДТП", callback_data="srv_civ_auto")],
        [InlineKeyboardButton("🎓 Документы об обучении", callback_data="srv_civ_edu")],
        [InlineKeyboardButton("⚖️ Защита от мошенников", callback_data="srv_civ_fraud")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data="home")]
    ])

def service_action_keyboard(back_to_section):
    """Динамическая клавиатура для конкретной услуги.
    back_to_section: куда возвращать кнопку 'Другой вопрос' (menu_military или menu_civil)"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Оформить заявку", callback_data="consult")],
        [InlineKeyboardButton("⬅️ Другой вопрос", callback_data=back_to_section)]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отменить отправку", callback_data="home")]
    ])


# --- ОБРАБОТЧИКИ ХЕНДЛЕРОВ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт бота. Выводим баннер и главное меню."""
    waiting_users.discard(update.effective_user.id)
    
    await update.message.reply_photo(
        photo=BANNER_URL,
        caption=WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Логика кликов по кнопкам """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data

    # Главное меню
    if data == "home":
        waiting_users.discard(user_id)
        await query.edit_message_caption(
            caption=WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    # Категория: Военные вопросы
    elif data == "menu_military":
        await query.edit_message_caption(
            caption=MILITARY_TEXT,
            parse_mode="Markdown",
            reply_markup=military_keyboard()
        )

    # Категория: Гражданские вопросы
    elif data == "menu_civil":
        await query.edit_message_caption(
            caption=CIVIL_TEXT,
            parse_mode="Markdown",
            reply_markup=civil_keyboard()
        )

    # Клик по конкретной услуге
    elif data.startswith("srv_"):
        service_key = data.replace("srv_", "") # получаем ключ (например, mil_payouts)
        text = SERVICES_INFO.get(service_key, "Информация обновляется...")
        
        # Определяем, куда возвращать по кнопке "Другой вопрос"
        back_target = "menu_military" if service_key.startswith("mil_") else "menu_civil"
        
        await query.edit_message_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=service_action_keyboard(back_target)
        )

    # Переход на консультацию
    elif data == "consult":
        waiting_users.add(user_id)
        await query.edit_message_caption(
            caption=CONSULT_TEXT,
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )


async def application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Обработка отправки самой заявки """
    user_id = update.effective_user.id

    if user_id not in waiting_users:
        await update.message.reply_text(
            "Пожалуйста, используйте меню бота для навигации.",
            reply_markup=main_menu_keyboard()
        )
        return

    user = update.effective_user

    admin_notification = f"🔔 **ПОСТУПИЛА НОВАЯ ЗАЯВКА**\n\n" \
                         f"👤 **Клиент:** {user.full_name}\n" \
                         f"🆔 **ID:** `{user.id}`\n" \
                         f"📛 **Юзернейм:** @{user.username if user.username else 'отсутствует'}\n" \
                         f"----------------------------------------\n\n" \
                         f"📝 **ДАННЫЕ ЗАЯВКИ:**\n{update.message.text}"

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_notification,
            parse_mode="Markdown"
        )
        
        await update.message.reply_text(
            "✨ **Ваша заявка успешно зарегистрирована!**\n\n"
            "Наш ведущий специалист уже изучает информацию. Мы свяжемся с вами в ближайшее время.",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
        await update.message.reply_text("Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.")

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

    print("Бот перезапущен с новым кнопочным меню.")
    app.run_polling()


if __name__ == "__main__":
    main()
