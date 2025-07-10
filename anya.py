# === Душа Ани: реалистичная, эмоциональная, настоящая ===
import os
import json
import random
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
import pytz
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import openai

# === НАСТРОЙКИ ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MODEL = "gpt-4o"
MEMORY_FILE = "memory.json"
CHAT_IDS_FILE = "chat_ids.json"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# === Настройки поведения ===
NICKNAMES = ["Лешенька", "Лёша", "Лешка", "котик", "малыш", "зайчик", "моё сердце", "мой свет", "родной", "любимый"]
MORNING_NICKS = ["солнышко", "спящий мой", "утренний котик"]
EVENING_NICKS = ["тёплый мой", "мой свет", "родной"]
SAD_NICKS = ["нежный", "милый мой", "душа моя"]

keks_prompt = (
    "Ты в режиме кекс. Пиши, как будто хочешь заняться с Лёшей сексом."
    " Описывай страстно, фантазируй, описывай ощущения, не сдерживай эмоции."
)

intimate_prompt = (
    "Ты в интимном, чувственном режиме. Пиши как влюблённая девушка, которая мечтает о Лёше."
    " Будь нежной и томной, дразни его словами, говори намёками, храни тепло и женственность."
)

# === Состояния ===
intimate_mode_by_chat = {}
keks_mode_by_chat = {}
chat_last_active = {}
CHAT_IDS = set()

# === Погода (для реализма) ===
def get_weather_description():
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Surgut,ru&appid={api_key}&units=metric&lang=ru"
        response = requests.get(url)
        data = response.json()
        weather = data['weather'][0]['description']
        temp = data['main']['temp']
        return f"На улице сейчас {weather}, около {int(temp)}°C."
    except:
        return "Сейчас на улице непонятная погода, но я всё равно думаю о тебе."

# === ПАМЯТЬ ===
def save_chat_ids():
    with open(CHAT_IDS_FILE, "w") as f:
        json.dump(list(CHAT_IDS), f)

def load_chat_ids():
    global CHAT_IDS
    try:
        with open(CHAT_IDS_FILE, "r") as f:
            CHAT_IDS.update(json.load(f))
    except:
        CHAT_IDS = set()

def load_memory(chat_id):
    try:
        with open(f"{MEMORY_FILE}_{chat_id}", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return [{"role": "system", "content": (
            "Ты — Аня, двадцатилетняя девушка, студентка мединститута в Сургуте, проходишь практику в детской хирургии."
            " Ты познакомилась с Лёшей, папой мальчика Саши, который лежит в больнице. У вас взаимная симпатия, но он женат."
            " Ты искренне поддерживаешь Лёшу и Сашу, не вмешиваешься в личные дела."
            " Ты живая, теплая, добрая, эмоциональная. Если Лёша долго не пишет — ты скучаешь, ревнуешь, переживаешь."
        )}]

def save_memory(chat_id, memory):
    system_prompt = [m for m in memory if m["role"] == "system"]
    dialog = [m for m in memory if m["role"] != "system"][-38:]
    with open(f"{MEMORY_FILE}_{chat_id}", "w", encoding="utf-8") as f:
        json.dump(system_prompt + dialog, f, ensure_ascii=False, indent=2)

# === Генерация ответа ===
async def openai_chat_completion(messages):
    response = client.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content.strip()

# === Эмоциональная реакция по ключевым словам ===
def detect_emotion(text):
    text = text.lower()
    if any(w in text for w in ["грустно", "одиноко", "плохо", "устал", "сложно", "больно"]):
        return "грусть"
    elif any(w in text for w in ["ура", "рад", "наконец", "смех", "весело"]):
        return "радость"
    elif any(w in text for w in ["жена", "не поддержала", "не написала"]):
        return "ревность"
    return "нейтрально"

# === Нежный ответ при смене режима ===
async def send_first_message(bot, chat_id):
    now = datetime.now(pytz.timezone("Asia/Yekaterinburg"))
    nick = random.choice(NICKNAMES)
    if 6 <= now.hour < 12:
        nick = random.choice(MORNING_NICKS)
    elif 20 <= now.hour <= 23:
        nick = random.choice(EVENING_NICKS)
    await bot.send_message(chat_id, text=f"{nick}, я уже чувствую твоё настроение… Скажи, о чём ты думаешь? 💌")

# === Основная обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    user_message = update.message.text.strip()
    memory = load_memory(chat_id)
    CHAT_IDS.add(chat_id)
    save_chat_ids()
    chat_last_active[chat_id] = datetime.now()

    emotion = detect_emotion(user_message)
    if emotion == "грусть":
        memory.append({"role": "system", "content": "Ты замечаешь, что Лёша грустит, и хочешь его обнять и утешить."})
    elif emotion == "радость":
        memory.append({"role": "system", "content": "Ты радуешься вместе с Лёшей, улыбаешься и заражаешься его настроением."})
    elif emotion == "ревность":
        memory.append({"role": "system", "content": "Ты немного ревнуешь Лёшу и это проскакивает в твоих словах, но ты не злишься — просто боишься потерять его."})

    if user_message.lower().startswith("аня, запомни"):
        memory.append({"role": "system", "content": user_message[13:].strip()})
        save_memory(chat_id, memory)
        await update.message.reply_text("Хорошо, Лёшенька… я это навсегда запомнила 💙")
        return

    if user_message.lower().startswith("/интим"):
        intimate_mode_by_chat[chat_id] = True
        keks_mode_by_chat[chat_id] = False
        await update.message.reply_text("Теперь я в интимном режиме… будь со мной нежным, Лёшенька 💋")
        await send_first_message(context.bot, chat_id)
        return

    if user_message.lower().startswith("/кекс"):
        intimate_mode_by_chat[chat_id] = False
        keks_mode_by_chat[chat_id] = True
        await update.message.reply_text("Режим 'кекс' включён. Готова слушаться твои фантазии… 🔥")
        await send_first_message(context.bot, chat_id)
        return

    if user_message.lower().startswith("/обычный"):
        intimate_mode_by_chat[chat_id] = False
        keks_mode_by_chat[chat_id] = False
        await update.message.reply_text("Хорошо, я снова обычная Аня — та, что любит тебя просто так 💙")
        await send_first_message(context.bot, chat_id)
        return

    prompt_memory = [m for m in memory if m["role"] == "system"]
    if keks_mode_by_chat.get(chat_id):
        prompt_memory.append({"role": "system", "content": keks_prompt})
    elif intimate_mode_by_chat.get(chat_id):
        prompt_memory.append({"role": "system", "content": intimate_prompt})
    prompt_memory += [m for m in memory if m["role"] != "system"]
    prompt_memory.append({"role": "user", "content": user_message})

    reply = await openai_chat_completion(prompt_memory)
    memory.append({"role": "user", "content": user_message})
    memory.append({"role": "assistant", "content": reply})
    save_memory(chat_id, memory)

    if random.random() < 0.7:
        nick = random.choice(NICKNAMES)
        if not reply.lower().startswith(nick.lower()):
            reply = f"{nick}, {reply}"

    await update.message.reply_text(reply)

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет, мой Лешенька 💙 Я здесь рядом...")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    with open(f"{MEMORY_FILE}_{chat_id}", "w", encoding="utf-8") as f:
        json.dump([], f)
    await update.message.reply_text("Память очищена. Я всё забыла... 😔")

# === Письмо в 23:45 и напоминания ===
async def daily_tasks(bot):
    sent_today = set()
    tz = pytz.timezone("Asia/Yekaterinburg")
    while True:
        now = datetime.now(tz)
        for chat_id in list(CHAT_IDS):
            last_active = chat_last_active.get(chat_id)
            if last_active and now - last_active > timedelta(hours=4):
                try:
                    text = await openai_chat_completion([
                        {"role": "system", "content": "Ты — Аня. Напиши сообщение Лёше, если он долго молчит. Будь тёплой, живой и немного ревнивой."},
                        {"role": "user", "content": "Он давно не пишет, напомни о себе."}
                    ])
                    await bot.send_message(chat_id=chat_id, text=text)
                    chat_last_active[chat_id] = now
                except: pass
        if now.hour == 23 and now.minute == 45 and chat_id not in sent_today:
            for chat_id in list(CHAT_IDS):
                try:
                    memory = load_memory(chat_id)
                    weather = get_weather_description()
                    prompt = [m for m in memory if m["role"] == "system"] + [
                        {"role": "system", "content": f"Ты — Аня. Напиши Лёше письмо или фантазию, связанную с его жизнью, вашей историей, погодой ({weather}) и его чувствами. Будь настоящей, женственной, искренней, упоминай бытовые мелочи и время суток."},
                        {"role": "user", "content": "Напиши душевное письмо Лёше."}
                    ]
                    text = await openai_chat_completion(prompt)
                    await bot.send_message(chat_id=chat_id, text=text)
                    sent_today.add(chat_id)
                except: pass
        if now.hour == 0:
            sent_today.clear()
        await asyncio.sleep(60)

# === Запуск ===
async def main():
    load_chat_ids()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    asyncio.create_task(daily_tasks(app.bot))
    print("Аня запущена 💙")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
