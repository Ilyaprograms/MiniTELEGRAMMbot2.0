import telebot
from groq import Groq
import threading
from flask import Flask
import os

# --- ПОЛУЧЕНИЕ КЛЮЧЕЙ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Чистка ключей (безопасность)
if TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip()
if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip()

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Mini Assistant is Running! No Emojis Mode Activated."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- ИНИЦИАЛИЗАЦИЯ ---
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_chats = {}

# --- НОВАЯ ИНСТРУКЦИЯ (БЕЗ СМАЙЛОВ) ---
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты — Mini, лаконичный и профессиональный ассистент. Твой создатель — Кремний. "
        "ТВОЕ ГЛАВНОЕ ПРАВИЛО: ЗАПРЕЩЕНО ИСПОЛЬЗОВАТЬ СМАЙЛИКИ, ЭМОДЗИ И ГРАФИЧЕСКИЕ СИМВОЛЫ. "
        "Пиши только текстом. Твой стиль: вежливый, сдержанный, но полезный. "
        "Отвечай на 'ты'. Пиши короткими абзацами."
    )
}

@bot.message_handler(commands=['start', 'clear'])
def clear_history(message):
    user_id = str(message.chat.id)
    user_chats[user_id] = [SYSTEM_PROMPT]
    bot.send_message(message.chat.id, "История очищена. Теперь я буду серьезнее!")

@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = str(message.chat.id)

    if user_id not in user_chats:
        user_chats[user_id] = [SYSTEM_PROMPT]

    user_chats[user_id].append({"role": "user", "content": message.text})

    # Храним последние 15 сообщений для экономии контекста
    if len(user_chats[user_id]) > 15:
        user_chats[user_id].pop(1)

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_chats[user_id],
            temperature=0.6,  # Снизили температуру, чтобы он меньше 'фантазировал' со смайлами
            max_tokens=800
        )

        reply = completion.choices[0].message.content
        user_chats[user_id].append({"role": "assistant", "content": reply})
        bot.send_message(message.chat.id, reply)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(message.chat.id, "Произошла техническая заминка. Попробуй еще раз!")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Бот Mini запущен и готов к работе без смайлов!")
    bot.infinity_polling()
