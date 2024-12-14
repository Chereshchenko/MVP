import datetime
import os
import telebot
import sqlite3

def connection_open():
    connection = sqlite3.connect('MVP.db')
    return connection

def connection_close(connection):
    connection.close()

connection = connection_open()
cursor = connection.cursor()

create_table_query1 = '''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT
)
'''
cursor.execute(create_table_query1)
connection.commit()

create_table_query2 = '''
CREATE TABLE IF NOT EXISTS sleep_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    sleep_time TEXT,  -- Изменили DATETIME на TEXT
    wake_time TEXT,   -- Изменили DATETIME на TEXT
    sleep_quality INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
'''
cursor.execute(create_table_query2)
connection.commit()

create_table_query3 = '''
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    sleep_record_id INTEGER,
    FOREIGN KEY (sleep_record_id) REFERENCES sleep_records (id)
)
'''
cursor.execute(create_table_query3)
connection.commit()

MY_TOKEN = os.getenv("TG_TOKEN").strip()
bot = telebot.TeleBot(MY_TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    connection = connection_open()
    cursor = connection.cursor()
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, user_name))
    connection.commit()

    bot.send_message(message.chat.id, "Давай начнём контролировать сон. Используй команды /sleep, /wake и /history")
    connection_close(connection)

@bot.message_handler(commands=['sleep'])
def handle_sleep(message):
    connection = connection_open()
    cursor = connection.cursor()
    user_id = message.from_user.id

    cursor.execute("SELECT * FROM sleep_records WHERE user_id = ? AND wake_time IS NULL", (user_id,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Ты уже спишь! Используй /wake, чтобы проснуться")
    else:
        start_time = datetime.datetime.now().isoformat()
        cursor.execute("INSERT INTO sleep_records (user_id, sleep_time) VALUES (?, ?)", (user_id, start_time))
        connection.commit()
        bot.send_message(message.chat.id, "Спокойной ночи)")
    connection_close(connection)

@bot.message_handler(commands=['wake'])
def handle_wake(message):
    connection = connection_open()
    cursor = connection.cursor()
    user_id = message.from_user.id

    cursor.execute("SELECT id, sleep_time FROM sleep_records WHERE user_id = ? AND wake_time IS NULL", (user_id,))
    sleep_record = cursor.fetchone()

    if sleep_record is None:
        bot.send_message(message.chat.id, "Ты не спал! Используй /sleep, чтобы начать")
    else:
        end_time = datetime.datetime.now().isoformat()
        sleep_record_id = sleep_record[0]
        cursor.execute("UPDATE sleep_records SET wake_time = ? WHERE id = ?", (end_time, sleep_record_id))
        connection.commit()

        start_time = datetime.datetime.fromisoformat(sleep_record[1])

        sleep_duration = datetime.datetime.fromisoformat(end_time) - start_time
        hours, minutes = divmod(int(sleep_duration.total_seconds() // 60), 60)
        bot.send_message(message.chat.id, f"Доброе утро, ты спал {hours} часов и {minutes} минут")
    connection_close(connection)

@bot.message_handler(commands=['history'])
def handle_history(message):
    connection = connection_open()
    cursor = connection.cursor()
    user_id = message.from_user.id

    cursor.execute("SELECT sleep_time, wake_time FROM sleep_records WHERE user_id = ?", (user_id,))
    sleep_records = cursor.fetchall()

    if sleep_records:
        response = "История снов:\n"
        for i, record in enumerate(sleep_records, start=1):
            start_time = datetime.datetime.fromisoformat(record[0])  
            end_time = datetime.datetime.fromisoformat(record[1]) if record[1] else None
            duration = end_time - start_time if end_time else "Все еще спит"
            duration_hours = duration.total_seconds() / 3600 if isinstance(duration, datetime.timedelta) else 0
            response += f"Сон {i}: Начало: {start_time}, Завершение: {end_time if end_time else 'Не закончено'}, Продолжительность: {duration_hours:.2f} часов\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "Нет данных о сне")
    connection_close(connection)

bot.polling(none_stop=True)
connection_close(connection)