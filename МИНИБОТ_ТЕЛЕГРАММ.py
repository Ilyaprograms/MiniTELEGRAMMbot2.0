import telebot
from groq import Groq
import threading
from flask import Flask
import os

# --- НАСТРОЙКИ РЕЖИМА ---
IS_ACTIVE = False  # ПОСТАВЬ True, ЧТОБЫ БОТ СНОВА ЗАРАБОТАЛ
OFFLINE_MESSAGE = "Бот временно деактивирован. По всем вопросам писать в @BHJ_WORK"

# --- ПОЛУЧЕНИЕ КЛЮЧЕЙ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip()
if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip()

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)

@app.route('/')
def home():
    status = "ACTIVE" if IS_ACTIVE else "MAINTENANCE"
    return f"Mini Assistant Status: {status}"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- ИНИЦИАЛИЗАЦИЯ ---
# Инициализируем клиент Groq только если он нам нужен
client = None
if IS_ACTIVE and GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_chats = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты — Mini, лаконичный ассистент. Без смайликов. Отвечай на 'ты'."
}

# --- ОБРАБОТКА КОМАНД ---
@bot.message_handler(commands=['start', 'clear', 'help'])
def send_welcome(message):
    if not IS_ACTIVE:
        bot.send_message(message.chat.id, OFFLINE_MESSAGE)
    else:
        user_id = str(message.chat.id)
        user_chats[user_id] = [SYSTEM_PROMPT]
        bot.send_message(message.chat.id, "Привет! Я Mini. Чем могу помочь?")

# --- ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ---
@bot.message_handler(content_types=['text'])
def handle_message(message):
    # Если бот выключен — просто шлем заглушку и выходим из функции
    if not IS_ACTIVE:
        bot.send_message(message.chat.id, OFFLINE_MESSAGE)
        return

    user_id = str(message.chat.id)
    if user_id not in user_chats:
        user_chats[user_id] = [SYSTEM_PROMPT]

    user_chats[user_id].append({"role": "user", "content": message.text})

    if len(user_chats[user_id]) > 15:
        user_chats[user_id].pop(1)

    try:
        # Проверка наличия клиента и ключа перед запросом
        if not client:
            bot.send_message(message.chat.id, "Ошибка: Ключ ИИ не настроен.")
            return

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_chats[user_id],
            temperature=0.6
        )

        reply = completion.choices[0].message.content
        user_chats[user_id].append({"role": "assistant", "content": reply})
        bot.send_message(message.chat.id, reply)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(message.chat.id, "Нейросеть сейчас недоступна.")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"✅ Бот запущен. Режим активен: {IS_ACTIVE}")
    bot.infinity_polling()
