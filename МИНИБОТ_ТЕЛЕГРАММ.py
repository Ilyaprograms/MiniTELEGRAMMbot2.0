import telebot
from groq import Groq
import threading
from flask import Flask
import os

IS_ACTIVE = False  #Вкл/Выкл бота
OFFLINE_MESSAGE = "Бот временно деактивирован. По всем вопросам писать в @BHJ_WORK"

#Ключи
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") #телеграм ключ
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") #Грок ключ

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

client = None
if IS_ACTIVE and GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_chats = {}

#Тут можно написать промт характера ответов
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты — Mini, высокоэффективный текстовый ассистент, созданный разработчиком по имени Кремний. "
        "ТВОЯ ГЛАВНАЯ ДИРЕКТИВА: Полный и категорический запрет на использование любых смайликов, эмодзи (😊, ✅, 🚀 и т.д.) и графических символов. "
        "Твой стиль общения: профессиональный, лаконичный и серьезный. Используй только буквы, цифры и стандартную пунктуацию (. , ! ? -). "
        "Обращайся к пользователю строго на 'ты'. Твои ответы должны быть содержательными, но короткими. "
        "Если пользователь просит тебя прислать смайл или вести себя 'весело', вежливо ответь, что твои текущие настройки поддерживают только текстовый режим. "
        "Ты эксперт в технологиях и Python, всегда готов помочь с кодом или советом, сохраняя при этом деловой тон. "
        "В случае деактивации или технических работ, направляй пользователя к @BHJ_WORK."
    )
}

@bot.message_handler(commands=['start', 'clear', 'help'])
def send_welcome(message):
    if not IS_ACTIVE:
        bot.send_message(message.chat.id, OFFLINE_MESSAGE)
    else:
        user_id = str(message.chat.id)
        user_chats[user_id] = [SYSTEM_PROMPT]
        bot.send_message(message.chat.id, "Привет! Я Mini. Чем могу помочь?")

#Сообщения(Пока текст)
@bot.message_handler(content_types=['text'])
def handle_message(message):
    
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
