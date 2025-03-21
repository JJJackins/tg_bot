import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram import executor


CHAT_ID = "625265901"  # Вставьте ваш chat_id (узнать через @userinfobot)

TOKEN = os.getenv("BOT_TOKEN")  # Получаем токен из переменных окружения

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Создаем базу данных
conn = sqlite3.connect("birthdays.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS birthdays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        days_before INTEGER DEFAULT 1
    )
""")
conn.commit()

# Устанавливаем стандартное значение напоминания (если не задано)
cursor.execute("SELECT COUNT(*) FROM reminders")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO reminders (days_before) VALUES (1)")
    conn.commit()

# Создаем меню с кнопками
menu_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📅 Добавить ДР"), KeyboardButton(text="📋 Список ДР")],
    [KeyboardButton(text="❌ Удалить ДР"), KeyboardButton(text="🔔 Настроить напоминание")],
], resize_keyboard=True)


# Команда /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! Я помогу запоминать дни рождения. Выберите действие в меню:", reply_markup=menu_keyboard)


# Команда /menu – повторное вызовы меню
@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=menu_keyboard)


# Добавление дня рождения
@dp.message(lambda message: message.text == "📅 Добавить ДР")
async def add_birthday_prompt(message: types.Message):
    await message.answer("Введите ДР в формате: **Имя ДД.ММ.ГГГГ**")


@dp.message(lambda message: len(message.text.split()) == 2 and "." in message.text)
async def add_birthday(message: types.Message):
    try:
        name, date_str = message.text.split(maxsplit=1)
        datetime.strptime(date_str, "%d.%m.%Y")  # Проверка формата даты
        cursor.execute("INSERT INTO birthdays (name, date) VALUES (?, ?)", (name, date_str))
        conn.commit()
        await message.answer(f"✅ День рождения {name} ({date_str}) добавлен!")
    except ValueError:
        await message.answer("⚠️ Неправильный формат! Введите **Имя ДД.ММ.ГГГГ**")


# Список дней рождений
@dp.message(lambda message: message.text == "📋 Список ДР")
async def list_birthdays(message: types.Message):
    cursor.execute("SELECT name, date FROM birthdays")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("📭 Список пуст.")
        return
    text = "🎂 Дни рождения:\n" + "\n".join([f"{name} – {date}" for name, date in rows])
    await message.answer(text)


# Удаление дня рождения
@dp.message(lambda message: message.text == "❌ Удалить ДР")
async def delete_birthday_prompt(message: types.Message):
    await message.answer("Введите имя, чей ДР удалить:")


@dp.message(lambda message: len(message.text.split()) == 1)
async def delete_birthday(message: types.Message):
    name = message.text
    cursor.execute("DELETE FROM birthdays WHERE name = ?", (name,))
    conn.commit()
    await message.answer(f"🗑 День рождения {name} удален.")


# Настройка напоминания
@dp.message(lambda message: message.text == "🔔 Настроить напоминание")
async def set_reminder_prompt(message: types.Message):
    await message.answer("Введите, за сколько дней до ДР напоминать (например: **3**):")


@dp.message(lambda message: message.text.isdigit())
async def set_reminder_days(message: types.Message):
    days = int(message.text)
    cursor.execute("UPDATE reminders SET days_before = ?", (days,))
    conn.commit()
    await message.answer(f"🔔 Теперь я буду напоминать за {days} дней до дня рождения!")


# Проверка дней рождений и отправка уведомлений
async def check_birthdays():
    while True:
        cursor.execute("SELECT days_before FROM reminders")
        days_before = cursor.fetchone()[0]

        today = datetime.today()
        notify_date = today + timedelta(days=days_before)

        cursor.execute("SELECT name, date FROM birthdays")
        rows = cursor.fetchall()

        for name, date in rows:
            bday = datetime.strptime(date, "%d.%m.%Y").replace(year=today.year)
            if bday.date() == notify_date.date():  # Проверяем, совпадает ли день
                await bot.send_message(CHAT_ID, f"🎉 Через {days_before} дней день рождения у {name}!")

        await asyncio.sleep(86400)  # Проверяем раз в сутки


# Запуск бота
async def main():
    dp.startup.register(lambda _: asyncio.create_task(check_birthdays()))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

executor.start_polling(dp, skip_updates=True)
