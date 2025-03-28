from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import os

API_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

form_button = KeyboardButton("Форма")
keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(form_button)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "Форма")
async def form_start(message: types.Message):
    await message.answer("Загрузите фото")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(msg: types.Message):
    await msg.answer("Теперь введите данные в формате:\n\n"
                     "1. ФИО:\n"
                     "2. Дата рождения:\n"
                     "3. Место рождения:\n"
                     "4. Дата выдачи прав:\n"
                     "5. Номер ГИБДД:\n"
                     "6. Номер прав:\n"
                     "7. Место регистрации:\n"
                     "8. Категории:")

@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(info: types.Message):
    full_text = f"\nФорма от @{info.from_user.username or info.from_user.id}:\n\n{info.text}"
    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        await bot.send_message(int(admin_id), full_text)
    await info.answer("Форма отправлена ✅")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)