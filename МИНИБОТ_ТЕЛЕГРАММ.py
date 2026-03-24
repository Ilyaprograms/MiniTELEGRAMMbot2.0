import telebot
from groq import Groq
import threading
from flask import Flask
import os

# В ФАЙЛЕ ТОЛЬКО ТАК:
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Очищаем ключи от случайных пробелов
TELEGRAM_TOKEN = TELEGRAM_TOKEN.strip()
if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы бот не спал) ---
app = Flask(__name__)


@app.route('/')
def home():
    return "Mini Assistant is Running with Memory!"


def run_flask():
    # На Render порт выдается автоматически, по умолчанию 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# --- ИНИЦИАЛИЗАЦИЯ ИИ И БОТА ---
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# База данных чатов в памяти: {user_id: [список сообщений]}
user_chats = {}

# --- ИНСТРУКЦИЯ ДЛЯ MINI (Системная роль) ---
# Измени текст в кавычках, чтобы поменять характер бота
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты — Mini, живой и супер-дружелюбный ассистент. Твой создатель — Кремний. "
        "Твой стиль: общайся на 'ты',НЕ ИСПОЛЬЗУЙ СМАЙЛЫ ЕСЛИ ТЕБЯ НЕ ПРОСЯТ НА ПРЯМУЮ "
        "будь энергичным и всегда подбадривай пользователя. "
        "Если тебя хвалят — радуйся, если шутят — шути в ответ. "
        "Избегай скучных фраз вроде 'Чем я могу вам помочь?'. "
        "Пиши короткими, емкими абзацами. Ты обожаешь технологии и Python!"
    )
}


# --- ЛОГИКА БОТА С ПАМЯТЬЮ ---
@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_id = str(message.chat.id)

    # 1. Если это новый пользователь, создаем ему историю с системной инструкцией
    if user_id not in user_chats:
        user_chats[user_id] = [SYSTEM_PROMPT]
        print(f"🆕 Создан новый чат для пользователя {user_id}")

    # 2. Добавляем сообщение пользователя в историю
    user_chats[user_id].append({"role": "user", "content": message.text})

    # Ограничим память (например, храним последние 20 сообщений, чтобы не перегружать ИИ)
    if len(user_chats[user_id]) > 20:
        # Удаляем самое старое сообщение пользователя (индекс 1, т.к. 0 - это система)
        user_chats[user_id].pop(1)

    try:
        # 3. Отправляем ВСЮ ИСТОРИЮ чата в Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Самая мощная модель
            messages=user_chats[user_id]
        )

        # 4. Получаем ответ, добавляем его в историю и отправляем пользователю
        reply = completion.choices[0].message.content
        user_chats[user_id].append({"role": "assistant", "content": reply})
        bot.send_message(message.chat.id, reply)

    except Exception as e:
        print(f"❌ Ошибка Groq: {e}")
        bot.send_message(message.chat.id, "Упс, нейросеть задумалась. Попробуй позже!")


# --- ЗАПУСК ---
if __name__ == "__main__":
    # Запускаем веб-сервер в фоне
    threading.Thread(target=run_flask, daemon=True).start()

    print("✅ Бот Mini запущен локально и готов к переезду в облако!")
    # Запускаем бота (бесконечный опрос)
    bot.infinity_polling()
